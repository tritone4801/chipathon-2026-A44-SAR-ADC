#!/usr/bin/env python3
"""Re-run the first five jobs and first five retained W4 records per dynamic lane."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", action="append", required=True)
    parser.add_argument("--jobs-per-phase", type=int, default=5)
    parser.add_argument(
        "--frames",
        type=int,
        default=5,
        help="Number of retained W4 records to compare (frames 4 onward).",
    )
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    campaign = args.campaign.resolve()
    output = args.output.resolve()
    scripts = campaign / "scripts"
    sys.path.insert(0, str(scripts))

    import fast64_v2_common as fast  # type: ignore
    import sar_campaign_common as common  # type: ignore
    import sar_event_noise as event_noise  # type: ignore

    matrix = read_csv(campaign / "manifests" / "job_matrix.csv")
    selected: list[dict[str, str]] = []
    for phase in args.phase:
        rows = [row for row in matrix if row["phase"] == phase]
        if len(rows) < args.jobs_per_phase:
            raise SystemExit(
                f"{campaign.name}:{phase} has {len(rows)} jobs, "
                f"expected at least {args.jobs_per_phase}"
            )
        selected.extend(rows[: args.jobs_per_phase])

    grouped_weights = common.load_cdac_weights()
    timing = json.loads(
        (campaign / "config" / "timing_tt_3p3_27c.json").read_text(
            encoding="utf-8"
        )
    )

    def run_job(job: dict[str, str]) -> dict[str, Any]:
        job_id = job["job_id"]
        phase = job["phase"]
        seed = int(job["mismatch_seed"])
        noise_seed = int(job["noise_seed"])
        band = job["band"]
        pvt = job["pvt"]
        maxstep_ps = int(job["maxstep_ps"])
        baseline_path = campaign / "csv" / "job_codes" / f"{job_id}.csv"
        baseline_all = read_csv(baseline_path)
        baseline = [
            row
            for row in baseline_all
            if row["retained"].strip().lower() == "true"
        ][: args.frames]
        if len(baseline) != args.frames:
            raise RuntimeError(
                f"{job_id}: baseline has {len(baseline)} retained W4 prefix rows"
            )
        first_retained_frame = int(baseline[0]["frame_index"])
        if first_retained_frame != int(job["warmup_frames"]):
            raise RuntimeError(
                f"{job_id}: first retained frame {first_retained_frame} does "
                f"not match warmup_frames={job['warmup_frames']}"
            )
        total_frames = int(baseline[-1]["frame_index"]) + 1

        ideal = fast.coherent_input_values(
            total_frames, band, common.TRACK_FALL_OFFSET_S
        )
        draws = event_noise.frozen_event_draws(noise_seed, total_frames)
        commanded = ideal + draws["sample_draws_v"]
        deck = common.build_deck(
            input_spec={
                "kind": "static_sequence",
                "vid_values": commanded,
            },
            total_frames=total_frames,
            frame_s=fast.FRAME_PERIOD_S,
            maxstep_s=maxstep_ps * 1e-12,
            pvt_name=pvt,
            mismatch_seed=seed,
            grouped_weights=grouped_weights,
        )
        deck = event_noise.apply_solver_profile(deck, "ROBUST_GEAR")
        deck = event_noise.add_comparator_event_noise(
            deck,
            draws["comparator_draws_v"],
            fast.FRAME_PERIOD_S,
            timing,
            (
                f"A44_REPRO_W4_FIRST5 job={job_id} noise_seed={noise_seed} "
                f"sample_sigma_v={event_noise.SAMPLE_SIGMA_V:.17g} "
                f"comparator_sigma_v={event_noise.COMPARATOR_SIGMA_V:.17g} "
                "solver_profile=ROBUST_GEAR"
            ),
        )
        job_root = output / phase / job_id
        run = common.run_deck(
            deck,
            "w4_first5",
            job_root / "jobs",
            job_root / "logs",
            timeout_s=1200,
            cache_completed_failure=False,
        )
        frames = common.decode_frames(
            run,
            total_frames,
            common.PVT_CASES[pvt]["vdd_v"],
            fast.FRAME_PERIOD_S,
        )
        rows: list[dict[str, Any]] = []
        for comparison_index, reference in enumerate(baseline):
            frame_index = int(reference["frame_index"])
            frame = frames[frame_index]
            expected_code = int(reference["code"])
            actual_code = int(frame["code"])
            expected_commanded = float(reference["commanded_vid_v"])
            input_match = math.isclose(
                float(commanded[frame_index]),
                expected_commanded,
                rel_tol=0.0,
                abs_tol=5e-15,
            )
            valid_match = bool(frame["valid"]) == (
                reference["valid"].strip().lower() == "true"
            )
            row_pass = (
                int(run["returncode"]) == 0
                and not bool(run.get("simulation_aborted"))
                and input_match
                and valid_match
                and actual_code == expected_code
            )
            rows.append(
                {
                    "campaign": campaign.name,
                    "phase": phase,
                    "job_id": job_id,
                    "pvt": pvt,
                    "mismatch_seed": seed,
                    "noise_seed": noise_seed,
                    "comparison_index": comparison_index,
                    "frame_index": frame_index,
                    "view": reference["view"],
                    "retained": reference["retained"],
                    "expected_commanded_vid_v": expected_commanded,
                    "actual_commanded_vid_v": float(commanded[frame_index]),
                    "commanded_input_match": input_match,
                    "expected_code": expected_code,
                    "actual_code": actual_code,
                    "code_match": actual_code == expected_code,
                    "expected_valid": reference["valid"],
                    "actual_valid": bool(frame["valid"]),
                    "valid_match": valid_match,
                    "returncode": int(run["returncode"]),
                    "simulation_aborted": bool(run.get("simulation_aborted")),
                    "row_pass": row_pass,
                    "early_stop": "W4_FIRST5_RETAINED_FRAMES_4_TO_8",
                    "deck": str(run["deck"]),
                    "log": str(run["log"]),
                }
            )
        return {
            "job_id": job_id,
            "phase": phase,
            "rows": rows,
            "pass": all(row["row_pass"] for row in rows),
            "elapsed_s": float(run["elapsed_s"]),
            "returncode": int(run["returncode"]),
        }

    results: list[dict[str, Any]] = []
    exceptions: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=min(args.workers, len(selected))) as pool:
        futures = {pool.submit(run_job, job): job for job in selected}
        for future in as_completed(futures):
            job = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(
                    f"DYNAMIC_PREFIX5 {result['job_id']} "
                    f"pass={result['pass']} elapsed_s={result['elapsed_s']:.3f}",
                    flush=True,
                )
            except Exception:
                exceptions.append(
                    {
                        "job_id": job["job_id"],
                        "traceback": traceback.format_exc(),
                    }
                )

    results.sort(key=lambda row: row["job_id"])
    comparison_rows = [
        row
        for result in results
        for row in sorted(result["rows"], key=lambda item: item["frame_index"])
    ]
    write_csv(output / "dynamic_first5_comparison.csv", comparison_rows)
    summary = {
        "status": (
            "PASS_DYNAMIC_FIRST5_REPRODUCIBLE"
            if not exceptions
            and len(results) == len(selected)
            and all(result["pass"] for result in results)
            else "FAIL_DYNAMIC_FIRST5_REPRODUCIBILITY"
        ),
        "pass": (
            not exceptions
            and len(results) == len(selected)
            and all(result["pass"] for result in results)
        ),
        "campaign": campaign.name,
        "phases": args.phase,
        "jobs_per_phase": args.jobs_per_phase,
        "retained_records_per_job": args.frames,
        "warmup_frames_per_job": 4,
        "simulation_frames_per_job": 4 + args.frames,
        "selected_job_count": len(selected),
        "completed_job_count": len(results),
        "comparison_record_count": len(comparison_rows),
        "matching_record_count": sum(
            bool(row["row_pass"]) for row in comparison_rows
        ),
        "exceptions": exceptions,
        "early_stop_method": (
            "Each job runs the four diagnostic warm-up frames and compares the "
            "first five formal W4 retained records (frames 4-8). Frames 9-67 "
            "are not scheduled after those five retained records match."
        ),
        "completed_utc": utc_now(),
    }
    write_json(output / "dynamic_first5_summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    return 0 if summary["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
