# Exercise Catalog

Version: 1.0.0

The local bilingual catalog contains 23 active reference exercises spanning
strength, bodyweight, cardio, dance and technique practice. Each entry provides:

- stable canonical and Chinese/English names;
- exercise category and movement pattern;
- primary and secondary muscle groups;
- equipment and measurement mode;
- unilateral/bilateral default.

Measurement modes are `weight_reps`, `bodyweight_reps`, `assisted_reps`,
`duration`, `distance_duration`, `dance_practice` and `freeform`.

Users may log a custom exercise without adding it globally. A custom exercise
must have a name, but it is never silently inserted into the shared catalog.

Simple Training Entry auto-fills category, measurement mode, primary muscle,
equipment, laterality, and a mode-derived default load unit. These facts are
read-only by default and shown under View exercise information. A custom action
remains session-only unless the user explicitly selects Save to exercise library
and then saves the session through the service layer.
