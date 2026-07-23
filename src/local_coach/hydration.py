"""Directional hydration and electrolyte guidance without prescriptions."""


LIMIT = "系统未直接测量汗液钠浓度；电解质方向基于训练和出汗情境，不是个体化医学处方。"


def generate_hydration_advice(data, rules):
    load_high = data.stress_load_score is not None and data.stress_load_score >= rules["high_load_score"]
    prior_training = (data.previous_training_duration_minutes or 0) > 60
    if load_high and prior_training:
        status = "consider_electrolytes"
        direction = "高负荷情境下注意持续补水；若出汗明显，可结合饮食情境考虑电解质。"
        rationale = "近期训练与活动负荷较高，但系统没有环境和汗液实测。"
    elif load_high or prior_training:
        status = "increase_fluids"
        direction = "训练前后留意口渴、尿色和出汗情况，方向性增加液体摄入机会。"
        rationale = "训练或活动情境提示补水需求可能增加。"
    elif data.stress_load_score is None:
        status = "monitor_sweat_loss"
        direction = "负荷和环境信息不足，按口渴、出汗和实际训练情况保守调整。"
        rationale = "缺少足够负荷或环境证据，不能给出个体化用量。"
    else:
        status = "normal_hydration"
        direction = "保持日常规律补水，并根据实际出汗情况调整。"
        rationale = "当前负荷未触发增加补水的透明工程规则。"
    return {"status": status, "direction": direction, "rationale": rationale, "measurement_limit": LIMIT}
