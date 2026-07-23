# Recovery Confidence and Data Completeness

## Kubios Data Model 1.0 boundary

Kubios `measurement_quality` and model completeness are stored and displayed but
do not change Confidence Engine 1.0.0. Adding either to Confidence would be a
formula change and therefore requires a separate ADR and version upgrade.

> Implementation status: complete.
> Current version: `1.0.0` from the unified version source.
> Recovery Engine v1.0 remains unchanged.

## Purpose

Recovery Score answers: “What is the current recovery recommendation?”

Recovery Confidence answers: “How much supporting personal data is available
for that recommendation?”

Data Completeness answers: “Which expected signal groups are present today?”

Baseline Maturity answers: “How much usable personal history supports those
comparisons?”

These values are decision-support metadata. They are not medical certainty,
probability of illness, or a replacement for subjective symptoms.

## Non-goals

- Do not change `recovery_score`.
- Do not change activity or training load scores.
- Do not change recommendation thresholds.
- Do not reinterpret missing data as poor recovery.
- Do not require Kubios when equivalent Polar signals are available.
- Do not let AI calculate confidence.
- Do not infer data freshness that the current schema cannot prove.
- Do not implement a database migration during the design phase.

## Design principles

1. Confidence is deterministic and replayable.
2. Confidence is stored separately from Recovery Score.
3. Null and zero have different meanings.
4. Equivalent Polar and Kubios signals form alternative groups.
5. Missing data lowers confidence, not recovery.
6. More historical days increase baseline maturity.
7. Every output records a confidence version.
8. Group-level details remain explainable.
9. Partial data produces a partial result rather than an exception.
10. AI Coach may explain the result but cannot overwrite it.

## Input contract

The engine will read `daily_recovery_metrics` and `baseline_metrics` for the
same target date. It will not read raw JSON, token files, Polar APIs, or
Dashboard state.

Presence means a valid non-null value. Numeric zero is present when zero is a
valid domain value. Negative, non-finite, or unparseable values are absent.

## Signal groups

| Group | Weight | Current fields | Completion rule |
| --- | ---: | --- | --- |
| Activity load | 15 | `steps`, `active_calories` | Mean presence of both fields |
| Training load | 15 | `training_count`, `training_duration`, `training_calories` | No-training day is complete when count is known and zero; otherwise mean presence |
| HRV | 25 | `nightly_hrv_rmssd`, `morning_rmssd` | Complete when either source is valid |
| Resting heart rate | 15 | `nightly_resting_hr`, `morning_mean_hr` | Complete when either source is valid |
| Sleep | 20 | `sleep_duration`, `sleep_score` | Mean presence of both fields |
| Readiness support | 10 | `respiration_rate`, `kubios_readiness` | Complete when either field is valid |

The weights sum to 100. Kubios and Polar do not receive separate mandatory
weights for the same physiological concept.

## Data Completeness formula

Each group produces a value from 0 to 100.

```text
data_completeness_score =
    activity_group   × 0.15
  + training_group   × 0.15
  + hrv_group        × 0.25
  + heart_rate_group × 0.15
  + sleep_group      × 0.20
  + readiness_group  × 0.10
```

Examples:

- Both activity fields present: activity group is 100.
- One activity field present: activity group is 50.
- `training_count = 0`: training group is 100 even if duration is null.
- `training_count > 0` with duration but no calories: training group is 67.
- Polar nightly HRV present and Kubios missing: HRV group is 100.
- Both HRV sources missing: HRV group is 0.
- Sleep score present but duration missing: sleep group is 50.

The final value is rounded and clamped to 0–100.

## Baseline Maturity formula

Every baseline-supported group uses the best valid history among equivalent
sources. A Polar HRV baseline and a Kubios HRV baseline are alternatives, not
two mandatory histories.

For one selected metric:

```text
metric_maturity = min(valid_days / window_days, 1) × 100
```

Rules:

- Missing baseline row gives maturity 0.
- `insufficient_data` may still produce partial maturity below the seven-day
  usability threshold.
- Seven valid days indicate minimum usability, not full maturity.
- Twenty-eight valid days produce full maturity for the default window.
- Alternative signals use the highest maturity available for that group.
- Multi-field groups such as activity and sleep average their metric maturity.
- Group weights match Data Completeness weights.
- Changing the baseline window requires a new confidence version review.

## Confidence v1.0 formula

