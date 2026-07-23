"""Deterministic training-volume helpers."""


VOLUME_NOTICE = "不同动作的绝对训练容量不可简单等同；体重和时间型动作不强制计算重量容量。"


def set_volume(record):
    weight, reps = record.get("weight_kg"), record.get("reps")
    return None if weight is None or reps is None else round(weight * reps, 2)


def session_rpe_load(duration_minutes, session_rpe):
    if duration_minutes is None or session_rpe is None:
        return None
    return round(duration_minutes * session_rpe, 2)
