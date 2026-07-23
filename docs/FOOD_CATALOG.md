# Food Catalog 1.0

The catalog contains nine bilingual reference foods: oats, Greek yogurt,
orange, egg, water, coffee, milk, broccoli and avocado. A food can have multiple
tags, such as egg = protein source + fat source + animal food.

Supported units are `g`, `kg`, `ml`, `l`, `piece`, `slice`, `serving`, `bowl`,
`cup`, `spoon`, `bottle`, and `pack`. Custom foods may use any supported unit.
Normalization occurs only for direct metric units or an explicit catalog
serving. Unknown bowls, pieces or servings remain unnormalized.
