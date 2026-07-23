from pathlib import Path

try:
    from src import kubios_import, polar_import
    from src.db import DB_PATH, connect
except ImportError:
    import kubios_import
    import polar_import
    from db import DB_PATH, connect


RAW_TABLES = (
    "polar_daily_activity_raw",
    "polar_training_sessions_raw",
    "polar_sleep_raw",
    "polar_nightly_recharge_raw",
    "polar_cardio_load_raw",
    "polar_continuous_hr_raw",
    "kubios_morning_hrv_raw",
)


def _counts(connection):
    return {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in RAW_TABLES
    }


def run(context, dry_run=False, imports_dir=kubios_import.IMPORTS_DIR, db_path=DB_PATH):
    imports_dir = Path(imports_dir)
    kubios_files = sorted(imports_dir.glob("*.csv")) if imports_dir.exists() else []
    if dry_run:
        return {
            "records_imported": 0,
            "records_processed": 0,
            "kubios_files": len(kubios_files),
        }

    connection = connect(db_path)
    try:
        before = _counts(connection)
        polar_result = polar_import.import_raw_polar_data(connection=connection)
        kubios_results = [
            kubios_import.import_kubios_csv(path, connection=connection)
            for path in kubios_files
        ]
        after = _counts(connection)
    finally:
        connection.close()

    records_imported = sum(max(after[name] - before[name], 0) for name in RAW_TABLES)
    records_processed = sum(polar_result.values()) + sum(
        result["raw_rows"] for result in kubios_results
    )
    return {
        "records_imported": records_imported,
        "records_processed": records_processed,
        "kubios_files": len(kubios_files),
    }
