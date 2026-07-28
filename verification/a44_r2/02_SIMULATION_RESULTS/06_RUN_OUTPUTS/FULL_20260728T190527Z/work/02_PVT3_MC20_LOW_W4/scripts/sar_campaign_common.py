#!/usr/bin/env python3
import csv
import math
import os
import re
import subprocess
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = ROOT.parents[1]
PDK_CANDIDATES = (
    PACKAGE_ROOT
    / "03_CACE_AND_SIMULATION_TOOLS"
    / "PDK"
    / "gf180mcuD"
    / "libs.tech"
    / "ngspice",
    ROOT.parent / "PDK" / "gf180mcuD" / "libs.tech" / "ngspice",
)
PDK = next((path for path in PDK_CANDIDATES if path.is_dir()), PDK_CANDIDATES[0])
NGSPICE = Path("/foss/tools/bin/ngspice")
NGSPICE_USERINIT_DIR = ROOT / "config" / "ngspice_userinit"
SWITCH = ROOT / "netlists" / "core" / "subckts" / "SWITCH_BOOT_SP_native_extracted.subckt.spice"
CDAC = ROOT / "netlists" / "core" / "subckts" / "CDAC_native_extracted.subckt.spice"
COMPARATOR = ROOT / "netlists" / "core" / "subckts" / "Comparator_StrongARM_extracted.subckt.spice"
LOADS = ROOT / "models" / "no_r6_equivalent_loads.inc"
BEHAVIOR_SO = ROOT / "models" / "SAR_LOGIC_BEH_TT_3P3_27C.so"
WEIGHTS_CSV = ROOT / "csv" / "cdac_mismatch_weights.csv"

BITS = 8
FULL_SCALE_DIFF_V = 3.4
LSB_DIFF_V = FULL_SCALE_DIFF_V / (1 << BITS)
VCM_V = 1.65
VREFP_V = 2.5
VREFN_V = 0.8
FRAME_DEFAULT_S = 500e-9
SAMPLE_EDGE_OFFSET_S = 50e-9
TRACK_FALL_OFFSET_S = 175e-9
APERTURE_GUARD_S = 20e-9
NUMERICAL_TIEBREAK_DIFF_V = 10.0e-6

PVT_CASES = {
    "TT_3P3_27C": {
        "name": "TT_3P3_27C",
        "model_section": "typical",
        "mim_section": "mimcap_typical",
        "vdd_v": 3.3,
        "temp_c": 27,
    },
    "SS_3P0_125C": {
        "name": "SS_3P0_125C",
        "model_section": "ss",
        "mim_section": "mimcap_ss",
        "vdd_v": 3.0,
        "temp_c": 125,
    },
    "FF_3P6_M40C": {
        "name": "FF_3P6_M40C",
        "model_section": "ff",
        "mim_section": "mimcap_ff",
        "vdd_v": 3.6,
        "temp_c": -40,
    },
}

ELEMENT_TO_INSTANCE = {
    "BIT1": "XC1",
    "BIT2": "XC2",
    "BIT3": "XC3",
    "BIT4": "XC4",
    "BIT5": "XC5",
    "BIT6": "XC6",
    "BIT7": "XC7",
    "DUMMY": "XC8",
}
NOMINAL_WEIGHTS = {
    "BIT1": 1.0,
    "BIT2": 2.0,
    "BIT3": 4.0,
    "BIT4": 8.0,
    "BIT5": 16.0,
    "BIT6": 32.0,
    "BIT7": 64.0,
    "DUMMY": 1.0,
}
MEASURE_RE = re.compile(r"(?im)^\s*([a-z][a-z0-9_]*)\s*=\s*([-+0-9.eE]+)")


def ensure_directories(*directories):
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def load_cdac_weights(branch="CLAIM_BASELINE_3SIGMA_CONVERSION"):
    grouped = {}
    with WEIGHTS_CSV.open(newline="", encoding="ascii") as handle:
        for row in csv.DictReader(handle):
            if row["branch"] != branch:
                continue
            key = (int(row["mismatch_seed"]), row["side"])
            grouped.setdefault(key, {})[row["element"]] = float(row["realized_units"])
    return grouped


