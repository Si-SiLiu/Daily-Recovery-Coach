# Supplement Product Catalog 2.0

Daily intake records store brand/product identity, quantity, unit, time and an
optional note. Ingredient facts live in a versioned product profile and are not
re-entered each day.

`supplement_products` preserves brand, variant, barcode, region, dosage form,
product kind, serving definition, formula/label version, provenance,
verification and supersession. `supplement_product_ingredients` stores multiple
active/nutrient facts per serving with source and confidence. Historical product
versions are separate rows; an update never overwrites a prior formula.

Ingredient totals are calculated only when the product is user-confirmed,
label-verified or source-verified, the intake unit exactly matches the serving
unit, the serving quantity is known, and the version is not stale. Otherwise the
intake remains valid and ingredients remain unavailable rather than zero.

Medication is a separate `product_kind`. Finasteride is normalized to
`medication`, excluded from ordinary supplement ingredient calculation, and
cannot produce medication dose-adjustment advice.

Migration 0.15.0 retains `meal_event_items.active_component_name`,
`active_amount`, and `active_unit`. Exact legacy identities migrate conservatively
to profiles and intake links; conflicting amounts form separate product versions.
