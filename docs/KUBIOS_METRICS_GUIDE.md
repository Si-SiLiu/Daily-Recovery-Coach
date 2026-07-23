# Kubios Metrics Guide

## Home Core Metrics

The Dashboard home page shows only Readiness, RMSSD, mean heart rate, PNS index,
SNS index, and measurement quality. Baseline deltas appear only when at least
seven valid prior measurements exist. PNS and SNS are dimensionless contextual
indices and are not standalone medical conclusions.

## Advanced Metrics Page

The dedicated **Kubios Advanced Metrics** page groups secondary and raw metrics:

- Variability: SDNN, Mean RR, Poincaré SD1, and Poincaré SD2.
- Autonomic/context: respiratory rate, Stress Index, physiological age, and mood.
- Frequency domain: LF power, HF power, normalized LF/HF power, and LF/HF ratio.
- Trends: baseline comparisons and deterministic seven-day slopes.

Frequency-domain measures are protocol- and context-sensitive. Physiological age
and mood are Kubios-provided descriptive outputs, not diagnoses. Missing values
are displayed as unavailable rather than estimated.

## Data Reliability

Source and completeness labels accompany selected data. CSV is preferred over a
reviewed screenshot, and a reviewed screenshot is preferred over manual input,
unless the user explicitly selects another reviewed record. The raw source is
never silently deleted.

## AI Context and Reports

Daily reports contain only the core Kubios summary and a link to the advanced
page. AI Context follows the same default. Exporting advanced raw metrics requires
two confirmations and still excludes raw OCR text, images, paths, and raw JSON.

## Limitations

Current real calibration covers two complementary cropped layouts. Both lack a
complete ISO date, so formal import still requires user completion and review.
Results Summary and broader full-screen layouts need additional confirmed samples.