def analytical_cdac_seed_metrics(grouped):
    rows = []
    seeds = sorted({seed for seed, _ in grouped})
    for seed in seeds:
        side_norm = {}
        for side in ("P", "N"):
            weights = grouped[(seed, side)]
            total = sum(weights.values())
            side_norm[side] = {
                element: weights[element] / total for element in NOMINAL_WEIGHTS
            }
        effective = {
            element: 0.5 * (side_norm["P"][element] + side_norm["N"][element])
            for element in NOMINAL_WEIGHTS
        }
        levels = []
        for code in range(128):
            value = sum(
                effective[f"BIT{bit + 1}"]
                for bit in range(7)
                if code & (1 << bit)
            )
            levels.append(value)
        levels = np.asarray(levels)
        ideal = np.arange(128, dtype=float) / 128.0
        inl_proxy_lsb = (levels - ideal) * 128.0
        dnl_proxy_lsb = np.diff(levels) * 128.0 - 1.0
        rows.append(
            {
                "mismatch_seed": seed,
                "predicted_max_abs_inl_proxy_lsb": float(np.max(np.abs(inl_proxy_lsb))),
                "predicted_rms_inl_proxy_lsb": float(np.sqrt(np.mean(inl_proxy_lsb**2))),
                "predicted_max_abs_dnl_proxy_lsb": float(np.max(np.abs(dnl_proxy_lsb))),
            }
        )
    return rows


def select_predicted_tail_seeds(grouped, excluded=(1, 2)):
    rows = analytical_cdac_seed_metrics(grouped)
    candidates = [row for row in rows if row["mismatch_seed"] not in set(excluded)]
    static_row = max(candidates, key=lambda row: row["predicted_max_abs_inl_proxy_lsb"])
    dynamic_candidates = [
        row for row in candidates if row["mismatch_seed"] != static_row["mismatch_seed"]
    ]
    dynamic_row = max(
        dynamic_candidates,
        key=lambda row: (
            row["predicted_rms_inl_proxy_lsb"],
            row["predicted_max_abs_dnl_proxy_lsb"],
        ),
    )
    return static_row, dynamic_row, rows


def _cdac_subckt(name, weights):
    instance_weights = {
        ELEMENT_TO_INSTANCE[element]: value for element, value in weights.items()
    }
    output = []
    for raw_line in CDAC.read_text(encoding="ascii").splitlines():
        line = raw_line
        if line.lower().startswith(".subckt cdac "):
            line = re.sub(r"(?i)^\.subckt\s+CDAC\b", f".subckt {name}", line)
        elif line.lower().startswith(".ends cdac"):
            line = f".ends {name}"
        else:
            match = re.match(r"^(XC[1-8])\s", line, flags=re.IGNORECASE)
            if match:
                instance = match.group(1).upper()
                line = re.sub(r"\s+m=[^\s]+", "", line, flags=re.IGNORECASE)
                line += f" m={instance_weights[instance]:.17g}"
        output.append(line)
    return "\n".join(output)


def cdac_pair_subckts(mismatch_seed, grouped):
    if mismatch_seed is None:
        p_weights = dict(NOMINAL_WEIGHTS)
        n_weights = dict(NOMINAL_WEIGHTS)
        suffix = "NOM"
    else:
        p_weights = grouped[(int(mismatch_seed), "P")]
        n_weights = grouped[(int(mismatch_seed), "N")]
        suffix = f"S{int(mismatch_seed):03d}"
    p_name = f"CDAC_P_{suffix}"
    n_name = f"CDAC_N_{suffix}"
    return p_name, n_name, _cdac_subckt(p_name, p_weights), _cdac_subckt(n_name, n_weights)


def _pwl_source(name, positive_node, values, frame_s):
    points = [(0.0, float(values[0]))]
    edge_s = 1e-12
    for index in range(1, len(values)):
        boundary = index * frame_s
        points.append((boundary - edge_s, float(values[index - 1])))
        points.append((boundary, float(values[index])))
    tokens = [f"{time_s:.12g} {value:.12g}" for time_s, value in points]
    lines = [f"{name} {positive_node} 0 PWL("]
    for start in range(0, len(tokens), 4):
        lines.append("+ " + " ".join(tokens[start : start + 4]))
    lines.append("+ )")
    return "\n".join(lines)


