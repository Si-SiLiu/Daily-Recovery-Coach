"""Read-only, recomputable field resolution for activity, sleep, and recovery."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any, Mapping
import argparse
import json
from pathlib import Path

from .models import ResolvedField, SourceCandidate
from .policies import get_field_policy
from .provenance import (
    candidate,
    duration_minutes,
    first,
    nested,
    number,
    parse_json,
    query_one,
    table_columns,
)


_UNSET = object()


def _timestamp(value: str | None = None) -> str:
    return value or datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _as_candidate(value: Any, record_id: int | str | None = None, confirmed: bool = False) -> SourceCandidate:
    if isinstance(value, SourceCandidate):
        return value
    if isinstance(value, Mapping) and "value" in value:
        return SourceCandidate(
            value.get("value"),
            value.get("source_record_id", value.get("record_id", record_id)),
            bool(value.get("confirmed", confirmed)),
        )
    if isinstance(value, tuple) and len(value) == 2:
        return SourceCandidate(value[0], value[1], confirmed)
    return SourceCandidate(value, record_id, confirmed)


def _reason(selected: str | None, policy: tuple[str, ...]) -> str:
    if selected is None:
        return "no_permitted_source_value_available"
    if selected == "manual_confirmed":
        return "confirmed_manual_correction"
    if selected == "manual_unconfirmed":
        return "polar_unavailable_manual_fallback"
    if selected == "manual":
        if policy[0] == "manual":
            return "manual_only_field_available"
        return "polar_unavailable_manual_fallback"
    if selected == "polar":
        return "polar_value_available"
    if selected == "kubios":
        return "kubios_independent_measurement_available"
    if selected == "estimated":
        return "approved_estimated_fallback"
    return f"{selected}_value_available"


def resolve_field(
    domain: str,
    field_name: str,
    candidates: Mapping[str, Any] | None = None,
    *,
    polar: Any = _UNSET,
    manual: Any = _UNSET,
    kubios: Any = _UNSET,
    estimated: Any = _UNSET,
    polar_value: Any = _UNSET,
    manual_value: Any = _UNSET,
    kubios_value: Any = _UNSET,
    estimated_value: Any = _UNSET,
    polar_record_id: int | str | None = None,
    manual_record_id: int | str | None = None,
    kubios_record_id: int | str | None = None,
    estimated_record_id: int | str | None = None,
    manual_confirmed: bool = False,
    resolved_at: str | None = None,
    policy_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve one canonical field without writing to any source table.

    Candidates may be raw values, ``SourceCandidate`` objects, ``(value, id)``
    pairs, or dictionaries containing ``value`` and ``record_id``.
    """
    supplied: dict[str, Any] = dict(candidates or {})
    for source, direct, alias, record_id in (
        ("polar", polar, polar_value, polar_record_id),
        ("manual", manual, manual_value, manual_record_id),
        ("kubios", kubios, kubios_value, kubios_record_id),
        ("estimated", estimated, estimated_value, estimated_record_id),
    ):
        selected_value = direct if direct is not _UNSET else alias
        if selected_value is not _UNSET:
            supplied[source] = _as_candidate(
                selected_value,
                record_id,
                manual_confirmed if source == "manual" else False,
            )

    normalized = {
        source: _as_candidate(value)
        for source, value in supplied.items()
    }
    manual_candidate = normalized.get("manual")
    if manual_candidate is not None:
        confirmed = manual_confirmed or manual_candidate.confirmed
        normalized["manual_confirmed" if confirmed else "manual_unconfirmed"] = manual_candidate

    policy = get_field_policy(domain, field_name, policy_config)
    selected_key: str | None = None
    selected_candidate: SourceCandidate | None = None
    selected_index = -1
    for index, source in enumerate(policy):
        option = normalized.get(source)
        if option is not None and option.available:
            selected_key = source
            selected_candidate = option
            selected_index = index
            break

    if selected_candidate is None:
        result = ResolvedField(
            field_name=field_name,
            value=None,
            value_source="missing",
            source_record_id=None,
            is_fallback=False,
            is_manual_override=False,
            resolution_reason=_reason(None, policy),
            resolved_at=_timestamp(resolved_at),
        )
        return result.to_dict()

    public_source = "manual" if selected_key.startswith("manual_") else selected_key
    result = ResolvedField(
        field_name=field_name,
        value=selected_candidate.value,
        value_source=public_source,
        source_record_id=selected_candidate.record_id,
        is_fallback=(
            public_source == "manual"
            and selected_key != "manual_confirmed"
            and "polar" in policy[:selected_index]
        ),
        is_manual_override=selected_key == "manual_confirmed",
        resolution_reason=_reason(selected_key, policy),
        resolved_at=_timestamp(resolved_at),
    )
    return result.to_dict()


