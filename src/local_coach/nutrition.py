"""Directional nutrition guidance without exact grams or calorie prescriptions."""


def generate_nutrition_advice(data, rules):
    high_load = data.stress_load_score is not None and data.stress_load_score >= rules["high_load_score"]
    return {
        "protein_direction": "保持稳定、分散到日常餐次的蛋白质来源。",
        "carbohydrate_direction": (
            "高负荷日可方向性增加碳水化合物来源。" if high_load
            else "根据当天实际训练量保持适度碳水化合物来源。"
        ),
        "post_training_meal_direction": "若完成晚间训练，可安排包含碳水和蛋白质来源的恢复餐。",
        "energy_intake_direction": "避免长期能量摄入不足，并结合饥饿感、训练量和目标调整。",
        "rationale": "系统缺少体重、明确目标、总热量、宏量摄入和饮食禁忌，因此只提供方向性建议。",
    }
