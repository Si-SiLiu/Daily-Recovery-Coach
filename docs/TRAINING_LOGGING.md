# Structured Training Logging

## Purpose

Structured Training Logging combines two complementary facts without overwriting
either source:

- Polar describes objective physiological load.
- Manual details describe the exercises, sets and training stimulus performed.

## Session Resolution

Each Polar `external_id` maps to at most one `training_sessions` row. Sessions on
the same date remain separate. A manual session has its own UUID and never merges
automatically with a Polar session by date alone.

Polar is authoritative for date/time, duration, heart rate, calories and distance.
Manual input is authoritative for exercises, order, sets, load, repetitions, RPE,
RIR, rest, technique content and an explicit sport-type override. The original
Polar sport identifier is always retained.

## Supported Training Forms

- Strength: load, repetitions, RPE/RIR and rest.
- Bodyweight: bodyweight, added/assisted load and repetitions.
- Duration: duration, RPE and rest without forced repetitions.
- Cardio: distance/duration, resistance and incline; sets are optional.
- Dance/technique: practice duration or performance count, proficiency and notes.

## Shortcuts and Editing

The UI supports adding, deleting, copying and reordering exercises; adding,
deleting, copying and batch-adding sets; copying exercises from training history;
saving drafts; completing logs; and soft deletion. Streamlit widget state retains
unsaved input when validation fails.

## Simple and Advanced Entry

Training Entry UI 1.0 defaults each session to Simple mode and RPE. Only fields
applicable to the selected measurement mode are rendered. Strength rows show
load, unit, repetitions, and either RPE or RIR; duration, distance/time,
dance/technique, and freeform use their own field maps. Advanced mode adds only
applicable professional fields. Mode changes do not delete hidden values or
convert RPE/RIR. Batch operations and confirmed deletes live under More actions.

## Deterministic Summary

Completed sets produce exercise/set counts, repetitions, RPE, rest, muscle-group
set counts and reliable strength volume. `lb` converts to `kg` with
`load-conversion-v1`; bodyweight and assisted load are excluded from volume.
No detail metric enters the Recovery or Baseline engines in this version.

## Privacy Boundary

Everything is local. AI Context receives completed session summaries only; it
does not receive notes or full set-level detail. No cloud model is called.
