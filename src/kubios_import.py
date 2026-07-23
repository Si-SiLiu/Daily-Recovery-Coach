import argparse
import csv
import hashlib
import json
from pathlib import Path

try:
    from .db import BASE_DIR, DB_PATH, connect
    from .kubios_screenshot.config import load_config as load_screenshot_config
except ImportError:
    from db import BASE_DIR, DB_PATH, connect
    from kubios_screenshot.config import load_config as load_screenshot_config


IMPORTS_DIR = BASE_DIR / "data" / "imports"
DEFAULT_CSV_PATH = IMPORTS_DIR / "kubios_morning_hrv.csv"
SOURCE = "kubios"

FIELD_ALIASES = {
    "date": {"date", "measurement date", "測定日", "日期"},
    "measurement_time": {
        "time",
        "measurement time",
        "timestamp",
        "datetime",
        "測定時刻",
        "时间",
    },
    "rmssd": {"rmssd", "rmssd ms", "rmssd (ms)"},
    "mean_hr": {"mean hr", "mean_hr", "mean heart rate", "mean heart rate (bpm)", "heart rate"},
    "readiness": {"readiness", "readiness score", "readiness status", "status"},
    "mean_rr_ms": {"mean rr", "mean rr ms", "mean rr (ms)"},
    "sdnn_ms": {"sdnn", "sdnn ms", "sdnn (ms)"},
    "poincare_sd1_ms": {"poincare sd1", "poincaré sd1", "sd1"},
    "poincare_sd2_ms": {"poincare sd2", "poincaré sd2", "sd2"},
    "stress_index": {"stress index"},
    "respiratory_rate_bpm": {"respiratory rate", "respiration rate", "breaths/min"},
    "lf_power_ms2": {"lf power", "lf power ms2"},
    "hf_power_ms2": {"hf power", "hf power ms2"},
    "lf_power_nu": {"lf power n.u.", "lf nu"},
    "hf_power_nu": {"hf power n.u.", "hf nu"},
    "lf_hf_ratio": {"lf/hf ratio", "lf hf ratio"},
    "pns_index": {"pns index"}, "sns_index": {"sns index"},
    "physiological_age": {"physiological age"},
    "measurement_quality": {"measurement quality", "quality"},
    "mood_code": {"mood"}, "recovery_status": {"recovery status"},
    "artefact_correction_percent": {"artefact correction", "artifact correction"},
    "measurement_duration_seconds": {"measurement duration", "duration seconds"},
}

EXTENDED_NUMERIC_FIELDS = (
    "mean_rr_ms","sdnn_ms","poincare_sd1_ms","poincare_sd2_ms","stress_index",
    "respiratory_rate_bpm","lf_power_ms2","hf_power_ms2","lf_power_nu","hf_power_nu",
    "lf_hf_ratio","pns_index","sns_index","physiological_age","artefact_correction_percent",
    "measurement_duration_seconds",
)


class KubiosImportError(RuntimeError):
    pass


def normalize_header(value):
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def build_column_map(fieldnames):
    normalized = {normalize_header(name): name for name in fieldnames or []}
    column_map = {}
    for target, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            source = normalized.get(normalize_header(alias))
            if source:
                column_map[target] = source
                break
    return column_map


def parse_float(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalize_measurement_quality(value):
    text = str(value or "").strip().upper()
    return text if text in {"GOOD", "ACCEPTABLE", "POOR", "INVALID"} else None


def normalize_date(value):
    text = str(value or "").strip()
    if not text:
        return None
    if "T" in text:
        return text[:10]
    if " " in text and len(text.split()[0]) >= 8:
        return text.split()[0]
    return text[:10]


def normalize_measurement_time(value, date_value):
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) <= 8 and ":" in text and date_value:
        return f"{date_value}T{text}"
    return text


def read_kubios_csv(csv_path=DEFAULT_CSV_PATH):
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise KubiosImportError(f"找不到 Kubios CSV：{csv_path}")

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        column_map = build_column_map(reader.fieldnames)
        if "date" not in column_map:
            raise KubiosImportError("Kubios CSV 缺少 date 字段。")

        rows = []
        for row in reader:
            date_value = normalize_date(row.get(column_map["date"]))
            if not date_value:
                continue

            measurement_time = normalize_measurement_time(
                row.get(column_map.get("measurement_time", "")),
                date_value,
            )
            normalized = {
                    "date": date_value,
                    "measurement_time": measurement_time,
                    "rmssd": parse_float(row.get(column_map.get("rmssd", ""))),
                    "mean_hr": parse_float(row.get(column_map.get("mean_hr", ""))),
                    "readiness": (
                        row.get(column_map.get("readiness", "")) or None
                    ),
                    "raw": dict(row),
                }
            for field in EXTENDED_NUMERIC_FIELDS:
                normalized[field] = parse_float(row.get(column_map.get(field, "")))
            normalized["measurement_quality"] = normalize_measurement_quality(
                row.get(column_map.get("measurement_quality", ""))
            )
            for field in ("mood_code", "recovery_status"):
                normalized[field] = (row.get(column_map.get(field, "")) or None)
            rows.append(normalized)
    return rows


def external_id_for_row(row):
    return row.get("external_id") or row.get("measurement_time") or row["date"]


