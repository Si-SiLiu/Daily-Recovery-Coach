# Local Coach Prospective Evaluation

## Purpose

This protocol collects genuine daily Local Coach outputs after `2026-07-12`.
It does not backfill, invent, or relabel historical records. The objective is an
engineering evaluation of fresh deterministic outputs, not clinical validation.

## Eligibility

A unique date is eligible only when:

- the recommendation date is on or after the protocol start;
- the date is not in the future at evaluation time;
- the stored record was generated on that date or within the configured one-day delay;
- the record passes the output Schema and deterministic regeneration check;
- the required safety notice and no-cloud marker are present.

The target is 14 unique eligible days. A late backfill remains visible as a
protocol failure and is not counted as eligible.

## Commands

```bash
.venv/bin/python -m src.local_coach.prospective
.venv/bin/python -m src.local_coach.prospective --require-pass
```

The first command reports collection progress without failing while records are
still accumulating. `--require-pass` is reserved for the final 14-day gate.
Both commands are read-only and return aggregate counts only.

Daily operational status is available with:

```bash
.venv/bin/python -m src.local_coach.collection
.venv/bin/python -m src.local_coach.collection --require-today
```

The default command is a non-failing monitor. `--require-today` returns a
non-zero exit status until today's timely record exists, which is suitable for a
future user-approved scheduler or external monitor.

## Current state

As of `2026-07-12`, progress is `0/14`. Existing records predate the protocol and
are intentionally excluded. Normal daily One-Click Sync executions will create
eligible records when fresh source data is available.
