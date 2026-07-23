# Kubios HRV Data Model 1.0

## Purpose

The model stores reviewed Kubios measurements without changing Recovery Engine,
Confidence Engine, or Local Coach formulas. It is local-only and preserves every
source record for audit and conflict review.

## Three Layers

1. `kubios_hrv_measurements_raw` stores source values, provenance, review state,
   source priority, selection reason, and nullable supported fields.
2. `kubios_hrv_normalized` stores one reviewed primary projection per date and
   normalization version. Missing input remains `NULL`.
3. `kubios_hrv_derived` stores 28-day baseline comparisons, 7-day linear trends,
   consecutive-day counters, and explicit data/source quality statuses.

The compatibility table `kubios_morning_hrv_raw` remains in place so existing
daily metrics and formulas continue to work unchanged.

## Sources and Selection

Configured priority is CSV, reviewed screenshot OCR, then reviewed manual input.
Unreviewed input is never selected. A user may explicitly choose a primary
record; otherwise priority, latest measurement time, then stable row ID resolve
ties. Raw rows are retained when another source wins.

## Complementary Screenshots

Two screenshots may be grouped only after explicit confirmation that they came
from the same measurement. Detected dates must not conflict and known times must
be within 15 minutes. Each screenshot is still reviewed and imported separately;
normalization merges only non-null fields from a confirmed group. No date or
value is guessed.

## Derivation Rules

- Baseline window: prior 28 calendar days.
- Minimum baseline history: seven valid prior values per metric.
- Relative metrics remain `NULL` when value, baseline, or sufficient history is
  absent.
- Seven-day trends are deterministic least-squares slopes over available points.
- PNS and SNS are displayed as neutral indices, not diagnoses.

## Safety Boundary

No cloud calls exist in this package. AI Context includes the allowlisted core
projection by default. Raw advanced metrics require two explicit confirmations.
OCR text, images, paths, raw JSON, secrets, and unrestricted payloads are never
exported. This model is not a medical device and does not provide diagnosis.

## Commands

```bash
.venv/bin/python -m src.kubios_metrics.normalizer --dry-run --all
.venv/bin/python -m src.kubios_metrics.derived --dry-run --all
```

Remove `--dry-run` only after reviewed source data exists.
