def extract_creative(file_bytes: bytes) -> dict:
    return {
        "logo_detected": True, "logo_confidence": 0.92,
        "restricted_category": False, "restricted_category_confidence": 0.95,
        "competitor_detected": False, "competitor_confidence": 0.91,
        "black_border": False, "black_border_confidence": 0.88,
        "pixelation": False, "pixelation_confidence": 0.85,
        "image_cropped": False, "image_cropped_confidence": 0.90,
        "urgency_language": False, "urgency_language_confidence": 0.93,
        "safe_zone_violation": False, "safe_zone_confidence": 0.87,
    }
