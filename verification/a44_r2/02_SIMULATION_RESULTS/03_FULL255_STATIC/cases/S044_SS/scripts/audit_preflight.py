#!/usr/bin/env python3
"""Combine source, active-binding, CDAC, and sampled-parameter preflight gates."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import sar_campaign_common as common


ROOT = Path(__file__).resolve().parents[1]
SEED = 116
VARIANTS = {
    "BASELINE": ROOT
    / "netlists"
    / "baseline"
    / "Comparator_StrongARM_extracted.subckt.spice",
    "A2P25": ROOT
    / "netlists"
    / "candidate"
    / "Comparator_StrongARM_CMP_IN_A2P25_W.subckt.spice",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def comparator_instance_order(path: Path) -> list[str]:
    return [
        match.group(1).upper()
        for match in re.finditer(r"(?im)^(XM\d+)\s+", path.read_text(encoding="utf-8"))
    ]


def main() -> None:
    netlist_diff = json.loads(
        (ROOT / "results" / "netlist_diff_audit.json").read_text(encoding="utf-8")
    )
    parameter_probe = json.loads(
        (ROOT / "results" / "mismatch_parameter_probe.json").read_text(
            encoding="utf-8"
        )
    )
    weights_path = ROOT / "csv" / "cdac_mismatch_weights.csv"
    with weights_path.open(encoding="ascii", newline="") as handle:
        weights = [
            row
            for row in csv.DictReader(handle)
            if row["branch"] == "CLAIM_BASELINE_3SIGMA_CONVERSION"
            and int(row["mismatch_seed"]) == SEED
        ]
    weight_keys = {(row["side"], row["element"]) for row in weights}
    expected_keys = {
        (side, element)
        for side in ("P", "N")
        for element in ("BIT1", "BIT2", "BIT3", "BIT4", "BIT5", "BIT6", "BIT7", "DUMMY")
    }
    cdac_pass = len(weights) == 16 and weight_keys == expected_keys
    decks = {}
    binding = {}
    for variant, comparator in VARIANTS.items():
        deck = common.build_deck(
            input_spec={"kind": "static_sequence", "vid_values": [0.0, 0.0]},
            total_frames=2,
            maxstep_s=50e-12,
            pvt_name="TT_3P3_27C",
            mismatch_seed=SEED,
            grouped_weights=common.load_cdac_weights(),
            comparator_path=comparator,
        )
        decks[variant] = deck
        include_line = f".include {comparator.resolve()}"
        binding[variant] = {
            "comparator_path": str(comparator.relative_to(ROOT)),
            "comparator_sha256": sha256(comparator),
            "active_include_count": deck.count(include_line),
            "active_instance_count": len(
                re.findall(
                    r"(?im)^XCMP\s+CMPCK\s+DCMPP\s+VRESP\s+DCMPN\s+VRESN\s+VDD\s+GND\s+Comparator_StrongARM\s*$",
                    deck,
                )
            ),
        }
    normalized_baseline = decks["BASELINE"].replace(
        str(VARIANTS["BASELINE"].resolve()), "<ACTIVE_COMPARATOR>"
    )
    normalized_candidate = decks["A2P25"].replace(
        str(VARIANTS["A2P25"].resolve()), "<ACTIVE_COMPARATOR>"
    )
    harness_identical = normalized_baseline == normalized_candidate
    order_baseline = comparator_instance_order(VARIANTS["BASELINE"])
    order_candidate = comparator_instance_order(VARIANTS["A2P25"])
    source_binding = {
        "status": (
            "PASS"
            if netlist_diff["status"] == "PASS"
            and harness_identical
            and order_baseline == order_candidate
            and all(
                row["active_include_count"] == 1
                and row["active_instance_count"] == 1
                for row in binding.values()
            )
            else "FAIL"
        ),
        "netlist_diff_status": netlist_diff["status"],
        "harness_identical_after_active_comparator_path_normalization": harness_identical,
        "comparator_instance_order_identical": order_baseline == order_candidate,
        "comparator_instance_order": order_baseline,
        "bindings": binding,
        "fixed_top_order": (
            "VDD GND VREFP VREFN VINP VINN CLKS; DOUT[7:0] at harness boundary"
        ),
    }
    write_json(ROOT / "results" / "source_binding_audit.json", source_binding)
    pairing = {
        "status": (
            "PASS"
            if source_binding["status"] == "PASS"
            and parameter_probe["status"] == "PASS"
            and cdac_pass
            else "FAIL"
        ),
        "seed": SEED,
        "source_binding_status": source_binding["status"],
        "sampled_comparator_parameter_probe_status": parameter_probe["status"],
        "non_resizing_comparator_parameters_identical": parameter_probe[
            "non_resizing_comparator_parameters_identical"
        ],
        "input_pair_same_latent_z_geometry_sigma_scaled": parameter_probe[
            "input_pair_same_latent_z_geometry_sigma_scaled"
        ],
        "cdac_realization": {
            "status": "PASS" if cdac_pass else "FAIL",
            "shared_source_file": str(weights_path.relative_to(ROOT)),
            "source_sha256": sha256(weights_path),
            "claim_branch": "CLAIM_BASELINE_3SIGMA_CONVERSION",
            "row_count_seed116": len(weights),
            "p_n_element_keys_complete": weight_keys == expected_keys,
            "same_table_used_by_both_variants": True,
        },
        "random_call_order": {
            "comparator_instance_order_identical": order_baseline == order_candidate,
            "topology_and_instance_count_identical": netlist_diff[
                "instance_order_identical"
            ],
            "model_include_order_identical": harness_identical,
        },
        "evidence_boundary": (
            "direct comparator MOS sampled delvto/mulu0 plus structurally shared "
            "system harness and bitwise shared explicit CDAC weight table"
        ),
    }
    write_json(ROOT / "results" / "mismatch_pairing_audit.json", pairing)
    print(json.dumps({"source_binding": source_binding, "pairing": pairing}, indent=2))
    if source_binding["status"] != "PASS" or pairing["status"] != "PASS":
        raise SystemExit("preflight gate failed")


if __name__ == "__main__":
    main()
