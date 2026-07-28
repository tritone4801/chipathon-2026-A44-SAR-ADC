#!/usr/bin/env python3
"""Traceable physical transfer reconstruction for the Phase F MC200 campaign."""

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from sar_campaign_common import FULL_SCALE_DIFF_V, LSB_DIFF_V, NOMINAL_WEIGHTS


VREF_DIFF_V = 1.7
VCM_V = 1.65
SETTLING_TAU_S = 5.0e-9
MAJOR_TRANSITIONS = (32, 64, 128, 192, 224)


def trailing_zero_count(value):
    return (value & -value).bit_length() - 1


def normalized_side_weights(grouped, seed, side):
    if seed is None:
        weights = NOMINAL_WEIGHTS
    else:
        weights = grouped[(int(seed), side)]
    total = sum(weights.values())
    return {name: weights[name] / total for name in NOMINAL_WEIGHTS}


def _timing_by_bit(timing):
    return {
        "cmpck_high_ns": {
            bit: timing["cmpck_high"][7 - bit] for bit in range(8)
        },
        "aperture_ns": {
            bit: timing["decision_aperture_from_cmpck_rise"][7 - bit]
            for bit in range(8)
        },
        "dctrl_ns": {
            bit: timing["dctrl_event_from_cmpck_rise_bits_7_to_1"][7 - bit]
            for bit in range(1, 8)
        },
        "low_guard_ns": {
            bit: timing["cmpck_low_guard_bits_7_to_1"][7 - bit]
            for bit in range(1, 8)
        },
    }


def switching_state(grouped, seed, target, timing):
    """Return the comparator threshold implied by the frozen SAR switch state.

    A code transition is decided at the least-significant set bit of its target
    code. Higher bits have already been applied to DCTRL; lower bits retain the
    sampling state. DCTRL=1 selects VREFN and DCTRL=0 selects VREFP.
    """
    if target < 1 or target > 255:
        raise ValueError("target transition must be in [1, 255]")
    wp = normalized_side_weights(grouped, seed, "P")
    wn = normalized_side_weights(grouped, seed, "N")
    decision_bit = trailing_zero_count(target)
    d7 = (target >> 7) & 1

    if decision_bit == 7:
        shift_p_v = 0.0
        shift_n_v = 0.0
        settle_feature_v = 0.0
        settle_interval_s = None
    else:
        shift_p_v = VREF_DIFF_V * wp["BIT7"] * (1 - d7)
        shift_n_v = VREF_DIFF_V * wn["BIT7"] * d7
        for bit in range(decision_bit + 1, 7):
            decision = (target >> bit) & 1
            shift_p_v -= VREF_DIFF_V * wp[f"BIT{bit}"] * decision
            shift_n_v += VREF_DIFF_V * wn[f"BIT{bit}"] * (decision - 1)

        previous_bit = decision_bit + 1
        previous_decision = (target >> previous_bit) & 1
        initial_control = 1 if previous_bit == 7 else 0
        delta_p_v = (
            -VREF_DIFF_V
            * wp[f"BIT{previous_bit}"]
            * (previous_decision - initial_control)
        )
        delta_n_v = (
            -VREF_DIFF_V
            * wn[f"BIT{previous_bit}"]
            * ((1 - previous_decision) - initial_control)
        )
        indexed = _timing_by_bit(timing)
        settle_interval_s = 1e-9 * (
            indexed["cmpck_high_ns"][previous_bit]
            - indexed["dctrl_ns"][previous_bit]
            + indexed["low_guard_ns"][previous_bit]
            + indexed["aperture_ns"][decision_bit]
        )
        settle_feature_v = (delta_p_v - delta_n_v) * math.exp(
            -settle_interval_s / SETTLING_TAU_S
        )

    return {
        "target_transition": target,
        "decision_bit": decision_bit,
        "cdac_threshold_v": shift_n_v - shift_p_v,
        "comparator_vicm_v": VCM_V + 0.5 * (shift_p_v + shift_n_v),
        "common_mode_shift_v": 0.5 * (shift_p_v + shift_n_v),
        "settling_feature_v": settle_feature_v,
        "settling_interval_s": settle_interval_s,
    }


def switching_states(grouped, seed, timing):
    return {
        target: switching_state(grouped, seed, target, timing)
        for target in range(1, 256)
    }


