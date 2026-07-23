"""Privacy and user-question safety checks for local export."""

import re


SENSITIVE_RE = re.compile(
    r"(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b(?:sk-|token|secret|password)\w*\b)",
    re.IGNORECASE,
)


def validate_questions(questions):
    cleaned = []
    for question in questions or []:
        text = str(question).strip()
        if not text:
            continue
        if len(text) > 1000 or SENSITIVE_RE.search(text):
            raise ValueError("AI_CONTEXT_SENSITIVE_QUESTION")
        cleaned.append(text)
    return cleaned


def require_free_text_confirmation(include_free_text, first_confirmation, second_confirmation):
    if include_free_text and not (first_confirmation and second_confirmation):
        raise ValueError("AI_CONTEXT_FREE_TEXT_CONFIRMATION_REQUIRED")
    return bool(include_free_text)
