import math
from datetime import date


NUMERIC_LIMITS = {
    "mean_rr_ms": (100, 3000), "mean_hr_bpm": (20, 250), "rmssd_ms": (0.1, 1000),
    "sdnn_ms": (0.1, 1000), "poincare_sd1_ms": (0.1, 1000), "poincare_sd2_ms": (0.1, 2000),
    "stress_index": (0, 10000), "respiratory_rate_bpm": (1, 80),
    "lf_power_ms2": (0, 10000000), "hf_power_ms2": (0, 10000000),
    "lf_power_nu": (0, 100), "hf_power_nu": (0, 100), "lf_hf_ratio": (0, 1000),
    "readiness_percent": (0, 100), "pns_index": (-20, 20), "sns_index": (-20, 20),
    "physiological_age": (1, 130), "artefact_correction_percent": (0, 100),
    "measurement_duration_seconds": (1, 7200),
}


def number_or_none(value, field):
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    limits = NUMERIC_LIMITS.get(field)
    if limits and not limits[0] <= number <= limits[1]:
        return None
    return number


def validate_date(value):
    try:
        return date.fromisoformat(str(value)).isoformat()
    except (TypeError, ValueError):
        raise ValueError("kubios_invalid_date")


def clean_values(values):
    clean = {}
    for field in NUMERIC_LIMITS:
        clean[field] = number_or_none((values or {}).get(field), field)
    for field in ("measurement_quality", "mood_code", "recovery_status"):
        value = (values or {}).get(field)
        clean[field] = str(value).strip().lower() if value not in (None, "") else None
    return clean
