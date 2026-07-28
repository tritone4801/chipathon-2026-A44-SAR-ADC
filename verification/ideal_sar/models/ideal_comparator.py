"""Ideal comparator for SAR threshold decisions."""


def decide(vdiff, threshold):
    """Return 1 when the input is greater than or equal to the threshold."""

    return 1 if vdiff >= threshold else 0