def upsert_kubios_rows(connection, rows):
    sql = """
    INSERT INTO kubios_morning_hrv_raw (
        source,
        external_id,
        date,
        raw_json,
        rmssd,
        mean_hr,
        readiness,
        measurement_time,
        source_type,
        source_file_sha256,
        ocr_confidence,
        reviewed,
        reviewed_at,
        import_method,
        is_daily_preferred
        ,stress_index,respiratory_rate,measurement_quality
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(source, external_id, date) DO UPDATE SET
        raw_json = excluded.raw_json,
        rmssd = excluded.rmssd,
        mean_hr = excluded.mean_hr,
        readiness = excluded.readiness,
        measurement_time = excluded.measurement_time,
        source_type = excluded.source_type,
        source_file_sha256 = excluded.source_file_sha256,
        ocr_confidence = excluded.ocr_confidence,
        reviewed = excluded.reviewed,
        reviewed_at = excluded.reviewed_at,
        import_method = excluded.import_method,
        is_daily_preferred = excluded.is_daily_preferred,
        stress_index = excluded.stress_index,
        respiratory_rate = excluded.respiratory_rate,
        measurement_quality = excluded.measurement_quality,
        updated_at = CURRENT_TIMESTAMP
    """
    for row in rows:
        connection.execute(
            sql,
            (
                SOURCE,
                external_id_for_row(row),
                row["date"],
                json.dumps(row["raw"], ensure_ascii=False, sort_keys=True),
                row["rmssd"],
                row["mean_hr"],
                row["readiness"],
                row["measurement_time"],
                row.get("source_type", "csv"),
                row.get("source_file_sha256"),
                row.get("ocr_confidence"),
                int(row.get("reviewed", True)),
                row.get("reviewed_at"),
                row.get("import_method", "csv"),
                int(row.get("is_daily_preferred", False)),
                row.get("stress_index"),
                row.get("respiratory_rate", row.get("respiratory_rate_bpm")),
                normalize_measurement_quality(row.get("measurement_quality")),
            ),
        )
        try:
            from .kubios_metrics.normalizer import import_raw
        except ImportError:
            from kubios_metrics.normalizer import import_raw
        import_raw(connection, row, row.get("source_type", "csv"), row.get("import_method", "csv"), row.get("reviewed", True))
    connection.commit()
    return len(rows)


def sync_daily_metrics(connection, rows):
    sql = """
    INSERT INTO daily_recovery_metrics (
        date,
        training_count,
        training_calories,
        morning_rmssd,
        morning_mean_hr,
        kubios_readiness
    )
    VALUES (?, 0, 0, ?, ?, ?)
    ON CONFLICT(date) DO UPDATE SET
        morning_rmssd = excluded.morning_rmssd,
        morning_mean_hr = excluded.morning_mean_hr,
        kubios_readiness = excluded.kubios_readiness,
        updated_at = CURRENT_TIMESTAMP
    """
    try:
        from .kubios_metrics.config import load_source_config
    except ImportError:
        from kubios_metrics.config import load_source_config
    priorities = load_source_config()["source_priority"]
    clauses = []
    for item in priorities:
        source = item["source_type"]
        rank = int(item["priority"])
        clauses.append(f"WHEN '{source}' THEN {rank}")
        if source == "reviewed_screenshot_ocr":
            clauses.append(f"WHEN 'screenshot_ocr' THEN {rank}")
    priority_sql = "CASE source_type " + " ".join(clauses) + " ELSE 999 END"
    dates = sorted({row["date"] for row in rows})
    selected = []
    for date_value in dates:
        row = connection.execute(
            f"""
            SELECT date, rmssd, mean_hr, readiness
            FROM kubios_morning_hrv_raw
            WHERE date = ? AND reviewed = 1
            ORDER BY is_daily_preferred DESC, {priority_sql} ASC,
                     measurement_time DESC, updated_at DESC, id DESC
            LIMIT 1
            """,
            (date_value,),
        ).fetchone()
        if row:
            selected.append(dict(row))

    for row in selected:
        connection.execute(
            sql,
            (
                row["date"],
                row["rmssd"],
                row["mean_hr"],
                row["readiness"],
            ),
        )
    connection.commit()
    return len(selected)


def rebuild_kubios_daily_metrics(connection, dates=None):
    if dates is None:
        dates = [row[0] for row in connection.execute(
            "SELECT DISTINCT date FROM kubios_morning_hrv_raw WHERE reviewed = 1"
        )]
    return sync_daily_metrics(connection, [{"date": value} for value in dates])


def import_kubios_csv(csv_path=DEFAULT_CSV_PATH, connection=None):
    owns_connection = connection is None
    connection = connection or connect()
    rows = read_kubios_csv(csv_path)
    digest = hashlib.sha256(Path(csv_path).read_bytes()).hexdigest()
    for row in rows:
        row["source_file_sha256"] = digest
    raw_count = upsert_kubios_rows(connection, rows)
    metrics_count = sync_daily_metrics(connection, rows)

    if owns_connection:
        connection.close()

    return {
        "raw_rows": raw_count,
        "daily_metrics": metrics_count,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Import Kubios Morning HRV CSV.")
    parser.add_argument("--csv", dest="csv_path", default=str(DEFAULT_CSV_PATH))
    return parser.parse_args()


def main():
    args = parse_args()
    result = import_kubios_csv(args.csv_path)
    print(f"Database: {DB_PATH}")
    print(f"Kubios raw rows imported: {result['raw_rows']}")
    print(f"Daily metrics updated: {result['daily_metrics']}")


if __name__ == "__main__":
    try:
        main()
    except KubiosImportError as exc:
        raise SystemExit(str(exc))
