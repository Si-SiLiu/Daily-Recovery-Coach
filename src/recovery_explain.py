"""Deterministic, locale-aware display explanations for persisted recovery facts."""

from src.i18n import get_translator


METRIC_RULES = {
    "nightly_hrv_rmssd": ("metrics.nightly_hrv", "higher_is_better", " ms"),
    "morning_rmssd": ("metrics.morning_rmssd", "higher_is_better", " ms"),
    "nightly_resting_hr": ("metrics.resting_hr", "lower_is_better", " bpm"),
    "morning_mean_hr": ("metrics.morning_hr", "lower_is_better", " bpm"),
    "respiration_rate": ("metrics.respiration", "lower_is_better", ""),
    "sleep_score": ("metrics.sleep_score", "higher_is_better", ""),
    "sleep_duration": ("metrics.sleep_duration", "higher_is_better", " h"),
    "kubios_readiness": ("metrics.kubios", "higher_is_better", ""),
    "steps": ("metrics.steps", "higher_is_load", ""),
    "active_calories": ("metrics.active_calories", "higher_is_load", " kcal"),
    "training_duration": ("metrics.training_duration", "higher_is_load", " min"),
    "training_calories": ("reports.training_calories", "higher_is_load", " kcal"),
}


def baseline_is_usable(row):
    return bool(row and row.get("status") != "insufficient_data" and row.get("latest_value") is not None and row.get("median_value") is not None and row.get("valid_days", 0) >= 7)


def deviation_strength(row):
    for key in ("robust_z_score", "z_score"):
        value = row.get(key)
        if value is not None:
            return abs(float(value))
    percent = row.get("percent_change")
    return abs(float(percent)) / 10 if percent is not None else 0


def classify_impact(direction, status):
    if status == "within_baseline": return "neutral"
    if direction == "higher_is_better": return "positive" if status == "above_baseline" else "negative"
    if direction == "lower_is_better": return "positive" if status == "below_baseline" else "negative"
    if direction == "higher_is_load": return "negative" if status == "above_baseline" else "positive"
    return "neutral"


def format_number(value, language="zh-CN"):
    if value is None: return get_translator(language)("common.no_data")
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:.1f}"


def build_factor(metric_name, baseline, language="zh-CN"):
    tr = get_translator(language)
    label_key, direction, suffix = METRIC_RULES[metric_name]
    status = baseline.get("status")
    percent = baseline.get("percent_change")
    status_key = {"above_baseline": "recovery.above_personal", "below_baseline": "recovery.below_personal", "within_baseline": "recovery.within_personal"}.get(status, "baseline.insufficient_data")
    label = tr(label_key)
    return {
        "metric_name": metric_name, "label": label, "impact": classify_impact(direction, status),
        "status": status, "current_value": baseline.get("latest_value"), "baseline_value": baseline.get("median_value"),
        "percent_change": percent, "strength": deviation_strength(baseline),
        "message": tr("recovery.factor", label=label, current=format_number(baseline.get("latest_value"), language), suffix=suffix,
                      median=format_number(baseline.get("median_value"), language),
                      change=tr("recovery.change_missing") if percent is None else f"{float(percent):+.1f}%", status=tr(status_key)),
    }


def _localize_recommendation(value, tr):
    aliases = {"normal_training": "normal_training", "正常训练": "normal_training", "normal": "normal_training",
               "moderate_training": "moderate_training", "适度训练": "moderate_training",
               "reduced_training": "reduced_training", "减量训练": "reduced_training",
               "recovery_priority": "recovery_priority", "恢复优先": "recovery_priority"}
    code = aliases.get(value)
    return tr(f"recovery.{code}") if code else (value or tr("recovery.no_recommendation"))


def generate_recovery_explanation(latest, baselines, language="zh-CN"):
    tr = get_translator(language)
    if not latest:
        return {"summary": tr("recovery.no_score"), "positive": [], "negative": [], "neutral": [], "missing": list(METRIC_RULES)}
    groups = {"positive": [], "negative": [], "neutral": []}; missing = []
    for metric_name in METRIC_RULES:
        baseline = (baselines or {}).get(metric_name)
        if not baseline_is_usable(baseline): missing.append(metric_name); continue
        factor = build_factor(metric_name, baseline, language)
        groups[factor["impact"]].append(factor)
    for factors in groups.values(): factors.sort(key=lambda item: item["strength"], reverse=True)
    score = latest.get("recovery_score")
    return {"summary": tr("recovery.summary", version=latest.get("score_version") or tr("recovery.unknown_version"),
                          score=tr("common.no_data") if score is None else score,
                          recommendation=_localize_recommendation(latest.get("recommendation"), tr)), **groups, "missing": missing}


def metric_labels(metric_names, language="zh-CN"):
    tr = get_translator(language)
    return [tr(METRIC_RULES[name][0]) for name in metric_names if name in METRIC_RULES]
