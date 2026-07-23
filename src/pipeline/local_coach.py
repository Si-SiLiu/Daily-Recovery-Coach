"""Local Coach pipeline step; no cloud runtime is reachable from here."""

try:
    from src.local_coach.engine import run_local_coach
    from src.local_coach.prospective import evaluate_prospective
    from src.local_coach.collection import monitor_daily_collection
except ImportError:
    from local_coach.engine import run_local_coach
    from local_coach.prospective import evaluate_prospective
    from local_coach.collection import monitor_daily_collection


def run(context, dry_run=False):
    result = run_local_coach(all_dates=True, dry_run=dry_run)
    progress = evaluate_prospective()
    daily = monitor_daily_collection()
    return {
        **result,
        "prospective_eligible_days": progress["eligible_unique_days"],
        "prospective_target_days": progress["target_unique_days"],
        "prospective_remaining_days": progress["remaining_unique_days"],
        "prospective_status": progress["status"],
        "daily_collection_status": daily["status"],
        "daily_collection_on_track": daily["on_track"],
        "today_collected": daily["today_collected"],
        "current_collection_streak_days": daily["current_streak_days"],
        "overdue_missing_days": daily["overdue_missing_days"],
    }
