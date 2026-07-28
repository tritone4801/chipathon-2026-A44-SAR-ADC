"""Shared ideal SAR ADC validation utilities."""

from __future__ import annotations

import csv
import importlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np

try:
    import yaml
except Exception:  # pragma: no cover - fallback for preflight diagnostics
    yaml = None

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
CONFIG_PATH = ROOT / "config" / "sar_adc.yaml"
RESULTS = ROOT / "results"
CSV_DIR = RESULTS / "csv"
RAW_DIR = RESULTS / "raw"
PLOTS_DIR = RESULTS / "plots"
LOGS_DIR = RESULTS / "logs"
REPORT_DIR = ROOT / "report"
METRICS_JSON = RESULTS / "metrics.json"
METRICS_CSV = CSV_DIR / "metrics.csv"


def ensure_dirs() -> None:
    for path in [CSV_DIR, RAW_DIR, PLOTS_DIR, LOGS_DIR, REPORT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to load config/sar_adc.yaml")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def derived_values(cfg: Dict[str, Any]) -> Dict[str, Any]:
    bits = int(cfg["adc"]["bits"])
    codes = 1 << bits
    vrefp = float(cfg["adc"]["vrefp_v"])
    vrefn = float(cfg["adc"]["vrefn_v"])
    vfs_peak = vrefp - vrefn
    vmin = -vfs_peak
    vmax = +vfs_peak
    lsb = (vmax - vmin) / codes
    fs = float(cfg["adc"]["fs_hz"])
    sample_period_s = 1.0 / fs
    clks_hz = float(cfg["timing"].get("clks_hz", fs))
    track_time_s = float(cfg["timing"].get("track_time_s", 0.25 * sample_period_s))
    conversion_time_s = float(cfg["timing"].get("conversion_time_s", sample_period_s - track_time_s))
    internal_bit_slots = int(cfg["timing"].get("internal_bit_slots", bits))
    internal_bit_slot_period_s = conversion_time_s / internal_bit_slots
    internal_bit_slot_hz = 1.0 / internal_bit_slot_period_s
    # Backward-compatible aliases for older helper code. These are internal bit slots,
    # not an external SAR clock.
    fclk = float(cfg["timing"].get("sar_clock_hz", internal_bit_slot_hz))
    cycles = int(cfg["timing"].get("cycles_per_conversion", internal_bit_slots))
    return {
        "bits": bits,
        "codes": codes,
        "max_code": codes - 1,
        "vrefp": vrefp,
        "vrefn": vrefn,
        "vcm": float(cfg["adc"]["vcm_v"]),
        "vfs_diff_peak": vfs_peak,
        "vfs_diff_pp": 2.0 * vfs_peak,
        "vmin": vmin,
        "vmax": vmax,
        "lsb": lsb,
        "fs_hz": fs,
        "clks_hz": clks_hz,
        "track_time_s": track_time_s,
        "conversion_time_s": conversion_time_s,
        "comparisons_per_conversion": int(cfg["timing"].get("comparisons_per_conversion", bits)),
        "cdac_adjustments_per_conversion": int(cfg["timing"].get("cdac_adjustments_per_conversion", bits - 1)),
        "internal_bit_slots": internal_bit_slots,
        "internal_bit_slot_period_s": internal_bit_slot_period_s,
        "internal_bit_slot_hz": internal_bit_slot_hz,
        "sar_clock_hz": fclk,
        "cycles_per_conversion": cycles,
        "sample_rate_from_clock_hz": clks_hz,
        "sample_period_s": sample_period_s,
        "sar_clock_period_s": internal_bit_slot_period_s,
    }


def direct_quantize(vdiff: Any, cfg: Dict[str, Any]) -> Any:
    d = derived_values(cfg)
    x = (np.asarray(vdiff, dtype=float) - d["vmin"]) / d["lsb"]
    code = np.floor(x + 1e-12).astype(np.int64)
    if cfg["adc"].get("saturation", True):
        code = np.clip(code, 0, d["max_code"])
    if np.isscalar(vdiff):
        return int(code)
    return code


def oracle_quantize(vdiff: Any, cfg: Dict[str, Any]) -> Any:
    """Independent scalar-loop oracle for the ideal transfer curve."""

    d = derived_values(cfg)

    def one(value: float) -> int:
        code = math.floor((float(value) - d["vmin"]) / d["lsb"] + 1e-12)
        if bool(cfg["adc"].get("saturation", True)):
            code = min(max(code, 0), d["max_code"])
        return int(code)

    if np.isscalar(vdiff):
        return one(float(vdiff))
    return np.array([one(v) for v in np.asarray(vdiff, dtype=float)], dtype=np.int64)


def dac_threshold(code: Any, cfg: Dict[str, Any]) -> Any:
    d = derived_values(cfg)
    result = d["vmin"] + np.asarray(code, dtype=float) * d["lsb"]
    if np.isscalar(code):
        return float(result)
    return result


def dac_center(code: Any, cfg: Dict[str, Any]) -> Any:
    d = derived_values(cfg)
    result = d["vmin"] + (np.asarray(code, dtype=float) + 0.5) * d["lsb"]
    if np.isscalar(code):
        return float(result)
    return result


def sar_convert_scalar(vdiff: float, cfg: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]]]:
    d = derived_values(cfg)
    code = 0
    trace: List[Dict[str, Any]] = []
    for bit in range(d["bits"] - 1, -1, -1):
        trial_code = code | (1 << bit)
        threshold = float(dac_threshold(trial_code, cfg))
        decision = bool(float(vdiff) >= threshold - 1e-12)
        if decision:
            code = trial_code
        trace.append(
            {
                "bit_index": bit,
                "trial_code": trial_code,
                "threshold_v": threshold,
                "comparator_decision": int(decision),
                "partial_code": code,
            }
        )
    return code, trace


