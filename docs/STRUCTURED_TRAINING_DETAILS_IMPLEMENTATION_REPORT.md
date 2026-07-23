# STRUCTURED_TRAINING_DETAILS_IMPLEMENTATION_REPORT

## Goal
Add analyzable exercise and set details while retaining Polar physiological load.

## Previous Training Model
The training page displayed date-level Polar summaries. Legacy local workout sets
were flat and lacked exercise identity, UUIDs, set types, units and soft deletion.

## New Training Data Model
Schema 0.14.0 adds normalized sessions, exercise catalog, session exercises and
training sets with UUIDs, ordering, audit timestamps and soft deletion.

## Database Migration
The formal migration created a pre-migration backup, migration-ledger entry 14,
23 catalog rows and canonical session links for all Polar records.

## Polar and Manual Data Resolution
Polar remains authoritative for date/time, duration, heart rate, calories and
distance. Manual details own exercises and sets. Sport overrides are marked
`manual_override`; original Polar sport values remain unchanged.

## Exercise Catalog
Twenty-three bilingual actions cover strength, bodyweight, cardio, dance and
technique. Custom exercises remain session-local.

## Supported Training Types
Strength, bodyweight, duration, cardio, dance/technique and freeform modes have
mode-appropriate validation and do not force load × repetitions onto every sport.

## Training Session UI
History now operates per session, including same-day multiple sessions, with a
View/Edit entry, read-only Polar metrics, manual session creation and draft status.

## Exercise and Set Entry
Actions store order, category, muscle group, equipment, laterality and proficiency.
Sets store type, load/unit, repetitions, duration, distance, RPE/RIR, rest, side,
completion and notes.

## Copy Previous Set
Users can copy the previous set, batch-add identical sets, copy an exercise and
copy a prior exercise structure with new UUIDs.

## Derived Training Metrics
Deterministic summaries include action/set counts, repetitions, volume in kg,
RPE, rest and muscle-group sets. Bodyweight/assisted loads are excluded; lb uses
the versioned `load-conversion-v1` rule.

## Internationalization
All new fields, enums, actions and statuses are available in Simplified Chinese
and English; the i18n coverage scanner passes.

## AI Context Preparation
AI Context Export 1.3.0 exposes completed session summaries only. Notes, Polar raw
payloads and full set detail are excluded. No cloud AI is invoked.

## Tests
Migration, uniqueness, Polar authority, same-day separation, CRUD, validation,
copying, training modes, summaries, privacy and UI contracts are covered.

## Regression Results
The complete suite passes. Recovery, Baseline, Confidence, Daily Metrics and Polar
fetch/import logic are unchanged.

## Version Changes
App 0.26.0; Schema 0.14.0; Dashboard 1.7.0; Training Logging 1.0.0;
Exercise Catalog 1.0.0; AI Context Export 1.3.0.

## Documentation Updated
Training, catalog, database, dictionary, architecture, AI Context, i18n, versions,
state, handoff, roadmap, changelog, quality gate, README, ADR and release notes.

## Known Limitations
Training templates and automatic similarity-based Polar merging are intentionally
deferred. Only user-confirmed or exact external-ID relationships are accepted.

## Quality Gate Result
PASS. Polar sessions accept structured details; exercises, sets, load, repetitions,
RPE/RIR and rest are supported; training modes remain appropriate; Polar objective
data has priority; same-day sessions stay separate; deterministic engines are unchanged.
