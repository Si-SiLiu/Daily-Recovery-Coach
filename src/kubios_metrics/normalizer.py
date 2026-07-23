import argparse
from collections import defaultdict

from src.db import connect

from . import NORMALIZATION_VERSION
from .config import source_priority
from .models import NormalizedMeasurement, RawMeasurement
from .selector import select_primary
from .storage import NORMALIZED_VALUE_FIELDS, RAW_VALUE_FIELDS, insert_raw, mark_primary, upsert_normalized
from .validation import clean_values, validate_date


ALIASES = {
    "rmssd":"rmssd_ms", "mean_hr":"mean_hr_bpm", "readiness":"readiness_percent",
    "sdnn":"sdnn_ms", "artefact_correction":"artefact_correction_percent",
    "measurement_duration":"measurement_duration_seconds",
}


def normalize_input(row, source_type, import_method=None, reviewed=None):
    values = {ALIASES.get(key, key): value for key, value in dict(row).items()}
    source = "reviewed_screenshot_ocr" if source_type == "screenshot_ocr" else source_type
    is_reviewed = bool(row.get("reviewed", reviewed if reviewed is not None else source == "csv"))
    return RawMeasurement(
        date=validate_date(row.get("date")), measurement_time=row.get("measurement_time"),
        measurement_group_id=row.get("measurement_group_id"), source_type=source,
        import_method=import_method or row.get("import_method") or source,
        source_priority=source_priority(source), reviewed=is_reviewed,
        selected_as_primary=bool(row.get("selected_as_primary") or row.get("is_daily_preferred")),
        selection_reason=row.get("selection_reason"), source_file_sha256=row.get("source_file_sha256"),
        parser_version=row.get("parser_version"), ocr_confidence=row.get("ocr_confidence"),
        values=clean_values(values), raw_json=row.get("raw") or row.get("raw_json") or {},
    )


def _completeness(row):
    core = ("rmssd_ms","mean_hr_bpm","readiness_percent","pns_index","sns_index","measurement_quality")
    return round(100 * sum(row.get(name) is not None for name in core) / len(core), 2)


def normalized_from_raw(raw, reason):
    values = {name: raw.get(name) for name in NORMALIZED_VALUE_FIELDS}
    return NormalizedMeasurement(
        date=raw["date"], measurement_time=raw.get("measurement_time"),
        measurement_group_id=raw.get("measurement_group_id"), source_raw_table="kubios_hrv_measurements_raw",
        source_raw_id=raw["id"], source_type=raw["source_type"], selection_reason=reason,
        source_priority=raw["source_priority"], core_data_completeness=_completeness(raw),
        normalization_version=NORMALIZATION_VERSION, values=values,
    )


def rebuild(connection, dates=None, dry_run=False):
    query = "SELECT * FROM kubios_hrv_measurements_raw"
    params = []
    if dates:
        query += f" WHERE date IN ({','.join('?' for _ in dates)})"; params = list(dates)
    rows = [dict(row) for row in connection.execute(query, params).fetchall()]
    grouped = defaultdict(list)
    for row in rows: grouped[row["date"]].append(row)
    built = []
    for date_value, candidates in sorted(grouped.items()):
        collapsed = []
        group_ids = {row.get("measurement_group_id") for row in candidates if row.get("measurement_group_id")}
        consumed = set()
        for group_id in group_ids:
            group = connection.execute("SELECT confirmed_by_user FROM kubios_measurement_groups WHERE id=?", (group_id,)).fetchone()
            members = [row for row in candidates if row.get("measurement_group_id") == group_id]
            if not group or not group[0]:
                continue
            base, _ = select_primary(members)
            if not base:
                continue
            merged = dict(base)
            ordered = sorted(members, key=lambda row: (row["source_priority"], -int(row.get("selected_as_primary") or 0), row["id"]))
            for field in RAW_VALUE_FIELDS:
                merged[field] = next((row.get(field) for row in ordered if row.get(field) is not None), None)
            merged["selection_reason"] = "confirmed_measurement_group"
            collapsed.append(merged); consumed.update(row["id"] for row in members)
        collapsed.extend(row for row in candidates if row["id"] not in consumed)
        chosen, reason = select_primary(collapsed)
        if not chosen: continue
        if chosen.get("selection_reason") == "confirmed_measurement_group":
            reason = "confirmed_measurement_group"
        built.append(normalized_from_raw(chosen, reason))
        if not dry_run:
            mark_primary(connection, date_value, chosen["id"], reason)
            upsert_normalized(connection, built[-1])
    if not dry_run: connection.commit()
    return {"raw_records":len(rows),"normalized_records":len(built),"dry_run":dry_run}


def import_raw(connection, row, source_type, import_method=None, reviewed=None, dry_run=False):
    measurement = normalize_input(row, source_type, import_method, reviewed)
    if dry_run: return measurement
    raw_id = insert_raw(connection, measurement); connection.commit(); return raw_id


def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("--dry-run",action="store_true"); parser.add_argument("--all",action="store_true"); parser.add_argument("--date",action="append")
    args=parser.parse_args(argv)
    with connect() as connection:
        result=rebuild(connection, dates=args.date, dry_run=args.dry_run)
    print(f"raw_records={result['raw_records']} normalized_records={result['normalized_records']} dry_run={str(result['dry_run']).lower()}")


if __name__ == "__main__": main()
