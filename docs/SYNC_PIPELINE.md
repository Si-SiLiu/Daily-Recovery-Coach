# One-Click Sync Pipeline

## Kubios normalization and derivation

After legacy daily metrics are rebuilt, the metrics stage rebuilds reviewed
Kubios normalized records and then derived records. Dry-run calculates counts
without writes. The builders are local, idempotent, independently runnable for
all dates or selected dates, and do not recalculate Recovery Score formulas.

## Kubios Screenshot Selective Step

`python -m src.sync_pipeline --only kubios-screenshot --dry-run` reports
confirmed and review-pending screenshot audits without writing. The non-dry
step reconciles only already reviewed screenshot records into daily metrics;
it never runs OCR, confirms a result, or calls Cloud AI. The App's “import and
update” choice runs metrics, baseline, recovery, confidence, Local Coach,
report, and governance state after the reviewed write.

Personal Logging is user-driven and is not fetched or uploaded by this pipeline.
AI Context export always requires a separate Preview and confirmation.

## Purpose

The pipeline turns the existing local commands into one resumable operation. It
orchestrates existing modules and does not redefine OAuth, API requests, imports,
daily metrics, baselines, recovery formulas, reports, or Dashboard analysis.

## Command

```bash
.venv/bin/python src/sync_pipeline.py
```

An existing Polar authorization is a prerequisite. If the local token is absent
or cannot be refreshed, the pipeline stops with a safe instruction to complete
the existing OAuth flow; it does not implement a second OAuth path.

## Steps

1. `token`: confirm authorization, detect expiry, and ask the existing client to
   refresh when required.
2. `fetch`: fetch profile, daily activity, training, sleep, Nightly Recharge,
   continuous heart rate, and cardio load through existing Polar client methods.
3. `import`: import Polar raw files into SQLite and import every CSV under
   `data/imports/` through the existing Kubios importer. A missing directory or
   no CSV is a normal skip.
4. `metrics`: rebuild daily recovery metrics through the existing module.
5. `baseline`: run the existing Baseline Engine unchanged.
6. `recovery`: build and upsert scores using the existing Recovery Engine
   functions without duplicating or changing formulas.
7. `confidence`: rebuild the independent persisted Confidence sidecar.
8. `local-coach`: generate schema-validated local deterministic advice.
9. `report`: generate the latest Markdown daily report including Local Coach.
9. `governance`: regenerate `project_state.json` and `CURRENT_STATE.md`, then
   replace only the marked operational-sync blocks in CHANGELOG and HANDOFF.
9. Dashboard: the next Streamlit refresh reads the updated SQLite and last-sync
   summary; the pipeline does not launch or mutate Dashboard analysis.

## Module Boundaries

| Module | Responsibility |
| --- | --- |
| `pipeline/token.py` | Token availability and refresh orchestration |
| `pipeline/fetch.py` | Dataset fetch orchestration |
| `pipeline/importer.py` | Polar and optional Kubios import |
| `pipeline/metrics.py` | Daily Metrics invocation |
| `pipeline/baseline.py` | Baseline invocation |
| `pipeline/recovery.py` | Existing Recovery build/upsert invocation |
| `pipeline/confidence.py` | Independent Confidence rebuild invocation |
| `pipeline/local_coach.py` | Local deterministic advice invocation |
| `pipeline/report.py` | Markdown report invocation |
| `pipeline/governance.py` | State and marked documentation synchronization |
| `pipeline/logger.py` | Safe lifecycle logging |
| `pipeline/history.py` | Operational history and resume state |

`src/sync_pipeline.py` owns only ordering, selection, resume, error handling, and
the final summary.

## Dry Run

```bash
.venv/bin/python src/sync_pipeline.py --dry-run
```

Dry Run checks prerequisites and planned steps. It does not load token contents,
call Polar, write `recovery.db`, create `sync_history.db`, generate reports, or
update governance files. Writing the lifecycle log is allowed.

## Selective Sync

```bash
.venv/bin/python src/sync_pipeline.py --only fetch
.venv/bin/python src/sync_pipeline.py --only report
.venv/bin/python src/sync_pipeline.py --only local-coach
.venv/bin/python -m src.sync_pipeline --if-new-data
.venv/bin/python src/sync_pipeline.py --only recovery
```

`fetch` obtains its token prerequisite automatically. Other selected steps use
the current local inputs and do not run unrelated steps.

`--if-new-data` is an opt-in full-pipeline mode. After Token, Fetch, and Import,
it skips Metrics through Report only when tracked Polar source files are exactly
unchanged, no raw row was added, and no Kubios CSV is pending. Governance still
runs. Missing snapshots, changed bytes, new rows, Kubios input, and uncertainty
all fail open to the normal complete rebuild. It cannot be combined with
`--only` or `--resume`; dry-run continues validating every step.

## Resume

```bash
.venv/bin/python src/sync_pipeline.py --resume
```

Every successful step and the failed pipeline summary are recorded. Resume finds
the latest unfinished `run_id`, skips its completed steps, and continues at the
failed step. `--only` and `--resume` cannot be combined.

## Logging

Lifecycle events are appended to `logs/sync.log` with start, finish, duration,
success, step, run ID, and safe exception type. Tokens, response payloads, raw
health data, and credential values are never logged.

## Sync History

Operational history uses the independent `data/sync_history.db`; the recovery
database schema is unchanged. `sync_history` contains:

- `id`, `run_id`, `start_time`, `finish_time`, `duration`
- `success`, `step`, `message`
- aggregate imported, baseline, recovery, Confidence, Local Coach, and report counts

The Dashboard reads only the latest pipeline summary: Last Sync, Duration,
Success, and Records Imported.

## Failure and Safety

- A step failure stops later steps and records a resumable checkpoint.
- Core endpoints (profile, activity, training, sleep, and Nightly Recharge) are
  required; an HTTP failure stops the fetch step with `FETCH_REQUIRED_ENDPOINT_FAILED`.
- Capability endpoints (Continuous HR and Cardio Load) may be unavailable; HTTP
  failures become explicit endpoint warnings without hiding the successful core sync.
- The final summary and Dashboard expose the warning count.
- Public failures use allowlisted codes and safe instructions, never response bodies.
- Final history-write failures become `PIPELINE_FINALIZATION_FAILED`; governance
  may already be synchronized, so the operator should correct storage and retry.
- Failure logs store only the exception class, not external response bodies.
- Imports and derived engines retain their existing idempotency behavior.
- No Recovery or Baseline formula is defined in the pipeline package.
- No AI Coach or new external API is introduced.
- Live sync is a user-authorized operation because it reads local authorization,
  calls Polar, and writes local data.

## Scheduler and resolution order

The full order is Token → Fetch → Import → Manual Summary → Daily Metrics →
Field Resolution → Baseline → Recovery → Confidence → Local Coach → Report →
Governance. `--only manual-summary` and `--only resolution` are supported, as
are dry-run and resume.

Manual Summary rebuilds local nutrition/training summaries and reads counts; it
does not feed subjective health values into deterministic engines. Resolution
persists provenance after metrics but before Report. Selective runs are marked
`completed_selective:<step>` and do not count as the day's complete sync.

`trigger_type` is `manual`, `scheduled`, or `catch_up`. All trigger paths share
the same kernel-backed lock. Scheduler and catch-up adapters never copy Fetch,
Import, scoring, or reporting logic and never call Cloud AI.