def _linear_sampled_source(name, positive_node, values, frame_s):
    points = [(0.0, float(values[0]))]
    for index, value in enumerate(values):
        points.append((index * frame_s + TRACK_FALL_OFFSET_S, float(value)))
    points.append((len(values) * frame_s, float(values[-1])))
    tokens = [f"{time_s:.12g} {value:.12g}" for time_s, value in points]
    lines = [f"{name} {positive_node} 0 PWL("]
    for start in range(0, len(tokens), 4):
        lines.append("+ " + " ".join(tokens[start : start + 4]))
    lines.append("+ )")
    return "\n".join(lines)


def _model_includes(pvt, mismatch_seed):
    lines = []
    if mismatch_seed is not None:
        legacy_rng_alignment = tuple(
            f"RLEGACY_RNG_BURN_{index:02d} legacy_rng_burn_{index:02d} 0 r='1+0*agauss(0,1,3)'"
            for index in range(1, 20)
        )
        lines.extend(
            (
                f".option seed={int(mismatch_seed)}",
                ".param sw_stat_global=0 sw_stat_mismatch=1 mc_skew=3 res_mc_skew=3 cap_mc_skew=3 fnoicor=0",
                "* PVT3 contract: deterministic process corner plus local MOS mismatch.",
                "* Do not replace this with the statistical section: that would collapse",
                "* TT/SS/FF MOS process binding to the statistical nominal model.",
                f".lib {PDK / 'sm141064.ngspice'} {pvt['model_section']}",
                f".lib {PDK / 'sm141064.ngspice'} {pvt['mim_section']}",
                "* Preserve the established MC seed mapping by consuming the 19 global",
                "* agauss draws present in the legacy statistical section before fets_mm.",
                *legacy_rng_alignment,
            )
        )
    else:
        lines.extend(
            (
                f".lib {PDK / 'sm141064.ngspice'} {pvt['model_section']}",
                f".lib {PDK / 'sm141064.ngspice'} {pvt['mim_section']}",
            )
        )
    return "\n".join(lines)


def _input_sources(input_spec, frame_s, total_frames):
    if input_spec["kind"] == "static_sequence":
        vids = np.asarray(input_spec["vid_values"], dtype=float)
        if len(vids) != total_frames:
            raise ValueError("static input sequence length does not match total_frames")
        vinp = VCM_V + (vids + NUMERICAL_TIEBREAK_DIFF_V) / 2.0
        vinn = VCM_V - (vids + NUMERICAL_TIEBREAK_DIFF_V) / 2.0
        return "\n".join(
            (
                _pwl_source("VVINP_ID", "vinp_src", vinp, frame_s),
                _pwl_source("VVINN_ID", "vinn_src", vinn, frame_s),
            )
        )
    if input_spec["kind"] == "sine":
        amplitude = float(input_spec.get("amplitude_diff_v", 1.5)) / 2.0
        frequency = float(input_spec["frequency_hz"])
        phase = float(input_spec.get("phase_rad", 0.0))
        omega = 2.0 * math.pi * frequency
        return "\n".join(
            (
                f"BVINP_ID vinp_src 0 V={VCM_V + NUMERICAL_TIEBREAK_DIFF_V / 2.0:.12g}+{amplitude:.12g}*sin({omega:.17g}*time+{phase:.17g})",
                f"BVINN_ID vinn_src 0 V={VCM_V - NUMERICAL_TIEBREAK_DIFF_V / 2.0:.12g}-{amplitude:.12g}*sin({omega:.17g}*time+{phase:.17g})",
            )
        )
    if input_spec["kind"] == "linear_sequence":
        vids = np.asarray(input_spec["vid_values"], dtype=float)
        if len(vids) != total_frames:
            raise ValueError("linear input sequence length does not match total_frames")
        vinp = VCM_V + (vids + NUMERICAL_TIEBREAK_DIFF_V) / 2.0
        vinn = VCM_V - (vids + NUMERICAL_TIEBREAK_DIFF_V) / 2.0
        return "\n".join(
            (
                _linear_sampled_source("VVINP_ID", "vinp_src", vinp, frame_s),
                _linear_sampled_source("VVINN_ID", "vinn_src", vinn, frame_s),
            )
        )
    raise ValueError(f"unsupported input kind: {input_spec['kind']}")


