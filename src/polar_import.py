import json
from pathlib import Path

try:
    from .db import DB_PATH, connect
except ImportError:
    from db import DB_PATH, connect


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
SOURCE = "polar"


def load_raw_list(path):
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return []


def load_raw_items(path, container_keys=()):
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if data.get("ok") is False:
            return []
        for key in container_keys:
            value = data.get(key)
            if isinstance(value, list):
                return value
        for key in container_keys:
            parts = key.split(".")
            value = data
            for part in parts:
                value = value.get(part) if isinstance(value, dict) else None
            if isinstance(value, list):
                return value
        if data.get("date"):
            return [data]
    return []


def date_from_timestamp(value):
    if not value:
        return None
    return str(value)[:10]


def first_value(item, *keys):
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return None


def nested_value(item, *path):
    value = item
    for key in path:
        value = value.get(key) if isinstance(value, dict) else None
    return value


def text_value(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        for key in ("name", "displayName", "value", "id", "code"):
            if isinstance(value, dict) and value.get(key) is not None:
                return str(value[key])
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def identifier_value(value):
    if isinstance(value, dict):
        return text_value(
            first_value(value, "id", "value", "uuid", "exerciseId", "trainingSessionId")
        ) or text_value(value)
    return text_value(value)


def iso_duration_from_millis(value):
    if value is None:
        return None
    try:
        total_seconds = int(value) // 1000
    except (TypeError, ValueError):
        return None
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours}H")
    if minutes:
        parts.append(f"{minutes}M")
    if seconds or not parts:
        parts.append(f"{seconds}S")
    return "PT" + "".join(parts)


def iso_duration_from_seconds(value):
    if value is None:
        return None
    text = str(value).strip()
    if text.lower().endswith("s"):
        text = text[:-1]
    try:
        total_seconds = int(round(float(text)))
    except (TypeError, ValueError):
        return None
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours}H")
    if minutes:
        parts.append(f"{minutes}M")
    if seconds or not parts:
        parts.append(f"{seconds}S")
    return "PT" + "".join(parts)


def normalize_duration(value):
    if value is None:
        return None
    text = str(value).strip()
    if text.startswith("P"):
        return text
    return iso_duration_from_seconds(text)


def _number(value):
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def heart_rate_from_rri(value):
    interval_ms = _number(value)
    return round(60000 / interval_ms, 2) if interval_ms and interval_ms > 0 else None


def respiration_rate_from_interval(value):
    interval_ms = _number(value)
    return round(60000 / interval_ms, 2) if interval_ms and interval_ms > 0 else None


def respiration_rate_from_samples(value):
    """Average valid breaths/min values from Dynamic API sample groups."""
    if not isinstance(value, list):
        return None
    rates = []
    for group in value:
        if not isinstance(group, dict):
            continue
        values = group.get("breathingRateValues") or group.get("breathing_rate_values")
        if not isinstance(values, list):
            continue
        for candidate in values:
            rate = _number(candidate)
            if rate is not None and 1 <= rate <= 80:
                rates.append(rate)
    return round(sum(rates) / len(rates), 2) if rates else None


def activity_date(activity):
    return (
        first_value(activity, "date", "calendarDate")
        or date_from_timestamp(first_value(activity, "start_time", "startTime"))
        or date_from_timestamp(first_value(activity, "end_time", "endTime"))
    )


def activity_external_id(activity):
    date_value = activity_date(activity)
    return str(
        activity.get("id")
        or activity.get("external_id")
        or first_value(activity, "start_time", "startTime")
        or date_value
    )


def session_date(session):
    return (
        first_value(session, "date", "calendarDate")
        or date_from_timestamp(first_value(session, "start_time", "startTime"))
        or date_from_timestamp(first_value(session, "upload_time", "uploadTime"))
    )


def session_external_id(session):
    date_value = session_date(session)
    return str(
        session.get("id")
        or session.get("exercise_id")
        or session.get("exerciseId")
        or identifier_value(session.get("identifier"))
        or first_value(session, "start_time", "startTime")
        or date_value
    )


def generic_date(item):
    return (
        first_value(item, "date", "calendar_date", "calendarDate", "sleepDate", "sleepResultDate")
        or date_from_timestamp(first_value(item, "start_time", "startTime"))
        or date_from_timestamp(first_value(item, "end_time", "endTime"))
    )


def generic_external_id(item):
    date_value = generic_date(item)
    return str(
        item.get("id")
        or item.get("external_id")
        or item.get("externalId")
        or first_value(item, "start_time", "startTime")
        or item.get("date")
        or date_value
    )


def number_from_keys(item, keys):
    for key in keys:
        value = item.get(key)
        if value is not None:
            return value
    return None


