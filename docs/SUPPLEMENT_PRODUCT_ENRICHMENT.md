# Supplement Product Enrichment 1.0

The provider-agnostic contract lives under `src/supplements/enrichment/`.
Candidates include product/variant/barcode/serving data, ingredients, source,
confidence and retrieval time. Search and label OCR can only create candidates;
they cannot create authoritative ingredient facts.

Current runtime status is `provider_blocked`. With no approved provider, the
resolver raises a gate error before any network request. Manual minimal product
profiles remain available locally.

Source priority is: confirmed current label, manufacturer label/official page,
trusted structured database, barcode database, qualified retailer, AI-assisted
web search, then manual minimal information. Conflicts are retained in
`supplement_product_sources` with review state and never silently overwrite a
confirmed profile.

Barcode, front-label and facts-label fields and candidate contracts are ready.
Actual scanner/OCR providers are deliberately not enabled. Any future candidate
requires explicit user confirmation before it can become a formal profile.
