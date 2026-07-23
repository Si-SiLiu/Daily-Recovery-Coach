try:
    from src.baseline import calculate_all_baselines
except ImportError:
    from baseline import calculate_all_baselines


def run(context, dry_run=False):
    if dry_run:
        return {"baseline_updated": 0}
    summary = calculate_all_baselines()
    return {
        "baseline_updated": summary["records"],
        "baseline_dates": summary["dates"],
    }
