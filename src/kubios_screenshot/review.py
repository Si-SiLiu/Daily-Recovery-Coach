from .confidence import confidence_band


def build_review(parse_result, config=None):
    fields = {
        name: {
            "value": field.value,
            "confidence": field.confidence,
            "confidence_band": confidence_band(field.confidence, config),
            "unit": field.unit,
            "candidates": list(field.candidates),
            "candidates_consistent": field.candidates_consistent,
        }
        for name, field in parse_result.fields.items()
    }
    return {
        "fields": fields,
        "missing_required_fields": list(parse_result.missing_required_fields),
        "warnings": list(parse_result.warnings),
        "overall_confidence": parse_result.overall_confidence,
        "overall_confidence_band": confidence_band(parse_result.overall_confidence, config),
        "review_required": True,
        "user_confirmed": False,
        "parser_version": parse_result.parser_version,
    }
