# Nutrition Logging

## Simple structured input (4.0.0)

The default Nutrition page records one food or beverage per dynamic row using
only name, quantity and a controlled unit. Date, meal type and actual meal time
belong to the meal header. Category-first carbohydrate/protein/fat tables remain
only as preserved legacy data and are no longer the default input interface.

`meal_records` owns draft/completed status, source, UUID and soft deletion.
`meal_items` preserves raw quantity/unit, optional catalog identity, reliable
normalization, multi-tag classification and nullable nutrient values. Unknown
foods save as unclassified and never receive guessed weight or nutrition.

Quick entry includes row add/delete/copy, yesterday/previous-meal copy, drafts,
recent/favorite foods and templates. Copies receive new meal and item UUIDs.

## Brand-based supplement logging (5.0.0)

The daily grid is Brand | Product | Quantity | Unit | Actions. Meal time is the
default intake time and notes are optional. Active ingredient fields are no
longer present in ordinary daily input.

Product Catalog 2.0 owns ingredients, serving definitions, provenance,
verification and version history. Confirmed products can be reused without
re-entering ingredients; unconfirmed custom products save without fake values.
See [Supplement Product Catalog](SUPPLEMENT_PRODUCT_CATALOG.md) and
[Product Enrichment](SUPPLEMENT_PRODUCT_ENRICHMENT.md).

## Legacy supplement dynamic units (3.0.0 compatibility)

Legacy rows retain consumed `quantity + unit` and optional paired
`active_amount + active_unit`. New daily rows do not accept manual active doses.

Supported codes are centrally defined: `g`, `mg`, `mcg`, `ml`, `capsule`,
`tablet`, `sachet`, `scoop`, `drop`, `iu`. The ten-entry catalog recommends and
limits units for known supplements; custom supplements may use any supported
unit. UI labels are localized while database codes remain stable.

Summaries group only identical name/unit pairs. Unlike units are never converted
or added, and supplements do not contribute a guessed calorie or gram total.
History localizes intake units and may show a user-entered component note beside
the optional active dose; free-form notes remain excluded from AI Context.
