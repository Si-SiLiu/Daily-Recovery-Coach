import json
from datetime import datetime

from src import kubios_import

from .audit import mark_downstream_updated, mark_reviewed
from .models import ImportResult
from .validation import validate_confirmed_fields


CONFLICT_RESOLUTIONS = {"keep_existing", "use_screenshot", "keep_both", "cancel"}


def detect_conflicts(connection, date_value, source_file_sha256=None):
    rows = connection.execute(
        """
        SELECT id, source_type, import_method, rmssd, mean_hr, readiness,
               measurement_time, source_file_sha256, is_daily_preferred
        FROM kubios_morning_hrv_raw
        WHERE date = ? AND (source_file_sha256 IS NULL OR source_file_sha256 != ?)
        ORDER BY id
        """,
        (date_value, source_file_sha256 or ""),
    ).fetchall()
    return [dict(row) for row in rows]


def conflict_summary(conflicts, confirmed):
    return {
        "existing_sources": sorted({row.get("source_type") or "csv" for row in conflicts}),
        "differences": {
            field: sorted({row.get(field) for row in conflicts} | {confirmed.get(field)}, key=lambda value: str(value))
            for field in ("rmssd", "mean_hr", "readiness")
            if any(row.get(field) != confirmed.get(field) for row in conflicts)
        },
    }


def import_reviewed_result(connection, audit_id, fields, user_confirmed=False, conflict_resolution=None, run_analysis=False, downstream_runner=None):
    if not user_confirmed:
        return ImportResult(False, "confirmation_required", audit_id=audit_id)
    audit = connection.execute(
        "SELECT * FROM kubios_screenshot_imports WHERE id = ?", (audit_id,)
    ).fetchone()
    if not audit:
        return ImportResult(False, "audit_not_found", audit_id=audit_id)
    audit = dict(audit)
    group_confirmed = False
    if audit.get("measurement_group_id"):
        group = connection.execute(
            "SELECT confirmed_by_user FROM kubios_measurement_groups WHERE id=?",
            (audit["measurement_group_id"],),
        ).fetchone()
        group_confirmed = bool(group and group[0])
    normalized, errors = validate_confirmed_fields(
        fields, required_fields=("date",) if group_confirmed else None
    )
    if errors:
        return ImportResult(False, "validation_failed", audit_id=audit_id, conflict={"errors": errors})
    if audit.get("imported_record_id"):
        return ImportResult(True, "already_imported", audit["imported_record_id"], audit_id)

    conflicts = detect_conflicts(connection, normalized["date"], audit["file_sha256"])
    if conflicts and conflict_resolution not in CONFLICT_RESOLUTIONS:
        return ImportResult(False, "conflict_review_required", audit_id=audit_id,
                            conflict=conflict_summary(conflicts, normalized))
    if conflict_resolution == "cancel":
        return ImportResult(False, "cancelled", audit_id=audit_id)
    if conflicts and conflict_resolution == "keep_existing":
        mark_reviewed(connection, audit_id, "skipped_existing")
        return ImportResult(True, "skipped_existing", audit_id=audit_id,
                            conflict=conflict_summary(conflicts, normalized))

    preferred = conflict_resolution == "use_screenshot"
    if preferred:
        connection.execute(
            "UPDATE kubios_morning_hrv_raw SET is_daily_preferred = 0 WHERE date = ?",
            (normalized["date"],),
        )
    reviewed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    external_id = normalized.get("measurement_time") or f"{normalized['date']}:{audit['file_sha256'][:12]}"
    row = {
        "external_id": external_id,
        "date": normalized["date"],
        "measurement_time": (
            f"{normalized['date']}T{normalized['measurement_time']}"
            if normalized.get("measurement_time") and "T" not in normalized["measurement_time"]
            else normalized.get("measurement_time")
        ),
        "rmssd": normalized.get("rmssd"),
        "mean_hr": normalized.get("mean_hr"),
        "readiness": normalized.get("readiness"),
        "raw": {"confirmed_fields": normalized, "parser_version": audit["parser_version"]},
        "source_type": "screenshot_ocr",
        "source_file_sha256": audit["file_sha256"],
        "ocr_confidence": audit.get("overall_ocr_confidence"),
        "reviewed": True,
        "reviewed_at": reviewed_at,
        "import_method": "screenshot_ocr",
        "is_daily_preferred": preferred,
        "measurement_group_id": audit.get("measurement_group_id"),
    }
    row.update(normalized)
    # Keep the existing CSV normalizer/upsert path as the sole Kubios raw writer.
    kubios_import.upsert_kubios_rows(connection, [row])
    raw_record = connection.execute(
        "SELECT id FROM kubios_morning_hrv_raw WHERE source_file_sha256 = ?",
        (audit["file_sha256"],),
    ).fetchone()
    raw_record_id = raw_record[0]
    kubios_import.sync_daily_metrics(connection, [row])
    mark_reviewed(connection, audit_id, "imported", raw_record_id)

    downstream = {}
    if run_analysis and downstream_runner:
        downstream = downstream_runner(normalized["date"])
        mark_downstream_updated(connection, audit_id, bool(downstream.get("success")))
    return ImportResult(True, "imported", raw_record_id, audit_id,
                        conflict=conflict_summary(conflicts, normalized) if conflicts else None,
                        downstream=downstream)