@dataclass(frozen=True)
class SamplerMap:
    offset_v: float
    gain_negative: float
    gain_positive: float
    rms_residual_v: float

    def forward(self, command_v):
        command = np.asarray(command_v, dtype=float)
        result = self.offset_v + np.where(
            command >= 0.0,
            self.gain_positive * command,
            self.gain_negative * command,
        )
        return float(result) if result.ndim == 0 else result

    def inverse(self, sampled_v):
        sampled = np.asarray(sampled_v, dtype=float)
        delta = sampled - self.offset_v
        result = np.where(
            delta >= 0.0,
            delta / self.gain_positive,
            delta / self.gain_negative,
        )
        return float(result) if result.ndim == 0 else result

    def as_dict(self):
        return {
            "sampler_offset_v": self.offset_v,
            "sampler_gain_negative": self.gain_negative,
            "sampler_gain_positive": self.gain_positive,
            "sampler_asymmetry_ppm": 1e6
            * (self.gain_positive - self.gain_negative)
            / (0.5 * (self.gain_positive + self.gain_negative)),
            "sampler_fit_rms_v": self.rms_residual_v,
        }


def fit_sampler_map(input_values_v, sampled_values_v):
    x = np.asarray(input_values_v, dtype=float)
    y = np.asarray(sampled_values_v, dtype=float)
    design = np.column_stack((np.ones_like(x), np.minimum(x, 0.0), np.maximum(x, 0.0)))
    coefficients, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    predicted = design @ coefficients
    model = SamplerMap(
        offset_v=float(coefficients[0]),
        gain_negative=float(coefficients[1]),
        gain_positive=float(coefficients[2]),
        rms_residual_v=float(np.sqrt(np.mean((predicted - y) ** 2))),
    )
    if model.gain_negative <= 0.5 or model.gain_positive <= 0.5:
        raise ValueError("non-physical sampler gain fit")
    return model


def nominal_internal_kernel(nominal_transitions, nominal_sampler, nominal_states):
    return {
        target: nominal_sampler.forward(nominal_transitions[target])
        - nominal_states[target]["cdac_threshold_v"]
        for target in range(1, 256)
    }


def fit_seed_correction(
    exact_major_transitions,
    sampler,
    states,
    nominal_kernel,
):
    design = []
    response = []
    for target in MAJOR_TRANSITIONS:
        state = states[target]
        exact_internal = sampler.forward(exact_major_transitions[target])
        baseline_internal = state["cdac_threshold_v"] + nominal_kernel[target]
        design.append(
            (
                1.0,
                state["common_mode_shift_v"] / 0.85,
                state["settling_feature_v"] / LSB_DIFF_V,
            )
        )
        response.append(exact_internal - baseline_internal)
    coefficients, _, _, _ = np.linalg.lstsq(
        np.asarray(design), np.asarray(response), rcond=None
    )
    residual = np.asarray(design) @ coefficients - np.asarray(response)
    return {
        "offset_v": float(coefficients[0]),
        "vicm_slope_scaled_v": float(coefficients[1]),
        "settling_scale_v": float(coefficients[2]),
        "major_fit_max_error_lsb": float(np.max(np.abs(residual)) / LSB_DIFF_V),
        "major_fit_rms_error_lsb": float(
            np.sqrt(np.mean(residual**2)) / LSB_DIFF_V
        ),
    }


def correction_value(state, correction):
    return (
        correction["offset_v"]
        + correction["vicm_slope_scaled_v"]
        * state["common_mode_shift_v"]
        / 0.85
        + correction["settling_scale_v"]
        * state["settling_feature_v"]
        / LSB_DIFF_V
    )