def import_daily_activities(connection, activities):
    sql = """
    INSERT INTO polar_daily_activity_raw (
        source,
        external_id,
        date,
        raw_json,
        steps,
        calories,
        active_calories,
        duration
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(source, external_id, date) DO UPDATE SET
        raw_json = excluded.raw_json,
        steps = excluded.steps,
        calories = excluded.calories,
        active_calories = excluded.active_calories,
        duration = excluded.duration,
        updated_at = CURRENT_TIMESTAMP
    """
    count = 0
    for activity in activities:
        date_value = activity_date(activity)
        external_id = activity_external_id(activity)
        if not date_value or not external_id:
            continue
        connection.execute(
            sql,
            (
                SOURCE,
                external_id,
                date_value,
                json.dumps(activity, ensure_ascii=False, sort_keys=True),
                first_value(activity, "steps"),
                first_value(activity, "calories"),
                first_value(activity, "active_calories", "activeCalories"),
                first_value(activity, "active_duration", "activeDuration", "duration"),
            ),
        )
        count += 1
    connection.commit()
    return count


def import_training_sessions(connection, sessions):
    sql = """
    INSERT INTO polar_training_sessions_raw (
        source,
        external_id,
        date,
        raw_json,
        sport,
        start_time,
        duration,
        calories
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(source, external_id, date) DO UPDATE SET
        raw_json = excluded.raw_json,
        sport = excluded.sport,
        start_time = excluded.start_time,
        duration = excluded.duration,
        calories = excluded.calories,
        updated_at = CURRENT_TIMESTAMP
    """
    count = 0
    for session in sessions:
        date_value = session_date(session)
        external_id = session_external_id(session)
        if not date_value or not external_id:
            continue
        connection.execute(
            sql,
            (
                SOURCE,
                external_id,
                date_value,
                json.dumps(session, ensure_ascii=False, sort_keys=True),
                text_value(first_value(session, "sport", "detailed_sport_info", "detailedSportInfo")),
                first_value(session, "start_time", "startTime"),
                first_value(session, "duration") or iso_duration_from_millis(session.get("durationMillis")),
                first_value(session, "calories"),
            ),
        )
        count += 1
    connection.commit()
    return count


def import_sleep(connection, sleeps):
    sql = """
    INSERT INTO polar_sleep_raw (
        source, external_id, date, raw_json, sleep_duration, sleep_score
    )
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(source, external_id, date) DO UPDATE SET
        raw_json = excluded.raw_json,
        sleep_duration = excluded.sleep_duration,
        sleep_score = excluded.sleep_score,
        updated_at = CURRENT_TIMESTAMP
    """
    count = 0
    for sleep in sleeps:
        date_value = generic_date(sleep)
        external_id = generic_external_id(sleep)
        if not date_value or not external_id:
            continue
        evaluation = sleep.get("sleepEvaluation") if isinstance(sleep.get("sleepEvaluation"), dict) else {}
        score_data = sleep.get("sleepScore") if isinstance(sleep.get("sleepScore"), dict) else {}
        duration = first_value(sleep, "sleep_duration", "sleepDuration", "duration", "sleepTime")
        if duration is None:
            duration = nested_value(evaluation, "asleepDuration") or nested_value(evaluation, "sleepSpan")
        score = first_value(sleep, "sleep_score", "sleepScore", "sleep_rating", "sleepRating", "sleepResult")
        if isinstance(score, dict):
            score = first_value(score, "sleepScore", "score")
        if score is None:
            score = first_value(score_data, "sleepScore", "score")
        connection.execute(
            sql,
            (
                SOURCE,
                external_id,
                date_value,
                json.dumps(sleep, ensure_ascii=False, sort_keys=True),
                normalize_duration(duration),
                score,
            ),
        )
        count += 1
    connection.commit()
    return count


def import_nightly_recharges(connection, recharges):
    sql = """
    INSERT INTO polar_nightly_recharge_raw (
        source, external_id, date, raw_json, ans_status, hrv_rmssd, resting_hr, respiration_rate
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(source, external_id, date) DO UPDATE SET
        raw_json = excluded.raw_json,
        ans_status = excluded.ans_status,
        hrv_rmssd = excluded.hrv_rmssd,
        resting_hr = excluded.resting_hr,
        respiration_rate = excluded.respiration_rate,
        updated_at = CURRENT_TIMESTAMP
    """
    count = 0
    for recharge in recharges:
        date_value = generic_date(recharge)
        external_id = generic_external_id(recharge)
        if not date_value or not external_id:
            continue
        resting_hr = first_value(recharge, "heart_rate_avg", "heartRateAvg", "resting_hr", "restingHr")
        if resting_hr is None:
            resting_hr = heart_rate_from_rri(recharge.get("meanNightlyRecoveryRri"))
        respiration_rate = first_value(recharge, "breathing_rate_avg", "breathingRateAvg", "respiration_rate", "respirationRate")
        if respiration_rate is None:
            respiration_rate = respiration_rate_from_interval(
                recharge.get("meanNightlyRecoveryRespirationInterval")
            )
        if respiration_rate is None:
            respiration_rate = respiration_rate_from_samples(
                recharge.get("breathingRateSamples")
            )
        connection.execute(
            sql,
            (
                SOURCE,
                external_id,
                date_value,
                json.dumps(recharge, ensure_ascii=False, sort_keys=True),
                first_value(recharge, "ans_charge_status", "ansChargeStatus", "ansStatus", "nightly_recharge_status", "nightlyRechargeStatus"),
                first_value(recharge, "heart_rate_variability_avg", "heartRateVariabilityAvg", "hrv_rmssd", "hrvRmssd", "meanNightlyRecoveryRmssd"),
                resting_hr,
                respiration_rate,
            ),
        )
        count += 1
    connection.commit()
    return count