```text
confidence_score =
    data_completeness_score × 0.55
  + baseline_maturity_score × 0.45
```

The score is rounded and clamped to 0–100.

Rationale:

- Current-day evidence receives a slight majority weight.
- A fully populated day with no personal history remains low confidence rather
  than appearing mature.
- Mature history cannot compensate for a day with missing current signals.
- The formula remains independent from Recovery Engine v1.0.

## Confidence levels

| Score | Level | Interpretation |
| ---: | --- | --- |
| 85–100 | `high` | Broad current coverage and mature personal history |
| 70–84 | `medium` | Useful evidence with limited gaps or history |
| 50–69 | `low` | Material gaps; use recommendations cautiously |
| 0–49 | `very_low` | Evidence is too limited for strong interpretation |

Level boundaries are product communication thresholds, not medical cutoffs.

## Persistence

Use a separate table named `recovery_confidence` rather than adding confidence
columns to `recovery_scores`.

Proposed fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | INTEGER | Surrogate primary key |
| `date` | TEXT UNIQUE | Target day |
| `data_completeness_score` | INTEGER | Current-day group coverage |
| `baseline_maturity_score` | INTEGER | Personal-history maturity |
| `confidence_score` | INTEGER | Combined deterministic confidence |
| `confidence_level` | TEXT | `high`, `medium`, `low`, or `very_low` |
| `group_scores_json` | TEXT | Explainable score by signal group |
| `available_groups_json` | TEXT | Groups with current evidence |
| `missing_groups_json` | TEXT | Groups without current evidence |
| `confidence_version` | TEXT | Unified Confidence Engine SemVer |
| `created_at` | TEXT | First creation timestamp |
| `updated_at` | TEXT | Latest recomputation timestamp |

The implementation must use date upsert and preserve Recovery Score rows.

## Explainability contract

The engine should be able to produce statements such as:

- “HRV is available from Polar; Kubios is not required for this group.”
- “Sleep duration is missing, so the sleep group is partially complete.”
- “The baseline is usable but has not yet reached the full 28-day window.”
- “Training count is zero and recorded, so this is a complete no-training day.”

It must not say that missing data means bad recovery.

## Dashboard and report contract

Dashboard now shows:

- Confidence score and level.
- Data completeness score.
- Baseline maturity score.
- Missing signal groups.
- Confidence version.

Dashboard reads persisted confidence results and does not reimplement the formula.
Report integration remains optional future presentation work.

## Future AI Coach contract

AI Coach may use confidence to calibrate wording:

- `high`: explain the recommendation normally.
- `medium`: mention the main data limitation.
- `low`: use cautious language and ask for missing measurements.
- `very_low`: avoid a strong training recommendation based only on system data.

AI Coach cannot calculate confidence, change Recovery Score, or hide missing
groups.

## Edge cases

- Empty day: completeness is 0.
- Full day with no history: maturity is 0 and confidence remains low.
- Polar-only recovery data: alternative HRV and heart-rate groups can be full.
- Kubios-only recovery data: morning alternatives can support HRV and heart
  rate, while sleep remains independently evaluated.
- No-training day: complete when `training_count = 0` is explicitly recorded.
- Unknown training day: incomplete when training count is null.
- Baseline `valid_days > window_days`: cap maturity at 100.
- Invalid negative values: treat as absent.
- Duplicate execution: update the same date.
- Future confidence version: do not overwrite the meaning of v1.0.

## Implementation acceptance criteria

The later implementation phase must include tests for:

1. Empty data.
2. Full data.
3. Partial activity fields.
4. Recorded no-training day.
5. Unknown training day.
6. Polar-only HRV and heart rate.
7. Kubios-only HRV and heart rate.
8. Partial sleep.
9. Seven-day baseline maturity.
10. Full 28-day baseline maturity.
11. Missing baseline rows.
12. Invalid negative and non-finite values.
13. Confidence boundaries.
14. Repeat upsert.
15. Recovery Score remains byte-for-byte unchanged for the same inputs.

## Approval and implementation result

The Product Owner approved implementation by continuing into this phase. The
following design choices are now implemented:

- Group weights.
- Completeness rules.
- The 55/45 confidence formula.
- Confidence level boundaries.
- The separate-table design.
- Proposed `confidence-v1.0` naming.

Migration `0.3.0` creates the independent table. Historical Recovery rows were
hashed before and after the real rebuild and remained unchanged.