def reconstruct_seed(seed, sampler, states, nominal_kernel, correction):
    transition_rows = []
    transitions = []
    for target in range(1, 256):
        state = states[target]
        comparator_correction_v = correction_value(state, correction)
        internal_threshold_v = (
            state["cdac_threshold_v"]
            + nominal_kernel[target]
            + comparator_correction_v
        )
        command_threshold_v = sampler.inverse(internal_threshold_v)
        transitions.append(command_threshold_v)
        transition_rows.append(
            {
                "mismatch_seed": seed,
                "target_transition": target,
                "decision_bit": state["decision_bit"],
                "transition_v": command_threshold_v,
                "cdac_threshold_v": state["cdac_threshold_v"],
                "nominal_internal_kernel_v": nominal_kernel[target],
                "comparator_correction_v": comparator_correction_v,
                "comparator_vicm_v": state["comparator_vicm_v"],
                "settling_feature_v": state["settling_feature_v"],
            }
        )

    values = np.asarray(transitions)
    targets = np.arange(1, 256, dtype=float)
    endpoint_lsb_v = (values[-1] - values[0]) / 254.0
    widths_v = np.diff(values)
    dnl = widths_v / endpoint_lsb_v - 1.0
    endpoint_ideal = values[0] + (targets - 1.0) * endpoint_lsb_v
    inl_endpoint = (values - endpoint_ideal) / endpoint_lsb_v
    best_fit_lsb_v, best_fit_intercept_v = np.polyfit(targets, values, 1)
    inl_best_fit = (
        values - (best_fit_intercept_v + best_fit_lsb_v * targets)
    ) / best_fit_lsb_v
    for index, row in enumerate(transition_rows):
        row["endpoint_lsb_v"] = endpoint_lsb_v
        row["dnl_to_next_lsb"] = float(dnl[index]) if index < 254 else None
        row["inl_endpoint_lsb"] = float(inl_endpoint[index])
        row["inl_best_fit_lsb"] = float(inl_best_fit[index])

    worst_width_index = int(np.argmin(widths_v))
    worst_dnl_index = int(np.argmax(np.abs(dnl)))
    worst_inl_index = int(np.argmax(np.abs(inl_endpoint)))
    ideal_first_v = -FULL_SCALE_DIFF_V / 2.0 + LSB_DIFF_V
    summary = {
        "mismatch_seed": seed,
        **sampler.as_dict(),
        **{f"correction_{key}": value for key, value in correction.items()},
        "offset_lsb": float((values[0] - ideal_first_v) / LSB_DIFF_V),
        "gain_error_ppm": float(1e6 * (endpoint_lsb_v / LSB_DIFF_V - 1.0)),
        "endpoint_lsb_v": float(endpoint_lsb_v),
        "minimum_code_width_lsb": float(np.min(widths_v) / endpoint_lsb_v),
        "missing_code_count": int(np.count_nonzero(widths_v <= 0.0)),
        "max_abs_dnl_lsb": float(np.max(np.abs(dnl))),
        "max_abs_inl_endpoint_lsb": float(np.max(np.abs(inl_endpoint))),
        "max_abs_inl_best_fit_lsb": float(np.max(np.abs(inl_best_fit))),
        "worst_width_lower_code": worst_width_index + 1,
        "worst_dnl_lower_transition": worst_dnl_index + 1,
        "worst_inl_transition": worst_inl_index + 1,
    }
    summary["static_risk_score"] = max(
        summary["max_abs_dnl_lsb"],
        summary["max_abs_inl_endpoint_lsb"] / 1.5,
        float(summary["missing_code_count"] > 0),
    )
    summary["reconstructed_spec_status"] = (
        "PASS"
        if summary["max_abs_dnl_lsb"] < 1.0
        and summary["max_abs_inl_endpoint_lsb"] < 1.5
        and summary["missing_code_count"] == 0
        else "FAIL"
    )
    return transition_rows, summary


def write_model_contract(path):
    payload = {
        "model": "TRACEABLE_SWITCH_STATE_TRANSFER_RECONSTRUCTION_V1",
        "interpolation": "NONE",
        "cdac": "frozen per-side normalized physical capacitor weights",
        "switching": "boundary least-significant-set-bit with frozen DCTRL=1-to-VREFN algorithm",
        "sampler": "piecewise-linear positive/negative gain with common offset",
        "comparator": "per-die VOS plus linear VICM shift",
        "timing": "fixed TT decision apertures from timing_tt_3p3_27c.json",
        "settling": {
            "kind": "previous-switch exponential residue feature",
            "tau_s": SETTLING_TAU_S,
        },
        "nominal_kernel": "exact nominal electrical transition residual in sampled domain",
        "major_calibration_transitions": list(MAJOR_TRANSITIONS),
    }
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )

