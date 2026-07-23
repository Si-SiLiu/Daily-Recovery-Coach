"""Recompute and persist canonical field provenance without touching raw data."""

from __future__ import annotations

import json

try:
    from src.data_resolution import (
        DATA_RESOLUTION_VERSION,
        resolve_activity_fields,
        resolve_recovery_date,
        resolve_sleep_date,
    )
    from src.db import connect
except ImportError:  # pragma: no cover - script-mode compatibility
    from data_resolution import (
        DATA_RESOLUTION_VERSION,
        resolve_activity_fields,
        resolve_recovery_date,
        resolve_sleep_date,
    )
    from db import connect


def _distinct_dates(connection, queries):
    values = set()
    for query in queries:
        try:
            values.update(row[0] for row in connection.execute(query).fetchall() if row[0])
        except Exception:
            continue
    return sorted(values)


def _row(connection, query, params=()):
    result = connection.execute(query, params).fetchone()
    return dict(result) if result else None


def _activity_for_date(connection, log_date):
    polar = _row(
        connection,
        "SELECT * FROM polar_training_sessions_raw WHERE date=? "
        "ORDER BY start_time DESC,id DESC LIMIT 1",
        (log_date,),
    )
    manual = None
    confirmed = False
    if polar:
        manual = _row(
            connection,
            """SELECT m.* FROM polar_manual_session_links l
               JOIN manual_activity_sessions m ON m.id=l.manual_activity_session_id
               WHERE l.polar_session_external_id=? AND l.confirmed_by_user=1
               ORDER BY l.id DESC LIMIT 1""",
            (polar["external_id"],),
        )
        confirmed = manual is not None
    if polar is None:
        manual = _row(
            connection,
            "SELECT * FROM manual_activity_sessions WHERE date=? "
            "ORDER BY start_time DESC,id DESC LIMIT 1",
            (log_date,),
        )
    return resolve_activity_fields(
        polar,
        manual,
        link_confirmed=polar is not None,
    ) if polar or manual else {}


def _persist(connection, log_date, domain, fields):
    updated = 0
    for field_name, field in fields.items():
        connection.execute(
            """
            INSERT INTO resolved_daily_fields (
                date,domain,field_name,resolved_value_json,value_source,
                source_record_id,is_fallback,is_manual_override,
                resolution_reason,resolution_version
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(date,domain,field_name,resolution_version) DO UPDATE SET
                resolved_value_json=excluded.resolved_value_json,
                value_source=excluded.value_source,
                source_record_id=excluded.source_record_id,
                is_fallback=excluded.is_fallback,
                is_manual_override=excluded.is_manual_override,
                resolution_reason=excluded.resolution_reason,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                log_date,
                domain,
                field_name,
                json.dumps(field.get("value"), ensure_ascii=False, sort_keys=True),
                field["value_source"],
                None if field.get("source_record_id") is None else str(field["source_record_id"]),
                int(bool(field.get("is_fallback"))),
                int(bool(field.get("is_manual_override"))),
                field["resolution_reason"],
                DATA_RESOLUTION_VERSION,
            ),
        )
        updated += 1
    return updated


def build_resolved_daily_fields(connection):
    activity_dates = _distinct_dates(connection, (
        "SELECT date FROM polar_training_sessions_raw",
        "SELECT date FROM manual_activity_sessions",
    ))
    sleep_dates = _distinct_dates(connection, (
        "SELECT date FROM polar_sleep_raw",
        "SELECT date FROM polar_nightly_recharge_raw",
        "SELECT sleep_date FROM manual_sleep_logs",
    ))
    recovery_dates = _distinct_dates(connection, (
        "SELECT date FROM kubios_morning_hrv_raw",
        "SELECT date FROM polar_nightly_recharge_raw",
        "SELECT date FROM manual_recovery_logs",
    ))
    for log_date in activity_dates:
        yield log_date, "activity", _activity_for_date(connection, log_date)
    for log_date in sleep_dates:
        yield log_date, "sleep", resolve_sleep_date(connection, log_date)
    for log_date in recovery_dates:
        yield log_date, "recovery", resolve_recovery_date(connection, log_date)


def rebuild_resolved_daily_fields(connection):
    count = 0
    for log_date, domain, fields in build_resolved_daily_fields(connection):
        count += _persist(connection, log_date, domain, fields)
    connection.commit()
    return count


def run(context, dry_run=False):
    if dry_run:
        return {"resolved_fields_updated": 0}
    with connect() as connection:
        updated = rebuild_resolved_daily_fields(connection)
    return {"resolved_fields_updated": updated}
