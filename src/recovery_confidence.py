import json
import math
from pathlib import Path

try:
    from .daily_metrics import duration_to_seconds
    from .db import DB_PATH, connect
except ImportError:
    from daily_metrics import duration_to_seconds
    from db import DB_PATH, connect


BASE_DIR = Path(__file__).resolve().parents[1]
VERSIONS_PATH = BASE_DIR / "config" / "versions.json"
WEIGHTS = {
    "activity_load": 0.15,
    "training_load": 0.15,
    "hrv": 0.25,
    "resting_heart_rate": 0.15,
    "sleep": 0.20,
    "readiness_support": 0.10,
}
MATURITY_METRICS = {
    "activity_load": ("steps", "active_calories"),
    "training_load": ("training_duration", "training_calories"),
    "hrv": ("nightly_hrv_rmssd", "morning_rmssd"),
    "resting_heart_rate": ("nightly_resting_hr", "morning_mean_hr"),
    "sleep": ("sleep_duration", "sleep_score"),
    "readiness_support": ("respiration_rate", "kubios_readiness"),
}
ALTERNATIVE_GROUPS = {"hrv", "resting_heart_rate", "readiness_support"}


def load_confidence_version(path=VERSIONS_PATH):
    versions = json.loads(Path(path).read_text(encoding="utf-8"))
    return versions["confidence_engine_version"]


def present(value, duration=False):
    if value is None or value == "":
        return False
    if duration:
        text = str(value).strip()
        if not text.isdigit() and not text.startswith("P"):
            return False
        seconds = duration_to_seconds(value)
        return seconds is not None and seconds >= 0
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(float(value)) and float(value) >= 0
    return bool(str(value).strip())


def completeness_groups(metric):
    activity = 50 * sum(
        present(metric.get(key)) for key in ("steps", "active_calories")
    )
    training_count = metric.get("training_count")
    if present(training_count) and float(training_count) == 0:
        training = 100
    elif not present(training_count):
        training = 0
    else:
        training = 100 / 3 * sum(
            (
                present(training_count),
                present(metric.get("training_duration"), duration=True),
                present(metric.get("training_calories")),
            )
        )
    sleep = 50 * sum(
        (
            present(metric.get("sleep_duration"), duration=True),
            present(metric.get("sleep_score")),
        )
    )
    return {
        "activity_load": activity,
        "training_load": training,
        "hrv": 100 if any(present(metric.get(k)) for k in ("nightly_hrv_rmssd", "morning_rmssd")) else 0,
        "resting_heart_rate": 100 if any(present(metric.get(k)) for k in ("nightly_resting_hr", "morning_mean_hr")) else 0,
        "sleep": sleep,
        "readiness_support": 100 if any(present(metric.get(k)) for k in ("respiration_rate", "kubios_readiness")) else 0,
    }


def metric_maturity(row):
    if not row:
        return 0
    window = row.get("window_days") or 0
    valid = row.get("valid_days") or 0
    if window <= 0 or valid < 0:
        return 0
    return min(valid / window, 1) * 100


def maturity_groups(baselines):
    result = {}
    for group, metrics in MATURITY_METRICS.items():
        values = [metric_maturity(baselines.get(name)) for name in metrics]
        result[group] = max(values) if group in ALTERNATIVE_GROUPS else sum(values) / len(values)
    return result


def weighted(groups):
    return round(sum(groups[name] * WEIGHTS[name] for name in WEIGHTS))


def confidence_level(score):
    if score >= 85:
        return "high"
    if score >= 70:
        return "medium"
    if score >= 50:
        return "low"
    return "very_low"


def calculate_confidence(metric, baselines=None, version=None):
    baselines = baselines or {}
    completeness = completeness_groups(metric or {})
    maturity = maturity_groups(baselines)
    completeness_score = weighted(completeness)
    maturity_score = weighted(maturity)
    score = max(0, min(100, round(completeness_score * 0.55 + maturity_score * 0.45)))
    group_scores = {
        name: {"completeness": round(completeness[name]), "maturity": round(maturity[name])}
        for name in WEIGHTS
    }
    return {
        "date": metric.get("date") if metric else None,
        "data_completeness_score": completeness_score,
        "baseline_maturity_score": maturity_score,
        "confidence_score": score,
        "confidence_level": confidence_level(score),
        "group_scores_json": json.dumps(group_scores, sort_keys=True),
        "available_groups_json": json.dumps([name for name, value in completeness.items() if value > 0]),
        "missing_groups_json": json.dumps([name for name, value in completeness.items() if value == 0]),
        "confidence_version": version or load_confidence_version(),
    }


def load_inputs(connection):
    metrics = [dict(row) for row in connection.execute("SELECT * FROM daily_recovery_metrics ORDER BY date")]
    rows = connection.execute("SELECT date, metric_name, window_days, valid_days, status FROM baseline_metrics").fetchall()
    baselines = {}
    for row in rows:
        baselines.setdefault(row["date"], {})[row["metric_name"]] = dict(row)
    return metrics, baselines


def upsert_confidence(connection, results):
    sql = """
    INSERT INTO recovery_confidence (
        date, data_completeness_score, baseline_maturity_score, confidence_score,
        confidence_level, group_scores_json, available_groups_json,
        missing_groups_json, confidence_version
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(date) DO UPDATE SET
        data_completeness_score=excluded.data_completeness_score,
        baseline_maturity_score=excluded.baseline_maturity_score,
        confidence_score=excluded.confidence_score,
        confidence_level=excluded.confidence_level,
        group_scores_json=excluded.group_scores_json,
        available_groups_json=excluded.available_groups_json,
        missing_groups_json=excluded.missing_groups_json,
        confidence_version=excluded.confidence_version,
        updated_at=CURRENT_TIMESTAMP
    """
    for item in results:
        connection.execute(sql, tuple(item[key] for key in (
            "date", "data_completeness_score", "baseline_maturity_score",
            "confidence_score", "confidence_level", "group_scores_json",
            "available_groups_json", "missing_groups_json", "confidence_version"
        )))
    connection.commit()
    return len(results)


def rebuild_confidence(connection=None):
    owns = connection is None
    connection = connection or connect(DB_PATH)
    try:
        metrics, baselines = load_inputs(connection)
        results = [calculate_confidence(metric, baselines.get(metric["date"], {})) for metric in metrics]
        return upsert_confidence(connection, results)
    finally:
        if owns:
            connection.close()


if __name__ == "__main__":
    print(f"Recovery confidence upserted: {rebuild_confidence()}")
