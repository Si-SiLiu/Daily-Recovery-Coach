# Manual Health Logging

Manual Logging Engine 1.1.0 uses inline editing for activity, sleep, and morning
recovery. Exercise and Sleep show historical records; the former separate
manual supplement panels and subjective Recovery panel are removed.

## Activity

`manual_activity_sessions` stores only user-entered or corrected fields. A
Polar/manual pair is merged only when its link is confirmed. Any field changed
in the inline table is a deliberate correction and outranks that Polar field;
unedited fields continue to use Polar. The Polar raw row and source record remain
unchanged and traceable. Unconfirmed rows never merge or double-count.

## Sleep

`manual_sleep_logs` supports corrections for sleep/wake time, total and actual
duration, deep and REM duration, average/minimum sleep heart rate, nightly HRV,
and respiration rate. A correction is labelled manual and the Polar source
remains intact. Missing values stay NULL until supplied. The page includes a
read-only history across available Polar and manual dates.

## Recovery

The Recovery UI stores only measurement time, post-waking RMSSD, and post-waking
resting heart rate. Legacy subjective columns remain in SQLite for
non-destructive compatibility but are no longer displayed or collected. Inline
corrections do not overwrite Kubios raw rows. Existing deterministic score
semantics are not recomputed by a page save.

## Validation and privacy

All writes use parameterized local SQLite operations. Time, duration, heart-rate,
HRV, respiration, and cross-field ranges fail closed. Notes stay excluded from
AI Context by default. Dashboard editors open the already-migrated database with
migrations disabled; schema changes remain a separate maintenance action.
