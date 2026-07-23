"""Central source priority for conflict display; lower is stronger."""

SOURCE_PRIORITY = {
    "user_label": 1,
    "manufacturer_label": 2,
    "official_product_page": 2,
    "trusted_database": 3,
    "barcode_database": 4,
    "retailer_page": 5,
    "ai_assisted_search": 6,
    "manual_minimal": 7,
    "imported": 7,
}


def source_rank(source_type: str) -> int:
    return SOURCE_PRIORITY.get(source_type, 99)
