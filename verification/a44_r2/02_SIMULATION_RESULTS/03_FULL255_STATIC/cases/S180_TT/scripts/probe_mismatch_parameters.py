#!/usr/bin/env python3
"""Probe model-exposed sampled MOS mismatch parameters for pairing evidence."""

from __future__ import annotations

import json
import math
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
PARAM_RE = re.compile(
    r"(?im)^\s*@m\.xcore\.xcmp\.(xm\d+)\.m0\[(delvto|mulu0)\]\s*=\s*([-+0-9.eE]+)"
)


def build_probe(comparator: Path) -> str:
    deck = common.build_deck(
        input_spec={"kind": "static_sequence", "vid_values": [0.0, 0.0]},
        total_frames=2,
        maxstep_s=50e-12,
        pvt_name="TT_3P3_27C",
        mismatch_seed=SEED,
        grouped_weights=common.load_cdac_weights(),
        comparator_path=comparator,
    )
    commands = ["set numdgt=15", "echo sampled_parameter_audit_begin"]
    for index in range(1, 16):
        commands.append(
            "print "
            f"@m.xcore.xcmp.xm{index}.m0[delvto] "
            f"@m.xcore.xcmp.xm{index}.m0[mulu0]"
        )
    commands.append("echo sampled_parameter_audit_end")
    anchor = "\nquit\n.endc"
    if deck.count(anchor) != 1:
        raise RuntimeError("unexpected control-section quit anchor")
    return deck.replace(anchor, "\n" + "\n".join(commands) + anchor, 1)


def run_variant(name: str, comparator: Path) -> dict:
    stem = f"mismatch_parameter_probe_{name.lower()}_s116"
    result = common.run_deck(
        build_probe(comparator),
        stem,
        ROOT / "generated" / "jobs" / "mismatch_probe",
        ROOT / "logs" / "mismatch_probe",
        timeout_s=600,
    )
    text = result["log"].read_text(encoding="utf-8", errors="replace")
    values: dict[str, dict[str, float]] = {}
    for instance, parameter, value in PARAM_RE.findall(text):
        values.setdefault(instance.upper(), {})[parameter.lower()] = float(value)
    return {
        "returncode": result["returncode"],
        "elapsed_s": result["elapsed_s"],
        "cached": result["cached"],
        "values": values,
        "log": str(result["log"].relative_to(ROOT)),
    }


def main() -> None:
    runs = {name: run_variant(name, path) for name, path in VARIANTS.items()}
    baseline = runs["BASELINE"]["values"]
    candidate = runs["A2P25"]["values"]
    rows = []
    direct_observation_complete = True
    non_resizing_equal = True
    resized_z_equal = True
    for index in range(1, 16):
        instance = f"XM{index}"
        b = baseline.get(instance, {})
        a = candidate.get(instance, {})
        if not {"delvto", "mulu0"}.issubset(b) or not {
            "delvto",
            "mulu0",
        }.issubset(a):
            direct_observation_complete = False
        for parameter in ("delvto", "mulu0"):
            bv = b.get(parameter, math.nan)
            av = a.get(parameter, math.nan)
            equal = (
                math.isfinite(bv)
                and math.isfinite(av)
                and math.isclose(bv, av, rel_tol=1e-9, abs_tol=1e-12)
            )
            if index not in (3, 4):
                non_resizing_equal = non_resizing_equal and equal
            rows.append(
                {
                    "instance": instance,
                    "parameter": parameter,
                    "baseline": bv,
                    "a2p25": av,
                    "equal": equal,
                    "role": (
                        "RESIZED_INPUT_PAIR"
                        if index in (3, 4)
                        else "NON_RESIZING_COMPARATOR_DEVICE"
                    ),
                }
            )
    # The GF180 statistical wrapper is linear in sigma for delvto and
    # (1-mulu0), with par_weff = par*(w-par_w) and par_w=-0.1 um for
    # nfet_03v3. L, nf, par and multiplicity remain fixed.
    model_par_w_um = -0.1
    sigma_ratio = math.sqrt(
        (1.56 - model_par_w_um) / (3.51 - model_par_w_um)
    )
    for instance in ("XM3", "XM4"):
        b = baseline.get(instance, {})
        a = candidate.get(instance, {})
        if {"delvto", "mulu0"}.issubset(b) and {
            "delvto",
            "mulu0",
        }.issubset(a):
            delvto_ratio_ok = math.isclose(
                a["delvto"],
                b["delvto"] * sigma_ratio,
                rel_tol=2e-5,
                abs_tol=1e-10,
            )
            k_base = 1.0 - b["mulu0"]
            k_candidate = 1.0 - a["mulu0"]
            mulu_ratio_ok = math.isclose(
                k_candidate,
                k_base * sigma_ratio,
                rel_tol=2e-5,
                abs_tol=1e-10,
            )
            resized_z_equal = resized_z_equal and delvto_ratio_ok and mulu_ratio_ok
            rows.extend(
                (
                    {
                        "instance": instance,
                        "parameter": "delvto_latent_z_ratio",
                        "baseline": b["delvto"],
                        "a2p25": a["delvto"],
                        "equal": delvto_ratio_ok,
                        "role": "RESIZED_INPUT_PAIR_STANDARDIZED_PAIRING",
                    },
                    {
                        "instance": instance,
                        "parameter": "mulu0_latent_z_ratio",
                        "baseline": k_base,
                        "a2p25": k_candidate,
                        "equal": mulu_ratio_ok,
                        "role": "RESIZED_INPUT_PAIR_STANDARDIZED_PAIRING",
                    },
                )
            )
        else:
            resized_z_equal = False
    common.write_csv(ROOT / "csv" / "sampled_parameter_pairing.csv", rows)
    payload = {
        "seed": SEED,
        "runs": runs,
        "direct_observation_complete": direct_observation_complete,
        "non_resizing_comparator_parameters_identical": non_resizing_equal,
        "input_pair_same_latent_z_geometry_sigma_scaled": resized_z_equal,
        "expected_sigma_ratio_a2p25_over_baseline": sigma_ratio,
        "gf180_nfet_03v3_par_w_um": model_par_w_um,
        "status": (
            "PASS"
            if all(
                (
                    all(run["returncode"] == 0 for run in runs.values()),
                    direct_observation_complete,
                    non_resizing_equal,
                    resized_z_equal,
                )
            )
            else "FAIL"
        ),
        "scope": (
            "model-exposed Comparator_StrongARM MOS delvto/mulu0; CDAC pairing "
            "and system structural ordering are audited separately"
        ),
    }
    (ROOT / "results" / "mismatch_parameter_probe.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    if payload["status"] != "PASS":
        raise SystemExit("sampled parameter pairing probe failed")


if __name__ == "__main__":
    main()
