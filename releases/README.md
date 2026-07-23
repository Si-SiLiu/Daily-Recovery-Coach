# Release Records

This directory stores one formal release snapshot for every application version.
Each snapshot is immutable historical context after acceptance.

- File name format: `VERSION.md` (for example, `0.10.0.md`).
- A release file records only the formal release snapshot.
- `docs/CHANGELOG.md` remains the continuous history of changes.
- `docs/HANDOFF.md` records only the latest phase handoff.
- Release notes may include aggregate counts and dates, but never credentials,
  tokens, raw payloads, or personal health details.
- Pre-1.0 snapshots must state their maturity and compatibility limits.
