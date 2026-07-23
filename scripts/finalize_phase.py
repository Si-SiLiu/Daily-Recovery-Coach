try:
    from . import update_project_state, verify_ai_collaboration
except ImportError:
    import update_project_state
    import verify_ai_collaboration


def finalize_phase():
    """Refresh measured state, run all tests, and verify the phase handoff."""
    state = update_project_state.update_project_state()
    verify_ai_collaboration.verify_all()
    return state


def main():
    try:
        state = finalize_phase()
    except (
        update_project_state.ProjectStateError,
        verify_ai_collaboration.CollaborationVerificationError,
    ) as exc:
        raise SystemExit(f"Phase finalization failed: {exc}")

    print("Phase finalization: passed")
    print(f"Phase: {state['current_phase']}")
    print(f"Project state: {update_project_state.STATE_PATH}")
    print(f"Handoff: {verify_ai_collaboration.HANDOFF_PATH}")


if __name__ == "__main__":
    main()