def resolve_canonical_field(field_name: str, *, domain: str, **kwargs: Any) -> dict[str, Any]:
    return resolve_field(domain, field_name, **kwargs)


def resolve_fields(
    domain: str,
    field_candidates: Mapping[str, Mapping[str, Any]],
    *,
    resolved_at: str | None = None,
    policy_config: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    timestamp = _timestamp(resolved_at)
    return {
        field_name: resolve_field(
            domain,
            field_name,
            candidates,
            resolved_at=timestamp,
            policy_config=policy_config,
        )
        for field_name, candidates in field_candidates.items()
    }


def _polar_activity(record: dict[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {}
    raw = parse_json(record.get("raw_json"))
    sport = first(raw, "sport")
    if isinstance(sport, dict):
        sport = first(sport, "id", "name", "displayName", "code")
    return {
        "activity_type": sport or record.get("sport"),
        "activity_name": first(raw, "name", "trainingName", "exerciseName"),
        "start_time": record.get("start_time") or first(raw, "startTime", "start_time"),
        "end_time": first(raw, "endTime", "stopTime", "end_time"),
        "duration_minutes": duration_minutes(record.get("duration") or first(raw, "duration")),
        "average_hr_bpm": number(first(raw, "hrAvg", "heartRateAvg", "averageHeartRate")),
        "max_hr_bpm": number(first(raw, "hrMax", "heartRateMax", "maximumHeartRate")),
        "calories_kcal": number(record.get("calories") if record.get("calories") is not None else raw.get("calories")),
        "fat_burn_percentage": number(first(raw, "fatPercentage", "fat_percentage")),
        "distance_m": number(first(raw, "distance", "distanceMeters", "distance_m")),
    }


def resolve_activity_fields(
    polar_record: dict[str, Any] | None,
    manual_record: dict[str, Any] | None,
    *,
    link_confirmed: bool,
    resolved_at: str | None = None,
) -> dict[str, dict[str, Any]]:
    polar_values = _polar_activity(polar_record) if link_confirmed else {}
    manual_values = manual_record or {}
    fields = (
        "activity_type", "activity_name", "start_time", "end_time",
        "duration_minutes", "average_hr_bpm", "max_hr_bpm", "calories_kcal",
        "fat_burn_percentage", "distance_m", "session_rpe", "notes",
    )
    timestamp = _timestamp(resolved_at)
    result = {}
    for field in fields:
        manual_candidate = candidate(
            manual_values.get(field), manual_record,
            confirmed=bool(link_confirmed and manual_values.get("confirmed_by_user")),
        )
        result[field] = resolve_field(
            "activity", field,
            {
                "polar": candidate(polar_values.get(field), polar_record),
                "manual": manual_candidate,
            },
            resolved_at=timestamp,
        )
    return result


def _confirmed_polar_external_id(
    connection: sqlite3.Connection,
    manual_record: dict[str, Any],
) -> tuple[str | None, bool]:
    columns = table_columns(connection, "polar_manual_session_links")
    if "manual_activity_session_id" not in columns:
        return None, False
    link = query_one(
        connection,
        """SELECT * FROM polar_manual_session_links
           WHERE manual_activity_session_id = ? AND confirmed_by_user = 1
           ORDER BY id DESC LIMIT 1""",
        (manual_record["id"],),
    )
    return (str(link["polar_session_external_id"]), True) if link else (None, False)


def resolve_activity_session(
    connection: sqlite3.Connection,
    manual_activity_session_id: int,
    *,
    resolved_at: str | None = None,
) -> dict[str, dict[str, Any]]:
    manual = query_one(
        connection, "SELECT * FROM manual_activity_sessions WHERE id = ?",
        (manual_activity_session_id,),
    )
    if manual is None:
        raise ValueError("MANUAL_ACTIVITY_SESSION_NOT_FOUND")
    polar_external_id, confirmed = _confirmed_polar_external_id(connection, manual)
    polar = None
    if confirmed and polar_external_id:
        polar = query_one(
            connection,
            """SELECT * FROM polar_training_sessions_raw
               WHERE external_id = ? ORDER BY id DESC LIMIT 1""",
            (polar_external_id,),
        )
    return resolve_activity_fields(
        polar, manual, link_confirmed=confirmed and polar is not None,
        resolved_at=resolved_at,
    )


def _polar_sleep(record: dict[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {}
    raw = parse_json(record.get("raw_json"))
    result = raw.get("sleepResult") if isinstance(raw.get("sleepResult"), dict) else {}
    hypnogram = result.get("hypnogram") if isinstance(result.get("hypnogram"), dict) else {}
    evaluation = raw.get("sleepEvaluation") if isinstance(raw.get("sleepEvaluation"), dict) else {}
    phases = evaluation.get("phaseDurations") if isinstance(evaluation.get("phaseDurations"), dict) else {}
    start = first(hypnogram, "sleepStart") or first(raw, "sleepStartTime", "sleep_start_time", "startTime")
    end = first(hypnogram, "sleepEnd") or first(raw, "wakeUpTime", "wake_time", "sleep_end_time", "endTime")
    asleep = duration_minutes(
        first(evaluation, "asleepDuration")
        or first(raw, "actualSleepDuration", "actual_sleep_duration")
        or record.get("sleep_duration")
    )
    total = duration_minutes(
        first(evaluation, "sleepSpan")
        or first(raw, "totalSleep", "sleepDuration", "sleep_duration")
        or record.get("sleep_duration")
    )
    return {
        "sleep_start_time": start,
        "wake_time": end,
        "sleep_end_time": end,
        "sleep_duration_minutes": asleep,
        "actual_sleep_duration_minutes": asleep,
        "total_sleep_duration_minutes": total,
        "sleep_score": record.get("sleep_score") if record.get("sleep_score") is not None else first(raw, "sleepScore", "sleep_score"),
        "deep_sleep_duration_minutes": duration_minutes(first(phases, "deep") or first(raw, "deepSleepDuration", "deep_sleep_duration")),
        "rem_sleep_duration_minutes": duration_minutes(first(phases, "rem") or first(raw, "remSleepDuration", "rem_sleep_duration")),
        "average_sleep_hr_bpm": number(first(raw, "averageHeartRate", "sleepAvgHr", "heartRateAvg")),
        "minimum_sleep_hr_bpm": number(first(raw, "lowestHeartRate", "minimumHeartRate", "sleepMinHr")),
        "interruption_duration_minutes": duration_minutes(first(evaluation, "interruptionDuration") or first(raw, "interruptionDuration")),
    }


def resolve_sleep_fields(
    polar_sleep_record: dict[str, Any] | None,
    manual_record: dict[str, Any] | None,
    polar_nightly_record: dict[str, Any] | None = None,
    *,
    resolved_at: str | None = None,
) -> dict[str, dict[str, Any]]:
    polar = _polar_sleep(polar_sleep_record)
    nightly = polar_nightly_record or {}
    polar.update({
        "nightly_hrv_rmssd": nightly.get("hrv_rmssd"),
        "nightly_resting_hr": nightly.get("resting_hr"),
        "respiration_rate": nightly.get("respiration_rate"),
    })
    manual = manual_record or {}
    manual_aliases = {
        "actual_sleep_duration_minutes": manual.get("actual_sleep_duration_minutes") if manual.get("actual_sleep_duration_minutes") is not None else manual.get("sleep_duration_minutes"),
        "total_sleep_duration_minutes": manual.get("total_sleep_duration_minutes") if manual.get("total_sleep_duration_minutes") is not None else manual.get("sleep_duration_minutes"),
        "sleep_end_time": manual.get("wake_time"),
    }
    fields = (
        "bed_time", "sleep_start_time", "wake_time", "sleep_end_time", "get_up_time",
        "sleep_duration_minutes", "actual_sleep_duration_minutes",
        "total_sleep_duration_minutes", "nap_duration_minutes",
        "subjective_sleep_quality", "awakenings", "notes", "sleep_score",
        "deep_sleep_duration_minutes", "rem_sleep_duration_minutes",
        "average_sleep_hr_bpm", "minimum_sleep_hr_bpm", "nightly_hrv_rmssd",
        "nightly_resting_hr", "respiration_rate", "interruption_duration_minutes",
    )
    timestamp = _timestamp(resolved_at)
    result = {}
    for field in fields:
        polar_record = polar_nightly_record if field in {
            "nightly_hrv_rmssd", "nightly_resting_hr", "respiration_rate"
        } else polar_sleep_record
        result[field] = resolve_field(
            "sleep", field,
            {
                "polar": candidate(polar.get(field), polar_record),
                "manual": candidate(manual_aliases.get(field, manual.get(field)), manual_record),
            },
            resolved_at=timestamp,
        )
    return result


def resolve_sleep_date(
    connection: sqlite3.Connection,
    sleep_date: str,
    *,
    resolved_at: str | None = None,
) -> dict[str, dict[str, Any]]:
    polar_sleep = query_one(
        connection, "SELECT * FROM polar_sleep_raw WHERE date = ? ORDER BY id DESC LIMIT 1",
        (sleep_date,),
    )
    polar_nightly = query_one(
        connection, "SELECT * FROM polar_nightly_recharge_raw WHERE date = ? ORDER BY id DESC LIMIT 1",
        (sleep_date,),
    )
    manual = query_one(
        connection, "SELECT * FROM manual_sleep_logs WHERE sleep_date = ? ORDER BY id DESC LIMIT 1",
        (sleep_date,),
    )
    return resolve_sleep_fields(polar_sleep, manual, polar_nightly, resolved_at=resolved_at)


def resolve_recovery_fields(
    kubios_record: dict[str, Any] | None,
    polar_nightly_record: dict[str, Any] | None,
    manual_record: dict[str, Any] | None,
    *,
    resolved_at: str | None = None,
) -> dict[str, dict[str, Any]]:
    kubios = kubios_record or {}
    polar = polar_nightly_record or {}
    manual = manual_record or {}
    candidates_by_field = {
        "measurement_time": {
            "manual": candidate(manual.get("measurement_time"), manual_record),
            "kubios": candidate(kubios.get("measurement_time"), kubios_record),
        },
        "morning_rmssd": {
            "manual": candidate(manual.get("morning_rmssd_ms"), manual_record),
            "kubios": candidate(kubios.get("rmssd"), kubios_record),
        },
        "morning_mean_hr": {
            "manual": candidate(manual.get("morning_resting_hr_bpm"), manual_record),
            "kubios": candidate(kubios.get("mean_hr"), kubios_record),
        },
        "kubios_readiness": {"kubios": candidate(kubios.get("readiness"), kubios_record)},
        "nightly_hrv_rmssd": {"polar": candidate(polar.get("hrv_rmssd"), polar_nightly_record)},
        "nightly_resting_hr": {"polar": candidate(polar.get("resting_hr"), polar_nightly_record)},
        "respiration_rate": {"polar": candidate(polar.get("respiration_rate"), polar_nightly_record)},
    }
    for field in (
        "subjective_recovery", "fatigue", "muscle_soreness", "mental_energy",
        "training_motivation", "stress_level", "pain_present", "pain_location", "notes",
    ):
        candidates_by_field[field] = {"manual": candidate(manual.get(field), manual_record)}
    return resolve_fields(
        "recovery", candidates_by_field, resolved_at=resolved_at,
    )


def resolve_recovery_date(
    connection: sqlite3.Connection,
    log_date: str,
    *,
    resolved_at: str | None = None,
) -> dict[str, dict[str, Any]]:
    kubios = query_one(
        connection, "SELECT * FROM kubios_morning_hrv_raw WHERE date = ? ORDER BY id DESC LIMIT 1",
        (log_date,),
    )
    polar = query_one(
        connection, "SELECT * FROM polar_nightly_recharge_raw WHERE date = ? ORDER BY id DESC LIMIT 1",
        (log_date,),
    )
    manual = query_one(
        connection, "SELECT * FROM manual_recovery_logs WHERE date = ? ORDER BY id DESC LIMIT 1",
        (log_date,),
    )
    return resolve_recovery_fields(kubios, polar, manual, resolved_at=resolved_at)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Recompute canonical fields without modifying raw source rows."
    )
    parser.add_argument("--all", action="store_true", help="Resolve all available dates.")
    parser.add_argument("--dry-run", action="store_true", help="Validate without persisting resolved rows.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not args.all:
        raise SystemExit("--all is required")
    from src.db import get_current_db_path, connect
    from src.pipeline.resolution import (
        build_resolved_daily_fields,
        rebuild_resolved_daily_fields,
    )

    if args.dry_run:
        import sqlite3

        uri = f"file:{get_current_db_path().resolve()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        try:
            fields = sum(
                len(resolved)
                for _, _, resolved in build_resolved_daily_fields(connection)
            )
        finally:
            connection.close()
    else:
        with connect() as connection:
            fields = rebuild_resolved_daily_fields(connection)
    summary = {
        "success": True,
        "dry_run": args.dry_run,
        "resolved_fields": fields,
        "resolution_version": "1.0.0",
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return summary


if __name__ == "__main__":
    main()
