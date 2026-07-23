import json


RAW_VALUE_FIELDS = (
    "mean_rr_ms","mean_hr_bpm","rmssd_ms","sdnn_ms","poincare_sd1_ms","poincare_sd2_ms",
    "stress_index","respiratory_rate_bpm","lf_power_ms2","hf_power_ms2","lf_power_nu","hf_power_nu",
    "lf_hf_ratio","readiness_percent","pns_index","sns_index","physiological_age","measurement_quality",
    "mood_code","recovery_status","artefact_correction_percent","measurement_duration_seconds",
)
NORMALIZED_VALUE_FIELDS = (
    "rmssd_ms","mean_hr_bpm","readiness_percent","pns_index","sns_index","sdnn_ms",
    "respiratory_rate_bpm","stress_index","physiological_age","measurement_quality",
)
DERIVED_FIELDS = (
    "rmssd_vs_baseline_percent","mean_hr_vs_baseline_percent","sdnn_vs_baseline_percent",
    "readiness_vs_baseline_percent","pns_vs_baseline_delta","sns_vs_baseline_delta",
    "respiratory_rate_vs_baseline_percent","stress_index_vs_baseline_percent","rmssd_7d_trend",
    "mean_hr_7d_trend","readiness_7d_trend","pns_7d_trend","sns_7d_trend",
    "consecutive_rmssd_below_baseline_days","consecutive_mean_hr_above_baseline_days",
    "consecutive_readiness_decline_days","data_quality_status","source_reliability_status",
    "derivation_version",
)


def insert_raw(connection, measurement):
    row = measurement.to_dict() if hasattr(measurement, "to_dict") else dict(measurement)
    columns = ("date","measurement_time","measurement_group_id",*RAW_VALUE_FIELDS,"source_type",
               "source_file_sha256","import_method","parser_version","reviewed","ocr_confidence",
               "selected_as_primary","selection_reason","source_priority","raw_json")
    values = [row.get(name) for name in columns]
    values[columns.index("reviewed")] = int(bool(row.get("reviewed")))
    values[columns.index("selected_as_primary")] = int(bool(row.get("selected_as_primary")))
    values[columns.index("raw_json")] = json.dumps(row.get("raw_json") or {}, ensure_ascii=False, sort_keys=True)
    existing = connection.execute(
        "SELECT id FROM kubios_hrv_measurements_raw WHERE date=? AND measurement_time IS ? AND source_type=? AND source_file_sha256 IS ? AND import_method=?",
        (row.get("date"),row.get("measurement_time"),row.get("source_type"),row.get("source_file_sha256"),row.get("import_method")),
    ).fetchone()
    if existing:
        mutable = [name for name in columns if name not in {"date","measurement_time","source_type","source_file_sha256","import_method"}]
        connection.execute(
            f"UPDATE kubios_hrv_measurements_raw SET {','.join(name+'=?' for name in mutable)},updated_at=CURRENT_TIMESTAMP WHERE id=?",
            [values[columns.index(name)] for name in mutable] + [existing[0]],
        )
        return existing[0]
    placeholders = ",".join("?" for _ in columns)
    cursor = connection.execute(
        f"INSERT INTO kubios_hrv_measurements_raw ({','.join(columns)}) VALUES ({placeholders}) "
        "ON CONFLICT(date,measurement_time,source_type,source_file_sha256,import_method) DO UPDATE SET "
        + ",".join(f"{name}=excluded.{name}" for name in columns if name not in {"date","measurement_time","source_type","source_file_sha256","import_method"})
        + ",updated_at=CURRENT_TIMESTAMP",
        values,
    )
    if cursor.lastrowid:
        return cursor.lastrowid
    found = connection.execute(
        "SELECT id FROM kubios_hrv_measurements_raw WHERE date=? AND measurement_time IS ? AND source_type=? AND source_file_sha256 IS ? AND import_method=?",
        (row.get("date"),row.get("measurement_time"),row.get("source_type"),row.get("source_file_sha256"),row.get("import_method")),
    ).fetchone()
    return found[0]


def mark_primary(connection, date_value, raw_id, reason):
    connection.execute("UPDATE kubios_hrv_measurements_raw SET selected_as_primary=0,selection_reason=NULL WHERE date=?", (date_value,))
    connection.execute("UPDATE kubios_hrv_measurements_raw SET selected_as_primary=1,selection_reason=? WHERE id=?", (reason,raw_id))


def upsert_normalized(connection, normalized):
    row = normalized.to_dict() if hasattr(normalized, "to_dict") else dict(normalized)
    columns = ("date","measurement_time","measurement_group_id","source_raw_table","source_raw_id",
               "source_type","selected_as_primary","selection_reason","source_priority",*NORMALIZED_VALUE_FIELDS,
               "core_data_completeness","normalization_version")
    values = [int(bool(row.get(name))) if name == "selected_as_primary" else row.get(name) for name in columns]
    existing = connection.execute(
        "SELECT id FROM kubios_hrv_normalized WHERE date=? AND measurement_time IS ? AND source_type=? AND normalization_version=?",
        (row.get("date"),row.get("measurement_time"),row.get("source_type"),row.get("normalization_version")),
    ).fetchone()
    if existing:
        mutable = [name for name in columns if name not in {"date","measurement_time","source_type","normalization_version"}]
        connection.execute(
            f"UPDATE kubios_hrv_normalized SET {','.join(name+'=?' for name in mutable)},updated_at=CURRENT_TIMESTAMP WHERE id=?",
            [values[columns.index(name)] for name in mutable] + [existing[0]],
        )
        return existing[0]
    cursor = connection.execute(
        f"INSERT INTO kubios_hrv_normalized ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)}) "
        "ON CONFLICT(date,measurement_time,source_type,normalization_version) DO UPDATE SET "
        + ",".join(f"{name}=excluded.{name}" for name in columns if name not in {"date","measurement_time","source_type","normalization_version"})
        + ",updated_at=CURRENT_TIMESTAMP",
        values,
    )
    return cursor.lastrowid


def upsert_derived(connection, row):
    columns = ("date", *DERIVED_FIELDS)
    connection.execute(
        f"INSERT INTO kubios_hrv_derived ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)}) "
        "ON CONFLICT(date,derivation_version) DO UPDATE SET "
        + ",".join(f"{name}=excluded.{name}" for name in DERIVED_FIELDS if name != "derivation_version")
        + ",updated_at=CURRENT_TIMESTAMP",
        [row.get(name) for name in columns],
    )
