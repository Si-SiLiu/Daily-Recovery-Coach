import ast
import json
import re
from pathlib import Path

try:
    from . import update_project_state
except ImportError:
    import update_project_state


BASE_DIR = Path(__file__).resolve().parents[1]
HANDOFF_PATH = BASE_DIR / "docs" / "HANDOFF.md"
AI_COLLABORATION_PATH = BASE_DIR / "docs" / "AI_COLLABORATION.md"

REQUIRED_HANDOFF_SECTIONS = [
    "Goal",
    "Status",
    "Files Changed",
    "Version Changes",
    "Database Migrations",
    "Tests",
    "Current State Generation",
    "System Status",
    "Release Record",
    "Real Data Verification",
    "Documentation Updated",
    "State Synchronization",
    "Known Issues",
    "Prioritized Issues",
    "Quality Gate Result",
    "Architecture Decisions Needed",
    "Manual User Actions Required",
    "Recommended Next Phase",
]

HANDOFF_STATE_KEYS = {
    "App Version",
    "Current Phase",
    "Phase Status",
    "Recovery Engine Version",
    "Baseline Engine Version",
    "Confidence Engine Version",
    "Database Schema Version",
    "Schema Migration Count",
    "Latest Schema Migration",
    "Dashboard Version",
    "Test Total",
    "Test Passed",
    "Test Failed",
    "Test Success",
    "Baseline Record Count",
    "Scored Day Count",
    "Recovery v1 Day Count",
    "Confidence Record Count",
    "Latest Data Date",
}

AUTHORITATIVE_FILES = {
    "Current machine state": BASE_DIR / "project_state.json",
    "Human-readable current state": BASE_DIR / "docs" / "CURRENT_STATE.md",
    "Long-term milestones": BASE_DIR / "docs" / "ROADMAP.md",
    "Architecture boundaries": BASE_DIR / "docs" / "ARCHITECTURE.md",
    "Technical decisions": BASE_DIR / "docs" / "DECISIONS.md",
    "Historical changes": BASE_DIR / "docs" / "CHANGELOG.md",
    "Version source": BASE_DIR / "config" / "versions.json",
    "Quality gate": BASE_DIR / "docs" / "QUALITY_GATE.md",
    "Release records": BASE_DIR / "releases" / "README.md",
    "Sync pipeline": BASE_DIR / "docs" / "SYNC_PIPELINE.md",
    "AI Coach design": BASE_DIR / "docs" / "AI_COACH.md",
    "Cloud provider evaluation": BASE_DIR / "docs" / "CLOUD_PROVIDER_EVALUATION.md",
    "Provider due diligence": BASE_DIR / "docs" / "PROVIDER_DUE_DILIGENCE.md",
    "AI Coach threat model": BASE_DIR / "docs" / "AI_COACH_THREAT_MODEL.md",
    "AI Coach contract versions": BASE_DIR / "config" / "ai_coach_contract.json",
    "AI Coach safety policy": BASE_DIR / "config" / "ai_coach_safety_policy.json",
    "AI Coach evaluation policy": BASE_DIR / "config" / "ai_coach_evaluation.json",
    "AI Coach provider approval": BASE_DIR / "config" / "ai_coach_provider_approval.json",
}

