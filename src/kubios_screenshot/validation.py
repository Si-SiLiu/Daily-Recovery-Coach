from datetime import datetime

from .config import load_config


NUMERIC_FIELDS = {
    "rmssd", "mean_hr", "sdnn", "pns_index", "sns_index",
    "stress_index", "artefact_correction", "measurement_duration",
    "mean_rr_ms", "poincare_sd1_ms", "poincare_sd2_ms",
    "respiratory_rate_bpm", "lf_power_ms2", "hf_power_ms2",
    "lf_power_nu", "hf_power_nu", "lf_hf_ratio", "physiological_age",
}


def parse_date(value, config=None):
    config = config or load_config()
    text = str(value).strip().replace("Sept ", "Sep ")
    for fmt in config["date_formats"]:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_time(value, config=None):
    config = config or load_config()
    text = str(value).strip().upper()
    for fmt in config["time_formats"]:
        try:
            return datetime.strptime(text, fmt).time().isoformat()
        except ValueError:
            continue
    return None


def validate_value(field, value, config=None):
    config = config or load_config()
    if field == "date":
        return parse_date(value, config) is not None, "invalid_date"
    if field == "measurement_time":
        return parse_time(value, config) is not None, "invalid_time"
    if field == "readiness" and isinstance(value, str) and not value.replace(".", "", 1).isdigit():
        return bool(value.strip()), "invalid_readiness"
    if field not in NUMERIC_FIELDS and field != "readiness":
        return bool(str(value).strip()), "empty_value"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False, "not_numeric"
    limits = config["valid_ranges"].get(field)
    if limits and not (float(limits[0]) <= number <= float(limits[1])):
        return False, "outside_recognition_range"
    return True, None


def validate_confirmed_fields(fields, config=None, required_fields=None):
    config = config or load_config()
    errors = {}
    normalized = {}
    required_fields = set(config["minimum_required_fields"] if required_fields is None else required_fields)
    for name in config["supported_fields"]:
        value = fields.get(name)
        if value in (None, ""):
            if name in required_fields:
                errors[name] = "required"
            continue
        if name == "date":
            value = parse_date(value, config) or value
        elif name == "measurement_time":
            value = parse_time(value, config) or value
        valid, code = validate_value(name, value, config)
        if not valid:
            errors[name] = code
        else:
            normalized[name] = float(value) if name in NUMERIC_FIELDS else str(value).strip()
    return normalized, errors
