import json
import math

from sar_campaign_common import (
    FRAME_DEFAULT_S,
    LSB_DIFF_V,
    PVT_CASES,
    ROOT,
    decode_frames,
    ensure_directories,
    run_deck,
    write_csv,
)
from sar_event_noise import ROBUST_GEAR_OPTIONS


JOB_DIR = ROOT / "jobs" / "dynamic_mc200_fast64"
LOG_DIR = ROOT / "logs" / "dynamic_mc200_fast64"
CSV_DIR = ROOT / "csv"
REPORT_DIR = ROOT / "reports"
RESULT_DIR = ROOT / "results"
SOURCE_STEM = "fast64_s001_n100001_main"
ROBUST_STEM = "fast64_s001_n100001_solver_profile_equivalence_robust50"


def main():
    ensure_directories(JOB_DIR, LOG_DIR, CSV_DIR, REPORT_DIR, RESULT_DIR)
    source_path = JOB_DIR / f"{SOURCE_STEM}.spice"
    source_deck = source_path.read_text(encoding="ascii")
    option_lines = [
        line for line in source_deck.splitlines() if line.startswith(".options ")
    ]
    if len(option_lines) != 1:
        raise RuntimeError("source deck must contain exactly one .options line")
    robust_deck = source_deck.replace(option_lines[0], ROBUST_GEAR_OPTIONS, 1)
    old_tran = "tran 5e-10 3.1995e-05 0 1e-10"
    new_tran = "tran 5e-10 3.1995e-05 0 5e-11"
    if robust_deck.count(old_tran) != 1:
        raise RuntimeError("source deck transient command is not the expected FAST64 command")
    robust_deck = robust_deck.replace(old_tran, new_tran, 1)
    robust_deck = robust_deck.replace(
        "* A44 actual analog core with fixed TT timed behavioral SAR control.\n",
        "* A44 actual analog core with fixed TT timed behavioral SAR control.\n"
        "* SOLVER_PROFILE_EQUIVALENCE ROBUST_GEAR maxstep_s=5e-11\n",
        1,
    )

    default = run_deck(source_deck, SOURCE_STEM, JOB_DIR, LOG_DIR, timeout_s=7200)
    robust = run_deck(robust_deck, ROBUST_STEM, JOB_DIR, LOG_DIR, timeout_s=7200)
    default_frames = decode_frames(
        default, 64, PVT_CASES["TT_3P3_27C"]["vdd_v"], FRAME_DEFAULT_S
    )
    robust_frames = decode_frames(
        robust, 64, PVT_CASES["TT_3P3_27C"]["vdd_v"], FRAME_DEFAULT_S
    )
    rows = []
    for default_frame, robust_frame in zip(default_frames, robust_frames):
        sampled_delta_lsb = (
            (robust_frame["sampled_diff_v"] - default_frame["sampled_diff_v"])
            / LSB_DIFF_V
        )
        complete_delta_ps = (
            robust_frame["complete_time_s"] - default_frame["complete_time_s"]
        ) * 1e12
        rows.append(
            {
                "frame_index": default_frame["frame_index"],
                "default_code": default_frame["code"],
                "robust_code": robust_frame["code"],
                "code_match": default_frame["code"] == robust_frame["code"],
                "default_valid": default_frame["valid"],
                "robust_valid": robust_frame["valid"],
                "sampled_delta_lsb": sampled_delta_lsb,
                "complete_time_delta_ps": complete_delta_ps,
            }
        )
    write_csv(CSV_DIR / "solver_profile_equivalence_fast64.csv", rows)
    finite_sampled = [
        abs(float(row["sampled_delta_lsb"]))
        for row in rows
        if math.isfinite(float(row["sampled_delta_lsb"]))
    ]
    finite_complete = [
        abs(float(row["complete_time_delta_ps"]))
        for row in rows
        if math.isfinite(float(row["complete_time_delta_ps"]))
    ]
    payload = {
        "status": (
            "PASS"
            if default["returncode"] == 0
            and robust["returncode"] == 0
            and all(row["default_valid"] and row["robust_valid"] for row in rows)
            and all(row["code_match"] for row in rows)
            and max(finite_sampled, default=float("inf")) <= 0.01
            else "FAIL"
        ),
        "default_stem": SOURCE_STEM,
        "robust_stem": ROBUST_STEM,
        "frames": len(rows),
        "code_mismatch_count": sum(not row["code_match"] for row in rows),
        "default_invalid_count": sum(not row["default_valid"] for row in rows),
        "robust_invalid_count": sum(not row["robust_valid"] for row in rows),
        "max_abs_sampled_delta_lsb": max(finite_sampled, default=float("inf")),
        "max_abs_complete_time_delta_ps": max(finite_complete, default=float("inf")),
        "default_returncode": default["returncode"],
        "robust_returncode": robust["returncode"],
    }
    (RESULT_DIR / "solver_profile_equivalence.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    lines = [
        "# Solver Profile Equivalence",
        "",
        f"- Status: `{payload['status']}`",
        f"- Frames: `{payload['frames']}`",
        f"- Code mismatches: `{payload['code_mismatch_count']}`",
        f"- Maximum sampled-input delta: `{payload['max_abs_sampled_delta_lsb']:.9g} LSB`",
        f"- Maximum completion-time delta: `{payload['max_abs_complete_time_delta_ps']:.9g} ps`",
        "- Compared profiles: `DEFAULT 100 ps` versus `ROBUST_GEAR 50 ps`",
        "- Electrical stimulus, mismatch seed, noise seed, event draws, and phase are identical.",
    ]
    (REPORT_DIR / "solver_profile_equivalence.md").write_text(
        "\n".join(lines) + "\n", encoding="ascii"
    )
    print(json.dumps(payload, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