ARCHITECTURE_IMPORT_RULES = {
    BASE_DIR / "src" / "ai_coach_readiness.py": {
        "requests",
        "sqlite3",
        "polar_client",
        "polar_oauth",
        "recovery_score",
        "baseline",
        "recovery_confidence",
        "dashboard",
        "streamlit",
    },
    BASE_DIR / "src" / "ai_coach_context.py": {
        "requests",
        "sqlite3",
        "polar_client",
        "polar_oauth",
        "recovery_score",
        "baseline",
        "recovery_confidence",
        "dashboard",
        "streamlit",
    },
    BASE_DIR / "src" / "ai_coach_approval.py": {
        "requests",
        "sqlite3",
        "polar_client",
        "polar_oauth",
        "recovery_score",
        "baseline",
        "recovery_confidence",
        "dashboard",
        "streamlit",
    },
    BASE_DIR / "src" / "ai_coach_evaluation.py": {
        "requests",
        "sqlite3",
        "polar_client",
        "polar_oauth",
        "recovery_score",
        "baseline",
        "recovery_confidence",
        "dashboard",
        "streamlit",
    },
    BASE_DIR / "src" / "ai_coach_safety.py": {
        "requests",
        "sqlite3",
        "polar_client",
        "polar_oauth",
        "recovery_score",
        "baseline",
        "recovery_confidence",
        "dashboard",
        "streamlit",
    },
    BASE_DIR / "src" / "ai_coach_contract.py": {
        "requests",
        "sqlite3",
        "polar_client",
        "polar_oauth",
        "recovery_score",
        "baseline",
        "recovery_confidence",
        "dashboard",
        "streamlit",
    },
    BASE_DIR / "src" / "dashboard.py": {
        "polar_client",
        "polar_fetch",
        "polar_oauth",
    },
    BASE_DIR / "src" / "dashboard_data.py": {
        "polar_client",
        "polar_fetch",
        "polar_oauth",
    },
    BASE_DIR / "src" / "system_status.py": {
        "polar_client",
        "polar_fetch",
        "polar_oauth",
        "recovery_score",
        "baseline",
    },
    BASE_DIR / "src" / "sync_pipeline.py": {
        "polar_client",
        "polar_fetch",
        "polar_oauth",
        "recovery_score",
        "baseline",
        "dashboard",
    },
    BASE_DIR / "src" / "recovery_score.py": {
        "dashboard",
        "dashboard_data",
        "streamlit",
    },
    BASE_DIR / "src" / "report.py": {
        "polar_client",
        "polar_fetch",
        "polar_oauth",
    },
}

FORBIDDEN_HANDOFF_PATTERNS = (
    re.compile(r"access_token\s*[:=]", re.IGNORECASE),
    re.compile(r"refresh_token\s*[:=]", re.IGNORECASE),
    re.compile(r"client_secret\s*[:=]", re.IGNORECASE),
    re.compile(r"polar_client_secret\s*[:=]", re.IGNORECASE),
)


class CollaborationVerificationError(RuntimeError):
    """Raised when a phase handoff violates the collaboration contract."""


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CollaborationVerificationError(
            f"Unable to read JSON {path}: {exc}"
        ) from exc


def parse_handoff(document_path=HANDOFF_PATH):
    document = Path(document_path).read_text(encoding="utf-8")
    if not document.startswith("# Phase / Version\n"):
        raise CollaborationVerificationError(
            "HANDOFF.md must start with '# Phase / Version'"
        )

    matches = list(re.finditer(r"^## (.+?)\s*$", document, re.MULTILINE))
    headings = [match.group(1) for match in matches]
    if headings != REQUIRED_HANDOFF_SECTIONS:
        raise CollaborationVerificationError(
            "HANDOFF.md headings must exactly match the required order: "
            + ", ".join(REQUIRED_HANDOFF_SECTIONS)
        )

    sections = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(document)
        section = document[start:end].strip()
        if not section:
            raise CollaborationVerificationError(
                f"HANDOFF.md section is empty: {match.group(1)}"
            )
        visible_section = re.sub(r"<!--.*?-->", "", section, flags=re.DOTALL)
        if re.search(r"<[^>]+>", visible_section):
            raise CollaborationVerificationError(
                f"HANDOFF.md contains a template placeholder in: {match.group(1)}"
            )
        sections[match.group(1)] = section
    return document, sections


def parse_labeled_values(document):
    values = {}
    for label, state_key in update_project_state.CURRENT_STATE_KEYS.items():
        if label not in HANDOFF_STATE_KEYS:
            continue
        match = re.search(
            rf"^- {re.escape(label)}:\s*(.+?)\s*$",
            document,
            re.MULTILINE,
        )
        if not match:
            raise CollaborationVerificationError(
                f"HANDOFF.md is missing state value: {label}"
            )
        raw_value = match.group(1).strip()
        if state_key in update_project_state.INTEGER_STATE_FIELDS:
            try:
                values[state_key] = int(raw_value)
            except ValueError as exc:
                raise CollaborationVerificationError(
                    f"HANDOFF.md value for {label} must be an integer"
                ) from exc
        elif state_key in update_project_state.BOOLEAN_STATE_FIELDS:
            if raw_value not in {"true", "false"}:
                raise CollaborationVerificationError(
                    f"HANDOFF.md value for {label} must be true or false"
                )
            values[state_key] = raw_value == "true"
        elif state_key == "latest_data_date" and raw_value == "none":
            values[state_key] = None
        else:
            values[state_key] = raw_value
    return values


