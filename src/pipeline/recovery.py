try:
    from src.db import connect
    from src.recovery_score import build_recovery_scores, upsert_recovery_scores
except ImportError:
    from db import connect
    from recovery_score import build_recovery_scores, upsert_recovery_scores


def run(context, dry_run=False):
    if dry_run:
        return {"recovery_updated": 0}
    connection = connect()
    try:
        scores = build_recovery_scores(connection)
        count = upsert_recovery_scores(connection, scores)
    finally:
        connection.close()
    return {"recovery_updated": count}
