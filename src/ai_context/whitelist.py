"""Explicit allow/deny policy for manual AI Context exports."""

ALLOWED_TOP_LEVEL = {
    "schema_version", "export_generated_at", "date", "range_days",
    "data_freshness", "body_summary", "recovery_summary", "sleep_summary",
    "nutrition_summary", "training_summary", "local_coach_summary",
    "trend_summary", "data_limitations", "user_questions", "privacy_notice",
    "display_language", "localized_summary",
    "kubios_summary",
}
FORBIDDEN_TERMS = {
    "name", "email", "polar_user_id", "access_token", "refresh_token",
    "client_secret", "token", "secret", "device_id", "serial_number",
    "raw_json", "raw_payload", "rr_data", "heart_rate_series",
    "database_path", "explanation_json", "notes",
}


def assert_allowlisted(payload):
    unknown = set(payload) - ALLOWED_TOP_LEVEL
    if unknown:
        raise ValueError("AI_CONTEXT_UNKNOWN_TOP_LEVEL")

    def walk(value, path=()):
        if isinstance(value, dict):
            for key, child in value.items():
                lowered = key.lower()
                supplement_catalog_name = lowered == "name" and "supplements" in path
                if ((lowered in FORBIDDEN_TERMS and not supplement_catalog_name)
                        or "token" in lowered or "secret" in lowered):
                    raise ValueError("AI_CONTEXT_FORBIDDEN_FIELD")
                walk(child, (*path, lowered))
        elif isinstance(value, list):
            for child in value:
                walk(child, path)
        elif isinstance(value, str) and value.startswith("/Users/"):
            raise ValueError("AI_CONTEXT_ABSOLUTE_PATH_FORBIDDEN")
    walk(payload)
    return payload
