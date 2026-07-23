"""Deterministic sleep opportunity and routine guidance."""


def generate_sleep_advice(data, rules):
    hours_low = data.sleep_duration_hours is not None and data.sleep_duration_hours < rules["sleep_insufficient_hours"]
    score_low = data.sleep_score is not None and data.sleep_score < rules["sleep_score_low"]
    if hours_low or score_low:
        return {
            "tonight_sleep_target_direction": "earlier_bedtime",
            "bedtime_adjustment": "建议适当提前就寝、增加睡眠机会，并降低睡前刺激。",
            "sleep_priority": "high",
            "rationale": "近期睡眠证据低于本地规则阈值，优先恢复比额外加量更稳妥。",
        }
    if data.sleep_duration_hours is None and data.sleep_score is None:
        return {
            "tonight_sleep_target_direction": "increase_sleep_opportunity",
            "bedtime_adjustment": "睡眠数据不足，建议保持规律作息并预留充足睡眠机会。",
            "sleep_priority": "elevated",
            "rationale": "设备睡眠数据缺失，不能把睡眠阶段估计当作医学测量。",
        }
    return {
        "tonight_sleep_target_direction": "maintain_routine",
        "bedtime_adjustment": "保持规律就寝时间，避免明显压缩睡眠机会。",
        "sleep_priority": "normal",
        "rationale": "当前结构化睡眠证据未触发睡眠不足规则。",
    }
