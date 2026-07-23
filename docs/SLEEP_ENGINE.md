# Sleep Regularity Engine 2.0.0

## Boundary

`src/sleep_regularity.py` is a deterministic, device-independent service. The
Streamlit page consumes `SleepRegularityResult`; it does not calculate sleep
regularity. `src/sleep_adapters.py` maps Polar projections to
`CanonicalSleepRecord` and reserves the same boundary for HealthKit.

## Algorithm selection

- `sri_timeline`: selected when at least seven valid nights contain usable
  sleep/awake segments and timeline coverage meets the configured threshold.
- `summary_composite`: fallback for valid nightly summaries.
- `insufficient_data`: fewer than seven valid nights; no numeric score.
- `unavailable`: malformed or incomplete input that cannot be calculated.

SRI compares minute-level states 24 hours apart. `unknown` and missing minutes
are excluded from matching, not treated as awake. Summary scoring uses the
last 14 valid nights and three robust components: bedtime 35%, wake time 45%,
and actual sleep duration 20%. Clock values use circular differences, centers,
and MAD; duration uses median and MAD. Initial half-score thresholds are 60,
45, and 60 minutes respectively. These are calibration parameters, not
clinical thresholds.

## Maturity and state

Fewer than 7 valid nights is `collecting`; 7–13 is `provisional`; 14–27 is
`reliable`; 28 or more is `stable`. `map_score_to_status()` is the sole score
to status mapping. Missing data is never converted to zero, and `0 / 100` can
only represent a genuinely calculated irregular score.

Long-term regularity and `LastNightScheduleDeviation` are calculated
separately. The latter excludes the target night from its reference window and
reports signed bedtime, wake-time, and duration deviations.
