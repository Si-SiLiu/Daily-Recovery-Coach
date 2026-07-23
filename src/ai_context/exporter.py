"""Preview and confirmed local file exports; never uploads data."""

import csv
import io
import json
from pathlib import Path

from .builder import build_ai_context
from src.i18n import get_translator


BASE_DIR = Path(__file__).resolve().parents[2]
EXPORT_DIR = BASE_DIR / "exports" / "ai_context"


def flatten(prefix, value, output):
    if isinstance(value, dict):
        for key, child in value.items():
            flatten(f"{prefix}.{key}" if prefix else key, child, output)
    elif isinstance(value, list):
        output[prefix] = json.dumps(value, ensure_ascii=False)
    else:
        output[prefix] = value


def render_json(payload):
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def render_markdown(payload, language=None):
    tr = get_translator(language or payload.get("display_language", "zh-CN"))
    lines = [f"# {tr('ai_context.markdown_title')} — {payload['date']}", "", payload["localized_summary"], "", payload["privacy_notice"], ""]
    for section in (
        "body_summary", "recovery_summary", "sleep_summary", "nutrition_summary",
        "training_summary", "kubios_summary",
    ):
        lines.extend((f"## {section}", "", "```json", json.dumps(payload[section], ensure_ascii=False, indent=2), "```", ""))
    if payload["user_questions"]:
        lines.extend((f"## {tr('ai_context.user_questions')}", "", *(f"- {item}" for item in payload["user_questions"]), ""))
    return "\n".join(lines)


def render_csv(payload):
    flat = {}
    flatten("", payload, flat)
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(flat))
    writer.writeheader()
    writer.writerow(flat)
    return stream.getvalue()


def export_ai_context(connection, analysis_date, range_days=7, questions=None,
                      output_dir=EXPORT_DIR, dry_run=True, confirmed=False, **options):
    payload = build_ai_context(connection, analysis_date, range_days, questions, **options)
    contents = {"json": render_json(payload), "md": render_markdown(payload), "csv": render_csv(payload)}
    if dry_run:
        return {"payload": payload, "contents": contents, "paths": {}, "written": False}
    if not confirmed:
        raise ValueError("AI_CONTEXT_EXPORT_CONFIRMATION_REQUIRED")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for extension, content in contents.items():
        path = output_dir / f"ai_context_{analysis_date}.{extension}"
        path.write_text(content, encoding="utf-8")
        paths[extension] = path
    return {"payload": payload, "contents": contents, "paths": paths, "written": True}
