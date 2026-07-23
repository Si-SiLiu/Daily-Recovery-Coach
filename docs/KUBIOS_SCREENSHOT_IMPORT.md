# Kubios Screenshot Import

Kubios Screenshot Import remains version 1.2.0. It now recognizes the complete
visible Readiness/HRV Parameters field set and can create a measurement group
only after the user confirms that exactly two audits came from the same
measurement. Group creation does not import health data; each screenshot still
requires separate field review, a complete date, and final import confirmation.
See `KUBIOS_DATA_MODEL.md` for downstream selection and merge behavior.

## Scope

Version 1.2.0 accepts PNG, JPG/JPEG, locally decodable HEIC, and WEBP files.
It uses the bundled macOS Vision helper locally, without cloud OCR, API keys,
automatic photo-library access, or network calls. CSV remains the preferred
source and the recovery formulas are unchanged.

## Template-Based Recognition

The parser no longer treats a screenshot as one undifferentiated OCR document.
It supports three explicit layouts: Readiness Summary, Measurement Details, and
Results Summary. The configuration in
`config/kubios_screenshot_templates.json` defines aspect ranges, anchor labels,
fixed units, and normalized field regions. Normalized coordinates scale across
screen resolutions.

Template detection combines aspect ratio, portrait layout, and locally detected
anchor labels. Readiness Summary and Measurement Details/HRV Parameters are
calibrated from two user-approved, cropped, anonymized genuine screenshots and
may be selected automatically. Results Summary remains
`pending_real_calibration`, so it still requires manual template confirmation.

## Quality and Field OCR

Low resolution, landscape rotation, unexpected aspect ratio, and strong JPEG
compression are checked before field recognition. Sanitized portrait crops are
accepted as well as full-height phone screenshots. Each configured region is
cropped separately and evaluated with six local preprocessing variants:
original, grayscale, high contrast, adaptive binary, 2x scale, and 3x scale.
Field-specific character allowlists remove labels and units; decimal commas are
normalized. Multiple Vision candidates are voted deterministically and
disagreement lowers confidence. Units come from the selected template rather
than OCR guesses.

## Review and Calibration

The review screen shows the screenshot with the active field region highlighted
beside editable fields. Candidate agreement, confidence state, quick manual
entry, and high-confidence prefill acceptance are visible, but every image still
requires final explicit confirmation. Missing required fields block import.
Normalized template regions can be edited and saved locally only after a
separate calibration confirmation.

## Data Flow and Conflict Rules

The App hashes every image, preserves its immutable original, and stores only
project-relative paths. Confirmed records reuse the existing Kubios
normalization/upsert path. CSV conflicts require an explicit choice; CSV is the
default and a user-selected screenshot override is persisted. Batch files are
isolated, and there is no unreviewed bulk-import path.

## Privacy and Safety

Unconfirmed recognition never writes formal health data. Screenshots and full
OCR text never enter AI Context or ordinary logs. Deletion requires separate
confirmation. Recognition errors are data-entry issues, not physiological or
medical interpretations.

## Evaluation

`scripts/evaluate_kubios_screenshot_parser.py` reports template detection,
required-field exact match, numeric accuracy, per-field accuracy, manual
correction rate, failure rate, and failure filenames only. The three generated
synthetic fixtures currently pass all measured fields, but this is engineering
fixture evidence only. `tests/fixtures/kubios_screenshots/anonymized_real/`
contains two user-approved genuine samples. On those samples, template detection
and all visible supported numeric fields pass, with no OCR failure. Mandatory
import-field exact match is 0% because the crops omit a full date or other
required fields; the App correctly requires manual completion instead of
guessing. This small sample is calibration evidence, not a broad accuracy claim.
