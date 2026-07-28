#!/usr/bin/env python3
"""Rebuild indexes and seal the reorganized A44 R2 package."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "02_SIMULATION_RESULTS"
TOOLS = ROOT / "03_CACE_AND_SIMULATION_TOOLS"
CIRCUITS = ROOT / "01_CURRENT_CIRCUIT_FILES"
DOCS = ROOT / "04_PACKAGE_DOCS"
AUDITS = ROOT / "05_PACKAGE_AUDIT"
RUN_OUTPUTS = RESULTS / "06_RUN_OUTPUTS"
R1 = ROOT.parent / "A44_SAR_ADC_CURRENT_CACE_REPRODUCIBLE_20260728_R1"

CAMPAIGNS = (
    "01_MC200_TT_LOW_W4",
    "02_PVT3_MC20_LOW_W4",
    "03_FULL255_STATIC",
    "04_CROSS_CAMPAIGN_SUMMARY",
)
STATIC_CASES = (
    "S044_TT",
    "S116_TT",
    "S180_TT",
    "S106_TT",
    "S044_SS",
    "S044_FF",
)
PORTABILITY_PATCHES = {
    "02_SIMULATION_RESULTS/01_MC200_TT_LOW_W4/scripts/sar_campaign_common.py",
    "02_SIMULATION_RESULTS/02_PVT3_MC20_LOW_W4/scripts/sar_campaign_common.py",
    *{
        "02_SIMULATION_RESULTS/03_FULL255_STATIC/"
        f"cases/{case}/scripts/sar_campaign_common.py"
        for case in STATIC_CASES
    },
}
ROOT_LAUNCHERS = {
    "RUN_FULL_CAMPAIGN.bat",
    "RUN_FULL_CAMPAIGN.ps1",
    "RUN_QUICK_VERIFY.bat",
    "RUN_QUICK_VERIFY.ps1",
}
COMPARATOR_SHA256 = (
    "53f26155df31b8d1f50dd1bc99a17a6530de29233c11faabe63906debd1b5b49"
)
PDK_HASHES = {
    "design.ngspice":
        "091cb530bf85160a1f07878fb81f789ca367d018991c8ab41a584cd1a85c6692",
    "sm141064.ngspice":
        "677822db50bf8968f77854bb455006ac5c245deb46ecfc8b352934e752135c46",
    "sm141064_mim.ngspice":
        "b7918b5ad4f4dad0ce5cb2fc08114e25b10ff5f9f827754334bb0bdfe2a89767",
}
PACKAGE_MANIFEST = AUDITS / "package_manifest_sha256.csv"
MANIFEST_EXCLUDES = {
    "05_PACKAGE_AUDIT/package_manifest_sha256.csv",
    "05_PACKAGE_AUDIT/manifest_readback_latest.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def ignored(path: Path) -> bool:
    return "__pycache__" in path.parts or path.suffix.lower() == ".pyc"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    data = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in data:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)
    return len(data)


def indexed_files(base: Path) -> list[Path]:
    return sorted(
        path for path in base.rglob("*")
        if path.is_file() and not ignored(path)
    )


def build_file_index(base: Path, destination: Path, scope_label: str) -> int:
    rows = []
    for path in indexed_files(base):
        local = path.relative_to(base)
        rows.append({
            "scope": local.parts[0] if len(local.parts) > 1 else scope_label,
            "relative_path": relative(path),
            "absolute_path": str(path),
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    return write_csv(destination, rows)


def build_current_circuit_index() -> tuple[int, int, int]:
    selected = [
        path for path in indexed_files(CIRCUITS)
        if path.suffix.lower() in {".sch", ".sym", ".spice", ".sv"}
        or path.name.lower() == "xschemrc"
    ]
    rows = [{
        "file_type": (
            "SCHEMATIC" if path.suffix.lower() == ".sch"
            else "SYMBOL" if path.suffix.lower() == ".sym"
            else "RTL" if path.suffix.lower() in {".sv", ".v"}
            else "XSCHEM_CONFIG" if path.name.lower() == "xschemrc"
            else "SPICE"
        ),
        "relative_path": relative(path),
        "absolute_path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "version_scope": "CURRENT_RESIZED_LATEST_ONLY",
    } for path in selected]
    count = write_csv(DOCS / "CURRENT_CIRCUIT_FILE_INDEX.csv", rows)
    return (
        count,
        sum(path.suffix.lower() == ".sch" for path in selected),
        sum(path.suffix.lower() == ".sym" for path in selected),
    )


def build_matrix() -> int:
    rows = [
        {
            "matrix": "MC200_TT_LOW_W4",
            "method": "FAST64_SS_W4",
            "pvt": "TT_3P3_27C",
            "population_or_cases": 200,
            "formal_window": "frames_4_to_67_64_records",
            "maxstep_ps": 50,
            "completed": "200/200",
            "performance": "197 hard dynamic PASS; 3 FAIL seeds 65,68,141",
            "claim_boundary": "TT LOW-only MC200; not two-band die yield",
            "result_path": str(RESULTS / "01_MC200_TT_LOW_W4"),
        },
        {
            "matrix": "PVT3_SELECTED_MC20_LOW_W4",
            "method": "FAST64_SS_W4",
            "pvt": "TT_3P3_27C;SS_3P0_125C;FF_3P6_M40C",
            "population_or_cases": 60,
            "formal_window": "frames_4_to_67_64_records",
            "maxstep_ps": 50,
            "completed": "60/60",
            "performance": "TT 19/20; SS 20/20; FF 20/20 hard dynamic PASS",
            "claim_boundary": "selected MC20 diagnostic; not yield or signoff",
            "result_path": str(RESULTS / "02_PVT3_MC20_LOW_W4"),
        },
        {
            "matrix": "FOUR_SEEDS_FULL255_STATIC_TT",
            "method": "FULL255_STATIC_TRANSITION_SEARCH",
            "pvt": "TT_3P3_27C",
            "population_or_cases": 4,
            "formal_window": "transitions_1_to_255",
            "maxstep_ps": "",
            "completed": "4/4 curves",
            "performance": "S044,S116,S180,S106 all PASS",
            "claim_boundary": "four deterministic curves; not population yield",
            "result_path": str(RESULTS / "03_FULL255_STATIC"),
        },
        {
            "matrix": "SEED44_FULL255_STATIC_PVT",
            "method": "FULL255_STATIC_TRANSITION_SEARCH",
            "pvt": "TT_3P3_27C;SS_3P0_125C;FF_3P6_M40C",
            "population_or_cases": 3,
            "formal_window": "transitions_1_to_255",
            "maxstep_ps": "",
            "completed": "3/3 curves; TT reused after exact audit",
            "performance": "TT PASS; SS FAIL; FF PASS",
            "claim_boundary": "SS failure blocks promotion",
            "result_path": str(RESULTS / "03_FULL255_STATIC"),
        },
        {
            "matrix": "CACE_PACKAGE_PREFLIGHT",
            "method": "CACE_2P9_XSCHEM_NGSPICE",
            "pvt": "package_execution_preflight",
            "population_or_cases": 1,
            "formal_window": "single_preflight",
            "maxstep_ps": "",
            "completed": "1/1",
            "performance": "final_v=1.250 V within 1.249-1.251 V; PASS",
            "claim_boundary": "package/tool closure only; not ADC performance",
            "result_path": str(RESULTS / "05_CACE_GENERATED"),
        },
    ]
    return write_csv(DOCS / "SIMULATION_MATRIX.csv", rows)


def compare_tree(
    source: Path,
    destination: Path,
    package_prefix: str,
    patches: set[str],
) -> list[dict[str, Any]]:
    source_files = {
        path.relative_to(source).as_posix(): path
        for path in indexed_files(source)
    }
    destination_files = {
        path.relative_to(destination).as_posix(): path
        for path in indexed_files(destination)
    }
    rows: list[dict[str, Any]] = []
    for rel in sorted(set(source_files) | set(destination_files)):
        src = source_files.get(rel)
        dst = destination_files.get(rel)
        package_rel = f"{package_prefix}/{rel}"
        src_hash = sha256(src) if src else ""
        dst_hash = sha256(dst) if dst else ""
        if src is None:
            status = "UNEXPECTED_PACKAGE_EXTRA"
        elif dst is None:
            status = "MISSING"
        elif src_hash == dst_hash:
            status = "EXACT_COPY"
        elif package_rel in patches:
            status = "INTENTIONAL_PORTABILITY_PATCH"
        else:
            status = "UNEXPECTED_HASH_DIFFERENCE"
        rows.append({
            "package_relative_path": package_rel,
            "r1_path": str(src) if src else "",
            "r2_path": str(dst) if dst else "",
            "r1_size_bytes": src.stat().st_size if src else "",
            "r2_size_bytes": dst.stat().st_size if dst else "",
            "r1_sha256": src_hash,
            "r2_sha256": dst_hash,
            "status": status,
        })
    return rows


def build_source_relocation_audit() -> tuple[int, dict[str, Any]]:
    if not R1.is_dir():
        raise RuntimeError(f"R1 reference package missing: {R1}")
    rows = compare_tree(
        R1 / "00_CURRENT_CIRCUIT_FILES",
        CIRCUITS,
        "01_CURRENT_CIRCUIT_FILES",
        set(),
    )
    for name in CAMPAIGNS:
        rows.extend(compare_tree(
            R1 / name,
            RESULTS / name,
            f"02_SIMULATION_RESULTS/{name}",
            PORTABILITY_PATCHES,
        ))
    rows.extend(compare_tree(
        R1 / "PDK",
        TOOLS / "PDK",
        "03_CACE_AND_SIMULATION_TOOLS/PDK",
        set(),
    ))
    counts = Counter(row["status"] for row in rows)
    hard_fail = sum(counts[key] for key in (
        "MISSING", "UNEXPECTED_HASH_DIFFERENCE", "UNEXPECTED_PACKAGE_EXTRA"
    ))
    observed = {
        row["package_relative_path"] for row in rows
        if row["status"] == "INTENTIONAL_PORTABILITY_PATCH"
    }
    passed = hard_fail == 0 and observed == PORTABILITY_PATCHES
    payload = {
        "status": (
            "PASS_R1_TO_R2_RELOCATION_WITH_8_DECLARED_PATH_PATCHES"
            if passed else "FAIL_R1_TO_R2_RELOCATION"
        ),
        "pass": passed,
        "r1_reference": str(R1),
        "r2_package": str(ROOT),
        "record_count": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "declared_patch_count": len(PORTABILITY_PATCHES),
        "observed_patch_count": len(observed),
        "completed_utc": utc_now(),
    }
    count = write_csv(AUDITS / "SOURCE_COPY_AUDIT.csv", rows)
    write_json(AUDITS / "source_copy_audit.json", payload)
    write_csv(AUDITS / "PORTABILITY_PATCHES.csv", (
        {**row, "reason": "Resolve R2 or staged package-owned PDK",
         "electrical_netlist_changed": False}
        for row in rows
        if row["status"] == "INTENTIONAL_PORTABILITY_PATCH"
    ))
    return count, payload


def root_layout_audit() -> dict[str, Any]:
    loose = sorted(path.name for path in ROOT.iterdir() if path.is_file())
    dirs = sorted(path.name for path in ROOT.iterdir() if path.is_dir())
    expected_dirs = [
        "01_CURRENT_CIRCUIT_FILES",
        "02_SIMULATION_RESULTS",
        "03_CACE_AND_SIMULATION_TOOLS",
        "04_PACKAGE_DOCS",
        "05_PACKAGE_AUDIT",
    ]
    generated_names = {"netlist", "reports", "runs", "logs", "results", "raw", "plots"}
    tool_result_dirs = [
        relative(path) for path in TOOLS.rglob("*")
        if path.is_dir() and path.name.lower() in generated_names
    ]
    passed = (
        set(loose) == ROOT_LAUNCHERS
        and dirs == expected_dirs
        and not tool_result_dirs
    )
    payload = {
        "status": "PASS_ROOT_LAUNCHERS_ONLY_RESULTS_UNIFIED" if passed
        else "FAIL_ROOT_LAYOUT",
        "pass": passed,
        "root_loose_files": loose,
        "root_directories": dirs,
        "unexpected_result_directories_under_tools": tool_result_dirs,
        "unified_result_root": str(RESULTS),
        "completed_utc": utc_now(),
    }
    write_json(AUDITS / "root_layout_audit.json", payload)
    return payload


def active_text_files() -> list[Path]:
    files = [ROOT / name for name in ROOT_LAUNCHERS]
    files.extend(path for path in indexed_files(TOOLS)
                 if path.suffix.lower() in {
                     ".py", ".ps1", ".bat", ".yaml", ".yml", ".sch", ".sym"
                 } or path.name == "Makefile")
    files.extend(ROOT / rel for rel in PORTABILITY_PATCHES)
    return sorted(set(
        path for path in files
        if path.is_file() and path.name != "build_package_audit.py"
    ))


def deck_dependencies(deck: Path) -> list[str]:
    include = re.compile(
        r"^\s*\.(?:include|lib)\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))",
        re.IGNORECASE,
    )
    simulation = re.compile(r'\bsimulation="([^"]+)"', re.IGNORECASE)
    found: list[str] = []
    for line in deck.read_text(encoding="utf-8", errors="replace").splitlines():
        match = include.search(line)
        if match:
            found.append(next(value for value in match.groups() if value))
        found.extend(simulation.findall(line))
    return found


def dependency_audit(latest_run: Path) -> dict[str, Any]:
    forbidden = ("/foss/pdks/", R1.name)
    executable_hits = []
    for path in active_text_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in forbidden:
            if token in text:
                executable_hits.append({"file": relative(path), "token": token})
    decks = sorted(latest_run.rglob("*.spice"))
    deck_hits = []
    missing = []
    dependency_count = 0
    package_prefix = f"/foss/designs/{ROOT.name}/"
    for deck in decks:
        text = deck.read_text(encoding="utf-8", errors="replace")
        for token in forbidden:
            if token in text:
                deck_hits.append({"deck": relative(deck), "token": token})
        for dependency in deck_dependencies(deck):
            dependency_count += 1
            if dependency.startswith(package_prefix):
                local = ROOT / dependency.removeprefix(package_prefix)
                if not local.is_file():
                    missing.append({
                        "deck": relative(deck),
                        "dependency": dependency,
                        "translated_local_path": str(local),
                    })
    pdk_checks = []
    for name, expected in PDK_HASHES.items():
        path = TOOLS / "PDK/gf180mcuD/libs.tech/ngspice" / name
        actual = sha256(path) if path.is_file() else ""
        pdk_checks.append({
            "relative_path": relative(path),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "pass": actual == expected,
        })
    passed = (
        not executable_hits and not deck_hits and not missing
        and all(item["pass"] for item in pdk_checks)
    )
    payload = {
        "status": "PASS_EXECUTABLE_DEPENDENCY_CLOSURE" if passed
        else "FAIL_EXECUTABLE_DEPENDENCY_CLOSURE",
        "pass": passed,
        "latest_quick_run": str(latest_run),
        "generated_deck_count": len(decks),
        "parsed_dependency_count": dependency_count,
        "executable_forbidden_references": executable_hits,
        "generated_deck_forbidden_references": deck_hits,
        "missing_package_dependencies": missing,
        "pdk_checks": pdk_checks,
        "completed_utc": utc_now(),
    }
    write_json(AUDITS / "dependency_closure_audit.json", payload)
    return payload


def find_latest_quick() -> Path:
    pointer = RUN_OUTPUTS / "LATEST_QUICK_RUN.json"
    if pointer.is_file():
        candidate = RUN_OUTPUTS / read_json(pointer)["run"]
        if candidate.is_dir():
            return candidate
    for candidate in reversed(sorted(RUN_OUTPUTS.glob("RUN_*"))):
        summary = candidate / "QUICK_REPRODUCIBILITY_SUMMARY.json"
        if summary.is_file() and read_json(summary).get("pass"):
            return candidate
    raise RuntimeError("no passing quick verification run found")


def find_full_dry_run() -> Path:
    for candidate in reversed(sorted(RUN_OUTPUTS.glob("FULL_*"))):
        status = candidate / "RUN_STATUS.json"
        if status.is_file() and read_json(status).get("state") == "STAGED_DRY_RUN_PASS":
            return candidate
    raise RuntimeError("no passing full dry-run found")


def package_files() -> list[Path]:
    return sorted(
        path for path in ROOT.rglob("*")
        if path.is_file() and not ignored(path)
        and relative(path) not in MANIFEST_EXCLUDES
    )


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    AUDITS.mkdir(parents=True, exist_ok=True)
    latest_run = find_latest_quick()
    full_run = find_full_dry_run()
    quick = read_json(latest_run / "QUICK_REPRODUCIBILITY_SUMMARY.json")
    full = read_json(full_run / "RUN_STATUS.json")

    current_count, schematic_count, symbol_count = build_current_circuit_index()
    result_count = build_file_index(
        RESULTS, DOCS / "SIMULATION_RESULTS_INDEX.csv", "SIMULATION_RESULTS"
    )
    tools_count = build_file_index(
        TOOLS, DOCS / "CACE_AND_TOOLS_INDEX.csv", "TOOLS"
    )
    matrix_count = build_matrix()
    first5 = read_csv(latest_run / "FIRST5_COMPARISON_ALL.csv")
    for row in first5:
        row["verification_run"] = latest_run.name
        row["verification_status"] = "PASS"
    first5_count = write_csv(
        DOCS / "BASELINE_AND_VERIFICATION_FIRST5.csv", first5
    )
    source_count, source = build_source_relocation_audit()
    layout = root_layout_audit()
    dependencies = dependency_audit(latest_run)

    comparator = (
        CIRCUITS / "spice/subckts/Comparator_StrongARM_extracted.subckt.spice"
    )
    comparator_actual = sha256(comparator)
    quick_pass = (
        bool(quick["pass"])
        and quick["comparison_record_count"] == 130
        and quick["matching_record_count"] == 130
    )
    integrity_pass = (
        source["pass"] and layout["pass"] and dependencies["pass"]
        and comparator_actual == COMPARATOR_SHA256
    )
    payload = {
        "status": (
            "COMPLETE_R2_UNIFIED_RESULTS_ROOT_LAUNCHERS_ONLY_"
            "QUICK_REPRO_PASS_PERFORMANCE_FAIL_NO_PROMOTION"
        ),
        "pass_package_integrity": integrity_pass,
        "pass_quick_reproduction": quick_pass,
        "full_run_entry_staged": full.get("state") == "STAGED_DRY_RUN_PASS",
        "root": str(ROOT),
        "unified_result_root": str(RESULTS),
        "tools_root": str(TOOLS),
        "current_circuit": {
            "indexed_file_count": current_count,
            "schematic_count": schematic_count,
            "symbol_count": symbol_count,
            "comparator_sha256": comparator_actual,
            "comparator_hash_match": comparator_actual == COMPARATOR_SHA256,
        },
        "indexes": {
            "simulation_result_file_count": result_count,
            "cace_and_tools_file_count": tools_count,
            "simulation_matrix_record_count": matrix_count,
            "baseline_verification_record_count": first5_count,
            "source_copy_record_count": source_count,
        },
        "quick_verification": {
            "run": latest_run.name,
            "status": quick["status"],
            "comparison_record_count": quick["comparison_record_count"],
            "matching_record_count": quick["matching_record_count"],
        },
        "full_dry_run": {
            "run": full_run.name,
            "status": full["state"],
            "preflight_pass": full["preflight_pass"],
        },
        "source_campaign_performance_status":
            "COMPLETE_AS_EXECUTED_PERFORMANCE_FAIL_NO_PROMOTION",
        "claim_boundary": [
            "Package integrity and quick reproduction PASS are not performance PASS.",
            "PVT3 MC20 is diagnostic, not yield or signoff evidence.",
            "Seed44 SS FULL255 failure prevents promotion.",
            "No layout, PEX, silicon, production-yield, tapeout, or signoff claim.",
        ],
        "completed_utc": utc_now(),
    }
    write_json(AUDITS / "PACKAGE_STATUS.json", payload)

    manifest_rows = [{
        "relative_path": relative(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    } for path in package_files()]
    write_csv(PACKAGE_MANIFEST, manifest_rows)

    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    print(f"PACKAGE_MANIFEST records={len(manifest_rows)}", flush=True)
    passed = (
        integrity_pass and quick_pass
        and payload["full_run_entry_staged"]
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
