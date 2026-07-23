"""Fail-closed safety rules for deterministic coaching advice."""

from .models import CoachInput

DISCLAIMER = "本建议由本地确定性规则生成，不构成医疗诊断或治疗意见。"
URGENT_TERMS = ("胸痛", "呼吸困难", "晕厥", "意识不清", "严重出血", "剧烈疼痛")


def _conservative(output, rules, missing_score=False):
    for key, status, advice in (
        ("morning_training", "technique_only", "数据证据有限，只建议轻量技术练习，并按实时主观状态调整。"),
        ("evening_training", "mobility_only", "数据证据有限，建议改为轻松活动或节奏走位。"),
    ):
        entry = output[key]
        entry["status"] = status
        entry["advice"] = advice
        entry["volume_adjustment_percent"] = None if missing_score else rules["training_adjustments"][status]["volume"]
        entry["intensity_adjustment_percent"] = None if missing_score else rules["training_adjustments"][status]["intensity"]


def apply_safety_fallback(data: CoachInput, output, rules, symptoms=None):
    limitations, notices = output["data_limitations"], output["safety_notices"]
    low_confidence = data.confidence_level in {None, "very_low", "insufficient"}
    incomplete = data.data_completeness is None or data.data_completeness < rules["minimum_data_completeness"]
    if data.recovery_score is None:
        _conservative(output, rules, missing_score=True)
        output["recovery_advice"] = {"status": "insufficient_data", "advice": "恢复分数缺失，不生成训练强度结论。",
                                     "monitoring": "根据主观感受和实时状态保守调整。"}
        limitations.append("恢复分数缺失，训练调整百分比不可用。")
    elif low_confidence or incomplete:
        _conservative(output, rules)
        output["recovery_advice"]["status"] = "insufficient_data"
        output["recovery_advice"]["advice"] = "证据不足，本地规则已降级为保守建议。"
    if low_confidence:
        limitations.append("置信度过低或缺失，建议已安全降级。")
    if incomplete:
        limitations.append("数据完整性低于本地规则要求。")
    hrv_down = data.baseline_status.get("nightly_hrv_rmssd") == "below_baseline"
    hr_up = data.baseline_status.get("nightly_resting_hr") == "above_baseline"
    sleep_low = ((data.sleep_duration_hours is not None and data.sleep_duration_hours < rules["sleep_insufficient_hours"])
                 or (data.sleep_score is not None and data.sleep_score < rules["sleep_score_low"]))
    if data.recovery_score is not None and data.recovery_score >= rules["recovery_score_thresholds"]["high"] and hrv_down and hr_up and sleep_low:
        limitations.append("结构化证据存在冲突，请根据主观感受和实时状态保守调整。")
    symptom_text = " ".join(symptoms or []) if not isinstance(symptoms, str) else symptoms
    if symptom_text and any(term in symptom_text for term in URGENT_TERMS):
        for key in ("morning_training", "evening_training"):
            output[key].update(status="rest", volume_adjustment_percent=-100,
                               intensity_adjustment_percent=-100, advice="停止训练，并及时寻求专业帮助。")
        output["recovery_advice"] = {"status": "rest_and_monitor", "advice": "停止训练，不要依赖本地建议继续运动。",
                                     "monitoring": "及时寻求专业帮助。"}
        notices.append("已根据用户明确输入的紧急症状触发停止训练降级。")
    notices.insert(0, DISCLAIMER)
    output["generated_without_cloud_ai"] = True
    output["data_limitations"] = list(dict.fromkeys(limitations))[:20]
    output["safety_notices"] = list(dict.fromkeys(notices))[:10]
    return output