def validate_handoff(state, document_path=HANDOFF_PATH):
    document, sections = parse_handoff(document_path)
    handoff_state = parse_labeled_values(document)
    differences = {
        key: {"project_state": state.get(key), "handoff": value}
        for key, value in handoff_state.items()
        if state.get(key) != value
    }
    if differences:
        details = "; ".join(
            f"{key}: project_state={values['project_state']!r}, "
            f"handoff={values['handoff']!r}"
            for key, values in differences.items()
        )
        raise CollaborationVerificationError(f"Handoff state mismatch: {details}")

    if state["next_goal"] not in sections["Recommended Next Phase"]:
        raise CollaborationVerificationError(
            "Recommended Next Phase does not match project_state.json next_goal"
        )

    prioritized = sections["Prioritized Issues"]
    for issue in state["prioritized_issues"]:
        if issue["priority"] not in prioritized or issue["description"] not in prioritized:
            raise CollaborationVerificationError(
                "HANDOFF.md Prioritized Issues does not mirror project_state.json"
            )

    for pattern in FORBIDDEN_HANDOFF_PATTERNS:
        if pattern.search(document):
            raise CollaborationVerificationError(
                "HANDOFF.md contains a forbidden sensitive assignment"
            )
    return sections


def imported_modules(source_path):
    tree = ast.parse(Path(source_path).read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def display_path(path):
    path = Path(path)
    try:
        return str(path.relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def validate_architecture_boundaries():
    violations = []
    for source_path, forbidden_names in ARCHITECTURE_IMPORT_RULES.items():
        modules = imported_modules(source_path)
        for module in modules:
            matched = sorted(forbidden_names & set(module.split(".")))
            if matched:
                violations.append(
                    f"{display_path(source_path)} imports {module} "
                    f"(forbidden: {', '.join(matched)})"
                )
    if violations:
        raise CollaborationVerificationError(
            "Architecture boundary violations: " + "; ".join(violations)
        )


def validate_authority_map():
    document = AI_COLLABORATION_PATH.read_text(encoding="utf-8")
    missing = []
    for label, path in AUTHORITATIVE_FILES.items():
        if not path.exists():
            missing.append(str(path.relative_to(BASE_DIR)))
        if label not in document:
            missing.append(f"AI_COLLABORATION label: {label}")
    if missing:
        raise CollaborationVerificationError(
            "Authority map is incomplete: " + ", ".join(missing)
        )


def validate_machine_state(state):
    versions = update_project_state.load_versions()
    expected = {
        **versions,
        **update_project_state.collect_database_state(),
        "test_total": update_project_state.discover_test_total(),
        "test_failed": 0,
        "test_success": True,
        "generated_by": update_project_state.GENERATED_BY,
    }
    expected["test_passed"] = expected["test_total"]

    differences = {
        key: {"project_state": state.get(key), "actual": value}
        for key, value in expected.items()
        if state.get(key) != value
    }
    if differences:
        details = "; ".join(
            f"{key}: project_state={values['project_state']!r}, "
            f"actual={values['actual']!r}"
            for key, values in differences.items()
        )
        raise CollaborationVerificationError(f"Machine state is stale: {details}")


def verify_all(state_path=update_project_state.STATE_PATH):
    state = load_json(state_path)
    validate_machine_state(state)
    update_project_state.validate_current_state(state)
    validate_handoff(state)
    validate_authority_map()
    validate_architecture_boundaries()
    return state


def main():
    try:
        state = verify_all()
    except (
        CollaborationVerificationError,
        update_project_state.ProjectStateError,
    ) as exc:
        raise SystemExit(f"AI collaboration verification failed: {exc}")

    print("AI collaboration verification: passed")
    print(f"Phase: {state['current_phase']} ({state['phase_status']})")
    print(
        "Tests: "
        f"total={state['test_total']} "
        f"passed={state['test_passed']} "
        f"failed={state['test_failed']}"
    )
    print("Architecture boundaries: passed")
    print("Handoff contract: passed")


if __name__ == "__main__":
    main()
