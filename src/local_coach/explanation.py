"""Privacy-safe deterministic rationale for Local Coach outputs."""

from .models import CoachInput

LABELS = {
    "nightly_hrv_rmssd": "夜间 HRV", "nightly_resting_hr": "夜间静息心率",
    "respiration_rate": "呼吸频率", "morning_rmssd": "晨测 RMSSD",
    "morning_mean_hr": "晨测平均心率", "sleep_score": "睡眠评分",
    "sleep_duration": "睡眠时长", "kubios_readiness": "Kubios Readiness",
    "steps": "步数", "active_calories": "活动负荷",
    "training_duration": "训练时长", "training_calories": "训练负荷",
}


def _safe_factor(factor):
    if not isinstance(factor, dict):
        return None
    label = factor.get("label") or LABELS.get(factor.get("metric_name"), "结构化因素")
    status = {"above_baseline": "高于个人基线", "below_baseline": "低于个人基线",
              "within_baseline": "接近个人基线"}.get(
        factor.get("status"), "已纳入确定性解释")
    return f"{label}：{status}"


def build_rationale(data: CoachInput):
    explanation = data.explanation_json or {}
    positive = [x for x in (_safe_factor(v) for v in explanation.get("positive", [])) if x]
    negative = [x for x in (_safe_factor(v) for v in explanation.get("negative", [])) if x]
    confidence = [f"置信度等级：{data.confidence_level}" if data.confidence_level else "置信度等级缺失"]
    confidence.append("数据完整性已纳入安全分级" if data.data_completeness is not None else "数据完整性缺失")
    fallbacks = []
    if data.fallback_used:
        fallbacks.append("上游恢复评分使用了回退路径")
    if data.is_historical:
        fallbacks.append("这是历史日期建议，不代表当前实时状态")
    missing = explanation.get("missing", [])
    if missing:
        fallbacks.append("缺失因素：" + "、".join(LABELS.get(x, x) for x in missing[:8]))
    return {"positive_factors": positive[:20], "negative_factors": negative[:20],
            "confidence_factors": confidence[:20], "fallbacks": fallbacks[:20]}
