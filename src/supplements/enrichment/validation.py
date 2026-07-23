"""Candidate safety rules."""


def candidate_can_be_authoritative(candidate: dict, user_confirmed=False) -> bool:
    return bool(
        user_confirmed
        and candidate.get("source_reference")
        and candidate.get("source_type")
        and candidate.get("product_name")
    )
