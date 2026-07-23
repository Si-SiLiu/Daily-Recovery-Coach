try:
    from src.db import DB_PATH, connect
    from src.kubios_import import rebuild_kubios_daily_metrics
except ImportError:
    from db import DB_PATH, connect
    from kubios_import import rebuild_kubios_daily_metrics


def run(context, dry_run=False, db_path=None):
    connection = connect(db_path)
    try:
        imported = connection.execute(
            "SELECT COUNT(*) FROM kubios_screenshot_imports WHERE reviewed = 1 AND import_status = 'imported'"
        ).fetchone()[0]
        pending = connection.execute(
            "SELECT COUNT(*) FROM kubios_screenshot_imports WHERE reviewed = 0"
        ).fetchone()[0]
        if dry_run:
            return {"records_processed": imported, "metrics_updated": 0, "review_pending": pending}
        updated = rebuild_kubios_daily_metrics(connection)
        return {"records_processed": imported, "metrics_updated": updated, "review_pending": pending}
    finally:
        connection.close()