def _measure_commands(total_frames, frame_s):
    lines = []
    aperture_offset = frame_s - APERTURE_GUARD_S
    sample_check_offset = min(TRACK_FALL_OFFSET_S - 5e-9, frame_s - 30e-9)
    for index in range(total_frames):
        aperture = index * frame_s + aperture_offset
        sample_check = index * frame_s + sample_check_offset
        for bit in range(7, -1, -1):
            lines.append(
                f"meas tran f{index:03d}_d{bit} find v(dout{bit}_rx) at={aperture:.12g}"
            )
        lines.extend(
            (
                f"meas tran f{index:03d}_complete find v(complete) at={aperture:.12g}",
                f"meas tran f{index:03d}_invalid find v(invalid0) at={aperture:.12g}",
                f"meas tran f{index:03d}_timeout find v(timeout0) at={aperture:.12g}",
                f"meas tran f{index:03d}_sampled find v(sampled_diff) at={sample_check:.12g}",
                f"meas tran f{index:03d}_input find v(input_diff) at={sample_check:.12g}",
                f"meas tran f{index:03d}_tcomplete when v(complete)=1.65 rise={index + 1}",
            )
        )
    return "\n".join(lines)


def build_deck(
    input_spec,
    total_frames,
    frame_s=FRAME_DEFAULT_S,
    maxstep_s=50e-12,
    pvt_name="TT_3P3_27C",
    mismatch_seed=None,
    grouped_weights=None,
):
    pvt = PVT_CASES[pvt_name]
    if grouped_weights is None:
        grouped_weights = load_cdac_weights()
    p_name, n_name, p_subckt, n_subckt = cdac_pair_subckts(
        mismatch_seed, grouped_weights
    )
    input_sources = _input_sources(input_spec, frame_s, total_frames)
    tstop = total_frames * frame_s - 5e-9
    output_step = max(0.5e-9, maxstep_s * 5.0)
    return f"""* A44 actual analog core with fixed TT timed behavioral SAR control.
.options method=gear reltol=1e-4 abstol=1e-13 vntol=1e-7 trtol=7 chgtol=1e-15 rshunt=1e12
.include {PDK / 'design.ngspice'}
{_model_includes(pvt, mismatch_seed)}
.include {SWITCH}
.include {COMPARATOR}
.include {LOADS}
{p_subckt}
{n_subckt}

.subckt SAR_ADC_ACTIVE VDD GND VREFP VREFN VINP VINN CLKS CMPCK
+ DCTRLP7 DCTRLP6 DCTRLP5 DCTRLP4 DCTRLP3 DCTRLP2 DCTRLP1
+ DCTRLN7 DCTRLN6 DCTRLN5 DCTRLN4 DCTRLN3 DCTRLN2 DCTRLN1
+ DCMPP DCMPN VRESP VRESN
XCDACP VINP CLKS VRESP DCTRLP7 DCTRLP6 DCTRLP5 DCTRLP4 DCTRLP3 DCTRLP2 DCTRLP1 VREFP VDD GND VREFN {p_name}
XCDACN VINN CLKS VRESN DCTRLN7 DCTRLN6 DCTRLN5 DCTRLN4 DCTRLN3 DCTRLN2 DCTRLN1 VREFP VDD GND VREFN {n_name}
XCMP CMPCK DCMPP VRESP DCMPN VRESN VDD GND Comparator_StrongARM
.ends SAR_ADC_ACTIVE

.temp {pvt['temp_c']}
VVDD vdd 0 {pvt['vdd_v']:.12g}
VVREFP_ID vrefp_src 0 {VREFP_V:.12g}
RVREFP vrefp_src vrefp {{REF_R_EQ}}
RVREFP_ESR vrefp vrefp_cap {{REF_ESR_EQ}}
CVREFP_LOCAL vrefp_cap 0 {{REF_CLOCAL_EQ}}
CVREFP_LINE vrefp 0 {{REF_CLINE_EQ}}
VVREFN_ID vrefn_src 0 {VREFN_V:.12g}
RVREFN vrefn_src vrefn {{REF_R_EQ}}
RVREFN_ESR vrefn vrefn_cap {{REF_ESR_EQ}}
CVREFN_LOCAL vrefn_cap 0 {{REF_CLOCAL_EQ}}
CVREFN_LINE vrefn 0 {{REF_CLINE_EQ}}

{input_sources}
RVINP vinp_src vinp {{VIN_R_EQ}}
CVINP vinp 0 {{VIN_CP_EQ+VIN_CCM_EQ}}
RVINN vinn_src vinn {{VIN_R_EQ}}
CVINN vinn 0 {{VIN_CN_EQ+VIN_CCM_EQ}}
CVIN_DIFF vinp vinn {{VIN_CDM_EQ}}

VCLKS_ID clks_src 0 PULSE(0 {pvt['vdd_v']:.12g} {SAMPLE_EDGE_OFFSET_S:.12g} {{CLK_TR_EQ}} {{CLK_TF_EQ}} 125n {frame_s:.12g})
RCLKS clks_src clks {{CLK_R_EQ}}
CCLKS clks 0 {{CLK_C_EQ}}

XCORE vdd 0 vrefp vrefn vinp vinn clks cmpck
+ dctrlp7 dctrlp6 dctrlp5 dctrlp4 dctrlp3 dctrlp2 dctrlp1
+ dctrln7 dctrln6 dctrln5 dctrln4 dctrln3 dctrln2 dctrln1
+ dcmpp dcmpn vresp vresn SAR_ADC_ACTIVE
E_SAMPLE_DIFF sampled_diff 0 vresp vresn 1
E_INPUT_DIFF input_diff 0 vinp vinn 1

CLOGIC_P dcmpp 0 {{CLOGIC_IN_P}}
CLOGIC_N dcmpn 0 {{CLOGIC_IN_N}}
A_CLKS [clks] [clks_d] adc_logic_in
A_DCMPP [dcmpp] [dcmpp_d] adc_logic_in
A_DCMPN [dcmpn] [dcmpn_d] adc_logic_in
ABEH [clks_d dcmpp_d dcmpn_d]
+ [cmpck_d
+ dctrlp7_d dctrlp6_d dctrlp5_d dctrlp4_d dctrlp3_d dctrlp2_d dctrlp1_d
+ dctrln7_d dctrln6_d dctrln5_d dctrln4_d dctrln3_d dctrln2_d dctrln1_d
+ dout7_d dout6_d dout5_d dout4_d dout3_d dout2_d dout1_d dout0_d
+ eoc_d
+ invalid7_d invalid6_d invalid5_d invalid4_d invalid3_d invalid2_d invalid1_d invalid0_d
+ timeout7_d timeout6_d timeout5_d timeout4_d timeout3_d timeout2_d timeout1_d timeout0_d
+ complete_d] sar_logic_beh

A_CMPCK [cmpck_d] [cmpck_drv] dac_cmpck
A_DCTRLP [dctrlp7_d dctrlp6_d dctrlp5_d dctrlp4_d dctrlp3_d dctrlp2_d dctrlp1_d]
+ [dctrlp7_drv dctrlp6_drv dctrlp5_drv dctrlp4_drv dctrlp3_drv dctrlp2_drv dctrlp1_drv] dac_dctrl
A_DCTRLN [dctrln7_d dctrln6_d dctrln5_d dctrln4_d dctrln3_d dctrln2_d dctrln1_d]
+ [dctrln7_drv dctrln6_drv dctrln5_drv dctrln4_drv dctrln3_drv dctrln2_drv dctrln1_drv] dac_dctrl
A_DOUT [dout7_d dout6_d dout5_d dout4_d dout3_d dout2_d dout1_d dout0_d]
+ [dout7_drv dout6_drv dout5_drv dout4_drv dout3_drv dout2_drv dout1_drv dout0_drv] dac_dout
A_STATUS [eoc_d invalid0_d timeout0_d complete_d] [eoc invalid0 timeout0 complete] dac_status

R_CMPCK cmpck_drv cmpck {{CMPCK_R_EQ}}
R_DCTRLP7 dctrlp7_drv dctrlp7 {{DCTRL_R_EQ}}
R_DCTRLP6 dctrlp6_drv dctrlp6 {{DCTRL_R_EQ}}
R_DCTRLP5 dctrlp5_drv dctrlp5 {{DCTRL_R_EQ}}
R_DCTRLP4 dctrlp4_drv dctrlp4 {{DCTRL_R_EQ}}
R_DCTRLP3 dctrlp3_drv dctrlp3 {{DCTRL_R_EQ}}
R_DCTRLP2 dctrlp2_drv dctrlp2 {{DCTRL_R_EQ}}
R_DCTRLP1 dctrlp1_drv dctrlp1 {{DCTRL_R_EQ}}
R_DCTRLN7 dctrln7_drv dctrln7 {{DCTRL_R_EQ}}
R_DCTRLN6 dctrln6_drv dctrln6 {{DCTRL_R_EQ}}
R_DCTRLN5 dctrln5_drv dctrln5 {{DCTRL_R_EQ}}
R_DCTRLN4 dctrln4_drv dctrln4 {{DCTRL_R_EQ}}
R_DCTRLN3 dctrln3_drv dctrln3 {{DCTRL_R_EQ}}
R_DCTRLN2 dctrln2_drv dctrln2 {{DCTRL_R_EQ}}
R_DCTRLN1 dctrln1_drv dctrln1 {{DCTRL_R_EQ}}

R_DOUT7 dout7_drv dout7_rx {{DOUT_R_EQ}}
R_DOUT6 dout6_drv dout6_rx {{DOUT_R_EQ}}
R_DOUT5 dout5_drv dout5_rx {{DOUT_R_EQ}}
R_DOUT4 dout4_drv dout4_rx {{DOUT_R_EQ}}
R_DOUT3 dout3_drv dout3_rx {{DOUT_R_EQ}}
R_DOUT2 dout2_drv dout2_rx {{DOUT_R_EQ}}
R_DOUT1 dout1_drv dout1_rx {{DOUT_R_EQ}}
R_DOUT0 dout0_drv dout0_rx {{DOUT_R_EQ}}
C_DOUT7 dout7_rx 0 {{DOUT_C_EQ}}
C_DOUT6 dout6_rx 0 {{DOUT_C_EQ}}
C_DOUT5 dout5_rx 0 {{DOUT_C_EQ}}
C_DOUT4 dout4_rx 0 {{DOUT_C_EQ}}
C_DOUT3 dout3_rx 0 {{DOUT_C_EQ}}
C_DOUT2 dout2_rx 0 {{DOUT_C_EQ}}
C_DOUT1 dout1_rx 0 {{DOUT_C_EQ}}
C_DOUT0 dout0_rx 0 {{DOUT_C_EQ}}

.model adc_logic_in adc_bridge in_low={0.30 * pvt['vdd_v']:.12g} in_high={0.70 * pvt['vdd_v']:.12g} rise_delay=1p fall_delay=1p
.model dac_cmpck dac_bridge input_load=10f t_rise={{CMPCK_TR_EQ}} t_fall={{CMPCK_TF_EQ}} out_low=0 out_high={pvt['vdd_v']:.12g}
.model dac_dctrl dac_bridge input_load=10f t_rise={{DCTRL_TR_EQ}} t_fall={{DCTRL_TF_EQ}} out_low=0 out_high={pvt['vdd_v']:.12g}
.model dac_dout dac_bridge input_load=10f t_rise={{DOUT_TR_EQ}} t_fall={{DOUT_TF_EQ}} out_low=0 out_high={pvt['vdd_v']:.12g}
.model dac_status dac_bridge input_load=1f t_rise=0.05n t_fall=0.05n out_low=0 out_high={pvt['vdd_v']:.12g}
.model sar_logic_beh d_cosim simulation="{BEHAVIOR_SO}" delay=1p

.save v(cmpck) v(vresp) v(vresn) v(vinp) v(vinn) v(sampled_diff) v(input_diff)
+ v(dout7_rx) v(dout6_rx) v(dout5_rx) v(dout4_rx) v(dout3_rx) v(dout2_rx) v(dout1_rx) v(dout0_rx)
+ v(complete) v(invalid0) v(timeout0)
.control
set noaskquit
set plotwinsize=0
tran {output_step:.12g} {tstop:.12g} 0 {maxstep_s:.12g}
{_measure_commands(total_frames, frame_s)}
quit
.endc
.end
"""


