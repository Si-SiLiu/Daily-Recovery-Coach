from datetime import datetime


def _now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def safe_field_summary(parse_result):
    # Intentionally records field names only, never complete recognized text.
    return "fields=" + ",".join(sorted(parse_result.fields))


def create_audit(connection, stored, ocr_result, parse_result, status="review_required", error_code=None, safe_error_message=None):
    existing = connection.execute(
        "SELECT id FROM kubios_screenshot_imports WHERE file_sha256 = ?",
        (stored.sha256,),
    ).fetchone()
    if existing:
        connection.execute(
            """
            UPDATE kubios_screenshot_imports
            SET import_status = ?, ocr_engine = ?, ocr_engine_version = ?,
                parser_version = ?, detected_date = ?,
                detected_measurement_time = ?, ocr_text_summary = ?,
                overall_ocr_confidence = ?, required_fields_found = ?,
                review_required = 1, error_code = ?, safe_error_message = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, ocr_result.engine, ocr_result.engine_version,
             parse_result.parser_version,
             parse_result.fields.get("date").value if "date" in parse_result.fields else None,
             parse_result.fields.get("measurement_time").value if "measurement_time" in parse_result.fields else None,
             safe_field_summary(parse_result), parse_result.overall_confidence,
             int(not parse_result.missing_required_fields), error_code,
             safe_error_message, existing[0]),
        )
        connection.commit()
        return existing[0]
    cursor = connection.execute(
        """
        INSERT INTO kubios_screenshot_imports (
            file_sha256, original_relative_path, processed_relative_path,
            import_status, ocr_engine, ocr_engine_version, parser_version,
            detected_date, detected_measurement_time, ocr_text_summary,
            overall_ocr_confidence, required_fields_found, review_required,
            reviewed, error_code, safe_error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?)
        """,
        (
            stored.sha256, stored.original_relative_path, stored.processed_relative_path,
            status, ocr_result.engine, ocr_result.engine_version,
            parse_result.parser_version,
            parse_result.fields.get("date").value if "date" in parse_result.fields else None,
            parse_result.fields.get("measurement_time").value if "measurement_time" in parse_result.fields else None,
            safe_field_summary(parse_result), parse_result.overall_confidence,
            int(not parse_result.missing_required_fields), error_code, safe_error_message,
        ),
    )
    connection.commit()
    return cursor.lastrowid


def create_failure_audit(connection, stored, engine, engine_version, parser_version, error_code, safe_message, status="parsing_failed"):
    existing = connection.execute(
        "SELECT id FROM kubios_screenshot_imports WHERE file_sha256 = ?", (stored.sha256,)
    ).fetchone()
    if existing:
        return existing[0]
    cursor = connection.execute(
        """
        INSERT INTO kubios_screenshot_imports (
            file_sha256, original_relative_path, processed_relative_path,
            import_status, ocr_engine, ocr_engine_version, parser_version,
            ocr_text_summary, required_fields_found, review_required, reviewed,
            error_code, safe_error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, '', 0, 1, 0, ?, ?)
        """,
        (stored.sha256, stored.original_relative_path, stored.processed_relative_path,
         status, engine, engine_version, parser_version, error_code, safe_message),
    )
    connection.commit()
    return cursor.lastrowid


def mark_reviewed(connection, audit_id, status, imported_record_id=None, downstream_updated=False, error_code=None, safe_error_message=None):
    connection.execute(
        """
        UPDATE kubios_screenshot_imports
        SET import_status = ?, reviewed = 1, reviewed_at = ?,
            imported_record_id = COALESCE(?, imported_record_id),
            downstream_updated = ?, error_code = ?, safe_error_message = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, _now(), imported_record_id, int(downstream_updated),
         error_code, safe_error_message, audit_id),
    )
    connection.commit()


def mark_downstream_updated(connection, audit_id, success):
    connection.execute(
        "UPDATE kubios_screenshot_imports SET downstream_updated = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (int(success), audit_id),
    )
    connection.commit()


def list_recent(connection, limit=20):
    try:
        rows = connection.execute(
            """
            SELECT id, file_sha256, import_status, ocr_engine,
                   overall_ocr_confidence, review_required, reviewed,
                   downstream_updated, detected_date, detected_measurement_time,
                   measurement_group_id, created_at
            FROM kubios_screenshot_imports ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    except Exception:
        return []
    return [dict(row) for row in rows]