def sar_quantize(vdiff: Any, cfg: Dict[str, Any]) -> Any:
    if np.isscalar(vdiff):
        return sar_convert_scalar(float(vdiff), cfg)[0]
    return np.array(
        [sar_convert_scalar(float(v), cfg)[0] for v in np.asarray(vdiff, dtype=float)],
        dtype=np.int64,
    )


def vinp_vinn_from_vdiff(vdiff: Any, cfg: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
    d = derived_values(cfg)
    arr = np.asarray(vdiff, dtype=float)
    return d["vcm"] + arr / 2.0, d["vcm"] - arr / 2.0


def coherent_sine(
    npts: int, bin_index: int, amplitude_fs_peak: float, phase: float, cfg: Dict[str, Any]
) -> np.ndarray:
    d = derived_values(cfg)
    n = np.arange(npts)
    amp_v = amplitude_fs_peak * d["vfs_diff_peak"]
    return amp_v * np.sin(2.0 * np.pi * bin_index * n / npts + phase)


def fold_harmonic_bin(k: int, harmonic: int, npts: int) -> int:
    raw = (k * harmonic) % npts
    return raw if raw <= npts // 2 else npts - raw


def power_spectrum(x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    arr = np.asarray(x, dtype=float)
    arr = arr - np.mean(arr)
    npts = arr.size
    spectrum = np.fft.rfft(arr)
    power = (np.abs(spectrum) ** 2) / (npts**2)
    if npts > 2:
        power[1:-1] *= 2.0
    freqs_bin = np.arange(power.size)
    return freqs_bin, power


def db10(value: float) -> float:
    if value <= 0.0:
        return math.inf
    return 10.0 * math.log10(value)


def finite_or_inf_ratio_db(num: float, den: float) -> float:
    if den <= np.finfo(float).tiny:
        return math.inf
    return db10(num / den)


def spectral_metrics(
    signal: np.ndarray,
    input_signal: np.ndarray,
    fundamental_bin: int,
    cfg: Dict[str, Any],
) -> Dict[str, Any]:
    npts = len(signal)
    harmonics = int(
        cfg["dynamic_test"]["quantization_metrics"].get(
            "quantization_distortion_harmonics", cfg["dynamic_test"].get("harmonics", 10)
        )
    )
    bins, power = power_spectrum(signal)
    fund = int(fundamental_bin)
    harmonic_bins: List[int] = []
    for h in range(2, harmonics + 1):
        hb = fold_harmonic_bin(fund, h, npts)
        if hb not in (0, fund, npts // 2) and hb not in harmonic_bins:
            harmonic_bins.append(hb)
    psignal = float(power[fund])
    pdc = float(np.mean(signal) ** 2)
    pharm = float(np.sum(power[harmonic_bins])) if harmonic_bins else 0.0
    excluded = {0, fund}
    excluded.update(harmonic_bins)
    if npts % 2 == 0:
        excluded.add(npts // 2)
    mask = np.ones_like(power, dtype=bool)
    for idx in excluded:
        if 0 <= idx < mask.size:
            mask[idx] = False
    pnonharm = float(np.sum(power[mask]))
    ptotal_err = float(np.mean((np.asarray(signal) - np.asarray(input_signal)) ** 2))
    ps_time = float(np.mean((np.asarray(input_signal) - np.mean(input_signal)) ** 2))
    spur_candidates = np.copy(power)
    spur_candidates[0] = 0.0
    spur_candidates[fund] = 0.0
    pspur = float(np.max(spur_candidates))
    spur_bin = int(np.argmax(spur_candidates))
    sqnr_td = finite_or_inf_ratio_db(ps_time, ptotal_err)
    sqnr_spectral = finite_or_inf_ratio_db(psignal, pnonharm)
    sqdr = finite_or_inf_ratio_db(psignal, pharm)
    sqndr = finite_or_inf_ratio_db(psignal, pnonharm + pharm)
    thd_db = -math.inf if pharm <= 0.0 else db10(pharm / psignal)
    sfdr_db = finite_or_inf_ratio_db(psignal, pspur)
    enob = (sqndr - 1.76) / 6.02 if math.isfinite(sqndr) else math.inf
    closure_left = 10.0 ** (-sqndr / 10.0) if math.isfinite(sqndr) else 0.0
    closure_right = (
        (10.0 ** (-sqnr_spectral / 10.0) if math.isfinite(sqnr_spectral) else 0.0)
        + (10.0 ** (-sqdr / 10.0) if math.isfinite(sqdr) else 0.0)
    )
    closure_error_db = 0.0
    if closure_left > 0.0 and closure_right > 0.0:
        closure_error_db = abs(db10(closure_left / closure_right))
    return {
        "fundamental_bin": fund,
        "harmonic_bins": harmonic_bins,
        "largest_spur_bin": spur_bin,
        "Psignal": psignal,
        "Pdc": pdc,
        "Pqn": pnonharm,
        "Pqd": pharm,
        "Pquant_error_total": ptotal_err,
        "SQNR_total_TD_dB": sqnr_td,
        "SQNR_spectral_dB": sqnr_spectral,
        "SQDR_dB": sqdr,
        "SQNDR_dB": sqndr,
        "SNR_dB": sqnr_spectral,
        "SNDR_dB": sqndr,
        "SFDR_dB": sfdr_db,
        "THD_dB": thd_db,
        "ENOB_bit": enob,
        "closure_error_db": closure_error_db,
        "power_bins": bins.tolist(),
        "power": power.tolist(),
    }


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], fieldnames: List[str] | None = None) -> None:
    ensure_dirs()
    rows = list(rows)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_json(path: Path = METRICS_JSON) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(data: Dict[str, Any], path: Path = METRICS_JSON) -> None:
    ensure_dirs()
    with path.open("w", encoding="utf-8") as fh:
        json.dump(to_jsonable(data), fh, indent=2, sort_keys=True)


def to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [to_jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, Path):
        return str(value)
    return value


def update_metrics(section: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = read_json()
    data[section] = payload
    data["last_updated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    write_json(data)
    return data


def metric_status(value: float, limit: float, op: str = "<=") -> str:
    if not math.isfinite(float(value)):
        return "FAIL"
    if op == "<=":
        return "PASS" if abs(float(value)) <= limit else "FAIL"
    if op == ">=":
        return "PASS" if float(value) >= limit else "FAIL"
    raise ValueError(op)


def command_probe(name: str, version_args: List[str] | None = None) -> Dict[str, Any]:
    exe = shutil.which(name)
    row: Dict[str, Any] = {"tool": name, "path": exe or "", "status": "MISSING", "version": ""}
    if exe is None:
        return row
    row["status"] = "FOUND"
    args = version_args or ["--version"]
    try:
        cp = subprocess.run(
            [exe, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
            cwd=str(ROOT),
        )
        first = (cp.stdout or "").strip().splitlines()
        row["version"] = first[0] if first else f"exit={cp.returncode}"
        row["status"] = "PASS" if cp.returncode == 0 else "FOUND"
    except Exception as exc:
        row["version"] = repr(exc)
        row["status"] = "FOUND"
    return row


def import_probe(module_name: str) -> Dict[str, Any]:
    try:
        module = importlib.import_module(module_name)
        return {
            "module": module_name,
            "status": "PASS",
            "version": str(getattr(module, "__version__", "installed")),
        }
    except Exception as exc:
        return {"module": module_name, "status": "MISSING", "version": repr(exc)}


def plot_line(path: Path, x: Any, ys: Dict[str, Any], title: str, xlabel: str, ylabel: str) -> None:
    ensure_dirs()
    plt.figure(figsize=(8, 4.5))
    for label, y in ys.items():
        plt.plot(x, y, label=label)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    if len(ys) > 1:
        plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=140)
    plt.close()


def plot_bar(path: Path, x: Any, y: Any, title: str, xlabel: str, ylabel: str) -> None:
    ensure_dirs()
    plt.figure(figsize=(8, 4.5))
    plt.bar(x, y, width=0.9)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=140)
    plt.close()


def plot_spectrum(path: Path, metrics: Dict[str, Any], cfg: Dict[str, Any], title: str) -> None:
    bins = np.array(metrics["power_bins"])
    power = np.array(metrics["power"])
    fs = float(cfg["adc"]["fs_hz"])
    freqs = bins * fs / (2 * (len(power) - 1))
    pmax = max(float(np.max(power)), np.finfo(float).tiny)
    dbfs = 10.0 * np.log10(np.maximum(power, np.finfo(float).tiny) / pmax)
    plt.figure(figsize=(9, 4.8))
    plt.plot(freqs / 1e6, dbfs, linewidth=0.8)
    fund = metrics["fundamental_bin"]
    plt.scatter([fund * fs / (2 * (len(power) - 1)) / 1e6], [dbfs[fund]], color="red", label="fund")
    for hb in metrics["harmonic_bins"]:
        plt.scatter([hb * fs / (2 * (len(power) - 1)) / 1e6], [dbfs[hb]], color="orange", s=20)
    plt.title(
        f"{title}\nSNDR={metrics['SNDR_dB']:.2f} dB, SQNR={metrics['SQNR_spectral_dB']:.2f} dB, "
        f"SQDR={format_db(metrics['SQDR_dB'])}, ENOB={metrics['ENOB_bit']:.2f}"
    )
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Power relative to largest bin (dB)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=140)
    plt.close()


def format_db(value: float) -> str:
    if value == math.inf:
        return "+inf dB"
    if value == -math.inf:
        return "-inf dB"
    return f"{value:.2f} dB"


def required_input_file_rows() -> List[Dict[str, Any]]:
    paths = [
        Path("D:/PICO/current_goal.md"),
        REPO_ROOT / "README.md",
        REPO_ROOT / "Makefile",
        REPO_ROOT / "docs" / "reproducing-docker.md",
        REPO_ROOT / "docs" / "reproducing-native.md",
        REPO_ROOT / "cocotb" / "chip_top_tb.py",
        REPO_ROOT / "src" / "chip_core.sv",
        Path("C:/Users/15031/eda/designs/sscs-chipathon-2026/resources/Analog/eda/README.md"),
    ]
    rows = []
    for p in paths:
        exists = p.exists()
        rows.append(
            {
                "path": str(p),
                "status": "READ" if exists else "MISSING",
                "bytes": p.stat().st_size if exists else 0,
            }
        )
    return rows


def write_text(path: Path, text: str) -> None:
    ensure_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def short_env_summary() -> Dict[str, Any]:
    return {
        "python": sys.executable,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "root": str(ROOT),
    }