def run_deck(
    deck,
    stem,
    job_dir,
    log_dir,
    timeout_s=1200,
    cache_completed_failure=False,
    raw_path=None,
):
    ensure_directories(job_dir, log_dir)
    deck_path = job_dir / f"{stem}.spice"
    log_path = log_dir / f"{stem}.log"
    if deck_path.exists() and log_path.exists():
        old_deck = deck_path.read_text(encoding="ascii")
        old_log = log_path.read_text(encoding="utf-8", errors="replace")
        old_aborted = (
            "simulation(s) aborted" in old_log or "Timestep too small" in old_log
        )
        if (
            old_deck == deck
            and "ngspice-46 done" in old_log
            and (not old_aborted or cache_completed_failure)
            and (raw_path is None or Path(raw_path).is_file())
        ):
            measures = {
                name.lower(): float(value) for name, value in MEASURE_RE.findall(old_log)
            }
            return {
                "returncode": 3 if old_aborted else 0,
                "elapsed_s": 0.0,
                "deck": deck_path,
                "log": log_path,
                "measures": measures,
                "cached": True,
                "cached_failure": old_aborted,
                "simulation_aborted": old_aborted,
                "timed_out": False,
                "peak_rss_kb": 0,
                "raw": Path(raw_path) if raw_path is not None else None,
            }
    deck_path.write_text(deck, encoding="ascii")
    started = time.monotonic()
    command = [str(NGSPICE), "-b", "-o", str(log_path)]
    if raw_path is not None:
        raw_path = Path(raw_path)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        command.extend(["-r", str(raw_path)])
    command.append(str(deck_path))
    ngspice_env = os.environ.copy()
    # SPICE_USERINIT_DIR from the container entrypoint can point to an empty
    # PDK directory. Pin the package-owned init so every run uses the same
    # accepted "hs a" compatibility modes and four-thread ngspice setting.
    ngspice_env["SPICE_USERINIT_DIR"] = str(NGSPICE_USERINIT_DIR)
    process = subprocess.Popen(
        command,
        cwd=job_dir,
        env=ngspice_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    peak_rss_kb = 0
    timed_out = False
    deadline = started + timeout_s
    while process.poll() is None:
        try:
            status = Path(f"/proc/{process.pid}/status").read_text(
                encoding="ascii", errors="replace"
            )
            for line in status.splitlines():
                if line.startswith(("VmRSS:", "VmHWM:")):
                    peak_rss_kb = max(peak_rss_kb, int(line.split()[1]))
        except (FileNotFoundError, ProcessLookupError, ValueError):
            pass
        if time.monotonic() >= deadline:
            timed_out = True
            process.kill()
            break
        time.sleep(0.1)
    process.wait()
    elapsed_s = time.monotonic() - started
    log_text = (
        log_path.read_text(encoding="utf-8", errors="replace")
        if log_path.exists()
        else ""
    )
    measures = {name.lower(): float(value) for name, value in MEASURE_RE.findall(log_text)}
    simulation_aborted = (
        "simulation(s) aborted" in log_text or "Timestep too small" in log_text
    )
    effective_returncode = (
        124 if timed_out else (process.returncode if not simulation_aborted else 3)
    )
    return {
        "returncode": effective_returncode,
        "elapsed_s": elapsed_s,
        "deck": deck_path,
        "log": log_path,
        "measures": measures,
        "cached": False,
        "simulation_aborted": simulation_aborted,
        "timed_out": timed_out,
        "peak_rss_kb": peak_rss_kb,
        "raw": raw_path,
    }


def decode_frames(run_result, total_frames, vdd_v, frame_s):
    measures = run_result["measures"]
    rows = []
    for index in range(total_frames):
        prefix = f"f{index:03d}_"
        missing = []
        bits = []
        for bit in range(7, -1, -1):
            key = f"{prefix}d{bit}"
            if key not in measures:
                missing.append(key)
                bits.append(0)
            else:
                bits.append(int(measures[key] > vdd_v / 2.0))
        code = sum(value << (7 - offset) for offset, value in enumerate(bits))
        complete = measures.get(f"{prefix}complete", float("nan"))
        invalid = measures.get(f"{prefix}invalid", float("nan"))
        timeout = measures.get(f"{prefix}timeout", float("nan"))
        sampled = measures.get(f"{prefix}sampled", float("nan"))
        input_value = measures.get(f"{prefix}input", float("nan"))
        complete_time = measures.get(f"{prefix}tcomplete", float("nan"))
        aperture_time = index * frame_s + frame_s - APERTURE_GUARD_S
        stable_margin_s = aperture_time - complete_time
        valid = all(
            (
                run_result["returncode"] == 0,
                not missing,
                math.isfinite(complete) and complete > vdd_v / 2.0,
                math.isfinite(invalid) and invalid < vdd_v / 2.0,
                math.isfinite(timeout) and timeout < vdd_v / 2.0,
                math.isfinite(complete_time),
            )
        )
        rows.append(
            {
                "frame_index": index,
                "code": code,
                "bits": "".join(str(bit) for bit in bits),
                "complete_v": complete,
                "invalid_v": invalid,
                "timeout_v": timeout,
                "sampled_diff_v": sampled,
                "input_diff_v": input_value,
                "sampled_input_error_v": sampled - input_value,
                "complete_time_s": complete_time,
                "stable_margin_s": stable_margin_s,
                "valid": valid,
                "missing_measures": ";".join(missing),
            }
        )
    return rows


def run_frames(
    stem,
    input_spec,
    total_frames,
    job_dir,
    log_dir,
    frame_s=FRAME_DEFAULT_S,
    maxstep_s=50e-12,
    pvt_name="TT_3P3_27C",
    mismatch_seed=None,
    grouped_weights=None,
    timeout_s=1200,
    cache_completed_failure=False,
):
    deck = build_deck(
        input_spec=input_spec,
        total_frames=total_frames,
        frame_s=frame_s,
        maxstep_s=maxstep_s,
        pvt_name=pvt_name,
        mismatch_seed=mismatch_seed,
        grouped_weights=grouped_weights,
    )
    result = run_deck(
        deck,
        stem,
        job_dir,
        log_dir,
        timeout_s=timeout_s,
        cache_completed_failure=cache_completed_failure,
    )
    result["frames"] = decode_frames(
        result, total_frames, PVT_CASES[pvt_name]["vdd_v"], frame_s
    )
    return result


def dynamic_metrics(codes, fundamental_bin, sample_rate_hz=2.0e6):
    values = np.asarray(codes, dtype=float)
    count = len(values)
    centered = values - np.mean(values)
    spectrum = np.fft.rfft(centered)
    powers = np.abs(spectrum) ** 2
    if count > 1:
        powers[1:-1] *= 2.0
    fundamental_power = float(powers[fundamental_bin])
    harmonic_bins = []
    for harmonic in range(2, 6):
        raw_bin = (harmonic * fundamental_bin) % count
        folded = raw_bin if raw_bin <= count // 2 else count - raw_bin
        if folded not in (0, fundamental_bin) and folded not in harmonic_bins:
            harmonic_bins.append(folded)
    harmonic_power = float(sum(powers[index] for index in harmonic_bins))
    excluded = {0, fundamental_bin, *harmonic_bins}
    noise_power = float(
        sum(power for index, power in enumerate(powers) if index not in excluded)
    )
    error_power = harmonic_power + noise_power
    spur_candidates = [
        (float(power), index)
        for index, power in enumerate(powers)
        if index not in (0, fundamental_bin)
    ]
    largest_spur_power, largest_spur_bin = max(spur_candidates)

    def ratio_db(numerator, denominator):
        if numerator <= 0.0 or denominator <= 0.0:
            return float("inf")
        return 10.0 * math.log10(numerator / denominator)

    sndr_db = ratio_db(fundamental_power, error_power)
    return {
        "samples": count,
        "fundamental_bin": fundamental_bin,
        "fundamental_frequency_hz": fundamental_bin * sample_rate_hz / count,
        "sndr_db": sndr_db,
        "snr_db": ratio_db(fundamental_power, noise_power),
        "sfdr_db": ratio_db(fundamental_power, largest_spur_power),
        "thd_db": -ratio_db(fundamental_power, harmonic_power),
        "enob_bit": (sndr_db - 1.76) / 6.02,
        "largest_spur_bin": int(largest_spur_bin),
        "largest_spur_frequency_hz": largest_spur_bin * sample_rate_hz / count,
        "mean_code": float(np.mean(values)),
        "min_code": int(np.min(values)),
        "max_code": int(np.max(values)),
        "clipping_count": int(np.count_nonzero((values <= 0) | (values >= 255))),
        "harmonic_bins": harmonic_bins,
    }


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="ascii")
        return
    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