def import_cardio_loads(connection, cardio_loads):
    sql = """
    INSERT INTO polar_cardio_load_raw (
        source, external_id, date, raw_json, cardio_load, strain, tolerance, status
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(source, external_id, date) DO UPDATE SET
        raw_json = excluded.raw_json,
        cardio_load = excluded.cardio_load,
        strain = excluded.strain,
        tolerance = excluded.tolerance,
        status = excluded.status,
        updated_at = CURRENT_TIMESTAMP
    """
    count = 0
    for item in cardio_loads:
        date_value = generic_date(item)
        external_id = generic_external_id(item)
        if not date_value or not external_id:
            continue
        connection.execute(
            sql,
            (
                SOURCE,
                external_id,
                date_value,
                json.dumps(item, ensure_ascii=False, sort_keys=True),
                number_from_keys(item, ("cardio_load", "cardioLoad", "cardio-load", "load")),
                number_from_keys(item, ("strain", "cardio_load_strain", "cardioLoadStrain")),
                number_from_keys(item, ("tolerance", "cardio_load_tolerance", "cardioLoadTolerance")),
                first_value(item, "status", "cardio_load_status", "cardioLoadStatus"),
            ),
        )
        count += 1
    connection.commit()
    return count


def import_continuous_heart_rates(connection, samples):
    sql = """
    INSERT INTO polar_continuous_hr_raw (
        source, external_id, date, raw_json
    )
    VALUES (?, ?, ?, ?)
    ON CONFLICT(source, external_id, date) DO UPDATE SET
        raw_json = excluded.raw_json,
        updated_at = CURRENT_TIMESTAMP
    """
    count = 0
    for item in samples:
        date_value = generic_date(item)
        external_id = generic_external_id(item)
        if not date_value or not external_id:
            continue
        connection.execute(
            sql,
            (
                SOURCE,
                external_id,
                date_value,
                json.dumps(item, ensure_ascii=False, sort_keys=True),
            ),
        )
        count += 1
    connection.commit()
    return count


def import_raw_polar_data(connection=None, raw_dir=RAW_DIR):
    owns_connection = connection is None
    connection = connection or connect()

    activities = load_raw_items(
        Path(raw_dir) / "polar_daily_activity.json",
        ("activities.activityDays", "activityDays", "activities", "days"),
    )
    sessions = load_raw_items(Path(raw_dir) / "polar_training_sessions.json", ("trainingSessions", "training_sessions", "exercises"))
    sleeps = load_raw_items(Path(raw_dir) / "polar_sleep.json", ("nights", "sleep", "sleeps", "nightSleeps"))
    recharges = load_raw_items(Path(raw_dir) / "polar_nightly_recharge.json", ("recharges", "nightlyRechargeResults", "nightly_recharge_results"))
    cardio_loads = load_raw_items(Path(raw_dir) / "polar_cardio_load.json", ("cardio_loads", "cardioLoads", "cardio-loads", "loads"))
    continuous_hr = load_raw_items(
        Path(raw_dir) / "polar_continuous_heart_rate.json",
        (
            "continuousSamples.heartRateSamplesPerDay",
            "heartRateSamplesPerDay",
            "continuous_heart_rate",
            "continuousHeartRate",
            "continuous_heartrate",
            "samples",
            "days",
        ),
    )

    result = {
        "daily_activity": import_daily_activities(connection, activities),
        "training_sessions": import_training_sessions(connection, sessions),
        "sleep": import_sleep(connection, sleeps),
        "nightly_recharge": import_nightly_recharges(connection, recharges),
        "cardio_load": import_cardio_loads(connection, cardio_loads),
        "continuous_heart_rate": import_continuous_heart_rates(connection, continuous_hr),
    }

    if owns_connection:
        connection.close()

    return result


def main():
    result = import_raw_polar_data()
    print(f"Database: {DB_PATH}")
    print(f"Daily activity imported: {result['daily_activity']}")
    print(f"Training sessions imported: {result['training_sessions']}")
    print(f"Sleep imported: {result['sleep']}")
    print(f"Nightly Recharge imported: {result['nightly_recharge']}")
    print(f"Cardio load imported: {result['cardio_load']}")
    print(f"Continuous heart rate imported: {result['continuous_heart_rate']}")


if __name__ == "__main__":
    main()
