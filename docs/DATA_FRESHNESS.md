# Data Freshness Diagnostics

The diagnostics compare aggregate dates across fetched Polar files, imported raw
tables, Daily Metrics, Recovery, Confidence, and Local Coach. They never emit raw
payloads or health measurements.

```bash
.venv/bin/python -m src.data_freshness
```

Possible blocker codes distinguish source unavailability from local processing
lag: `source_data_unavailable`, `source_data_not_available_for_today`,
`raw_import_lag`, `daily_metrics_lag`, `recovery_lag`, `confidence_lag`, and
`local_coach_lag`.

As of `2026-07-12`, every available source and local stage is aligned at
`2026-07-08`. The current prospective blocker is therefore Polar source
availability, not an importer or calculation defect.
