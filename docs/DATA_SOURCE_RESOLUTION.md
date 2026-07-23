# Data Source Resolution

Data Resolution 1.1.0 centralizes canonical-field priority in
`config/data_source_priority.json` and `src/data_resolution/`. Dashboard pages,
reports, and AI Context consume resolved fields instead of independent priority
branches.

Every result contains `field_name`, `value`, `value_source`,
`source_record_id`, `is_fallback`, `is_manual_override`, `resolution_reason`,
and `resolved_at`. Persisted rows also carry `resolution_version`. Raw Polar and
Kubios rows are never overwritten.

## Canonical policies

- Confirmed inline activity correction, then Polar, then unconfirmed manual
  fallback, then missing—for the specific corrected field.
- Editable sleep field: manual correction, then Polar, then missing.
- Manual-only legacy subjective fields remain available to old records but are
  not collected in the current pages.
- Morning measurement time/RMSSD/heart rate: manual correction, then Kubios.
- Polar nightly HRV/resting HR/respiration remain separate sleep semantics.

There is no global `Polar > Kubios > Manual` rule. Morning and nightly
measurements retain different time windows and meanings.

## Pipeline and persistence

The pipeline runs Manual Summary before Daily Metrics and Field Resolution after
Daily Metrics. `resolved_daily_fields` is an auditable, idempotently rebuilt
cache. Page saves do not modify raw source tables and do not automatically
recalculate Recovery, Baseline, Confidence, or Local Coach results.

```bash
.venv/bin/python -m src.data_resolution.resolver --all --dry-run
.venv/bin/python -m src.sync_pipeline --only resolution
```

Migration 0.9.0 is ledgered by SHA-256 fingerprint, backed up before application,
and verified by SQLite integrity check.
