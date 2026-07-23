"""Deterministic morning strength and evening Hip-Hop recommendations."""

from .models import CoachInput


def _advice(status, session):
    labels = {
        "normal": "可按既定安排进行，训练中仍根据主观状态调整。",
        "moderate_reduction": "建议适度减少训练量，保留动作质量并避免额外加量。",
        "major_reduction": "建议明显减量，以低风险动作和充分组间恢复为主。",
        "technique_only": "建议只做轻量技术练习，不追求强度或训练量。",
        "mobility_only": "建议改为灵活性、节奏走位或轻松活动。",
        "rest": "建议暂停本次训练，把恢复和状态观察放在首位。",
    }
    return f"{session}：{labels[status]}"


def _entry(status, schedule, session, rules, adjustments=True):
    values = rules["training_adjustments"][status]
    return {
        "status": status,
        "schedule": schedule,
        "volume_adjustment_percent": values["volume"] if adjustments else None,
        "intensity_adjustment_percent": values["intensity"] if adjustments else None,
        "advice": _advice(status, session),
    }


def generate_training_advice(data: CoachInput, rules):
    schedule = rules["fixed_schedule"]
    score = data.recovery_score
    level = data.confidence_level
    completeness = data.data_completeness
    missing_score = score is None
    low_confidence = level in {None, "very_low", "insufficient"}
    incomplete = completeness is None or completeness < rules["minimum_data_completeness"]
    hrv_down = data.baseline_status.get("nightly_hrv_rmssd") == "below_baseline"
    hr_up = data.baseline_status.get("nightly_resting_hr") == "above_baseline"
    sleep_low = (
        data.sleep_duration_hours is not None
        and data.sleep_duration_hours < rules["sleep_insufficient_hours"]
    ) or (
        data.sleep_score is not None and data.sleep_score < rules["sleep_score_low"]
    )
    triple_pressure = hrv_down and hr_up and sleep_low
    stress_high = data.stress_load_score is not None and data.stress_load_score >= rules["high_load_score"]

    if missing_score:
        morning, evening, adjustments = "technique_only", "mobility_only", False
    elif low_confidence or incomplete:
        morning, evening, adjustments = "technique_only", "mobility_only", True
    elif triple_pressure:
        morning, evening, adjustments = "major_reduction", "technique_only", True
    elif score >= rules["recovery_score_thresholds"]["high"]:
        morning, evening, adjustments = "normal", "normal", True
    elif score >= rules["recovery_score_thresholds"]["medium"]:
        if sleep_low or stress_high:
            morning, evening = "moderate_reduction", "technique_only"
        else:
            morning, evening = "normal", "moderate_reduction"
        adjustments = True
    elif score >= rules["recovery_score_thresholds"]["low"]:
        morning, evening, adjustments = "major_reduction", "technique_only", True
    else:
        morning, evening, adjustments = "rest", "mobility_only", True

    # High load alone never forces rest when deterministic recovery remains high.
    return {
        "morning_training": _entry(
            morning, schedule["morning_strength"], "上午力量训练", rules, adjustments
        ),
        "evening_training": _entry(
            evening, schedule["evening_hip_hop"], "晚间 Hip-Hop", rules, adjustments
        ),
    }
