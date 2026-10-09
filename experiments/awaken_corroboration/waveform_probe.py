"""DEV policy comparisons reuse the production waveform measurement."""
from alignment_waveform import measure, phat_window


def passes(measurement, z=7.0, margin=1.4, tolerance=0.1):
    return measurement["available"] and all(
        abs(r["lag_s"]) <= tolerance and r["z"] >= z
        and r["margin"] >= margin for r in measurement["windows"])
