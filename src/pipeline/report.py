try:
    from src.report import generate_daily_report
    from src.i18n import load_language_preference
except ImportError:
    from report import generate_daily_report
    from i18n import load_language_preference


def run(context, dry_run=False):
    if dry_run:
        return {"reports_generated": 0, "report_path": None}
    path, _ = generate_daily_report(language=load_language_preference())
    return {"reports_generated": 1, "report_path": str(path)}
