"""Deterministic active-recovery and monitoring direction."""


def generate_recovery_advice(data, rules):
    score = data.recovery_score
    if score is None:
        return {"status": "insufficient_data", "advice": "恢复分数缺失，不生成训练强度结论。", "monitoring": "根据主观感受和实时状态保守调整。"}
    if score >= rules["recovery_score_thresholds"]["high"]:
        status, advice = "normal", "维持正常恢复习惯，高负荷本身不自动等于必须休息。"
    elif score >= rules["recovery_score_thresholds"]["medium"]:
        status, advice = "active_recovery", "安排轻松活动、放松和充足间歇，避免额外加量。"
    elif score >= rules["recovery_score_thresholds"]["low"]:
        status, advice = "reduce_load", "恢复优先并明显控制当天总训练负荷。"
    else:
        status, advice = "rest_and_monitor", "以休息和轻松活动为主，持续观察主观状态。"
    return {"status": status, "advice": advice, "monitoring": "如实际疼痛、症状或状态明显异常，应停止训练并寻求专业帮助。"}
