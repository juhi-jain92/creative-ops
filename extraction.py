import anthropic
import base64
import json
import time

client = anthropic.Anthropic()

_BASE_PROMPT = """Analyze this display ad creative image. Return ONLY valid JSON, no preamble.

For each field, return a value and a confidence score (0-1):
- logo_detected (bool)
- restricted_category (bool, categories: alcohol, gambling, tobacco, pharma)
- competitor_detected (bool)
- black_border (bool)
- pixelation (bool)
- image_cropped (bool)
- urgency_language (bool)
- safe_zone_violation (bool)
- profanity_detected (bool) — detect explicit profanity or deliberately deceptive words (e.g. "guaranteed returns", "no risk", "Fck", "Sht")
- advertiser_match (bool) — does the brand/logo visible in the image match "{advertiser}"? Case-insensitive, partial match is fine.
- vertical_match (bool) — does the product or service category in the image match "{vertical}"?

Format: {{"field_name": {{"value": ..., "confidence": 0.XX}}, ...}}"""

_FALLBACK_FIELDS = [
    "logo_detected", "restricted_category", "competitor_detected",
    "black_border", "pixelation", "image_cropped",
    "urgency_language", "safe_zone_violation", "profanity_detected",
    "advertiser_mismatch", "vertical_mismatch",
]

_MEDIA_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
}


def _make_fallback() -> dict:
    return {field: {"value": False, "confidence": 0.0} for field in _FALLBACK_FIELDS}


def extract_creative_fields(file_bytes: bytes, filename: str, metadata: dict) -> dict:
    advertiser = metadata.get("Advertiser", "")
    vertical = metadata.get("Vertical", "")

    prompt = _BASE_PROMPT.format(advertiser=advertiser, vertical=vertical)

    ext = filename.rsplit(".", 1)[-1].lower()
    media_type = _MEDIA_TYPES.get(ext, "image/jpeg")
    b64_image = base64.b64encode(file_bytes).decode("utf-8")

    retryable = (anthropic.APITimeoutError, anthropic.APIConnectionError)
    delays = [2, 4]
    response = None

    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                timeout=30,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64_image}},
                        {"type": "text", "text": prompt},
                    ],
                }],
            )
            break
        except retryable as e:
            if attempt < len(delays):
                time.sleep(delays[attempt])
            else:
                print(f"API error after retries: {e}")
                return _make_fallback()
        except anthropic.APIStatusError as e:
            # 429 = rate limited, 5xx = server error. Both worth a retry.
            # 4xx other than 429 = our request is malformed, retrying won't help.
            if e.status_code == 429 or e.status_code >= 500:
                if attempt < len(delays):
                    time.sleep(delays[attempt])
                    continue
            print(f"API error (status {e.status_code}), not retrying: {e}")
            return _make_fallback()

    if response is None:
        return _make_fallback()

    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"JSON parse error: {e}\nRaw response: {raw}")
        return _make_fallback()

    # Invert match → mismatch so rules can treat False as "pass" consistently
    for match_field, mismatch_field in (
        ("advertiser_match", "advertiser_mismatch"),
        ("vertical_match", "vertical_mismatch"),
    ):
        entry = parsed.pop(match_field, None)
        if isinstance(entry, dict) and "value" in entry and "confidence" in entry:
            parsed[mismatch_field] = {
                "value": not entry["value"],
                "confidence": entry["confidence"],
            }
        else:
            # Field missing or malformed shape (e.g. no "value" key) —
            # treat as undetected rather than crashing the pipeline.
            parsed[mismatch_field] = {"value": False, "confidence": 0.0}

    # Same guard for every other field: if the model returned something
    # with a missing/wrong shape, replace it with a safe default instead
    # of letting a downstream KeyError take down the pipeline.
    for field in _FALLBACK_FIELDS:
        entry = parsed.get(field)
        if not (isinstance(entry, dict) and "value" in entry and "confidence" in entry):
            parsed[field] = {"value": False, "confidence": 0.0}

    return parsed


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "tests/images/gd001_nike_clean_apparel.png"
    with open(path, "rb") as f:
        file_bytes = f.read()

    meta = {"Advertiser": sys.argv[2] if len(sys.argv) > 2 else "", "Vertical": sys.argv[3] if len(sys.argv) > 3 else ""}
    result = extract_creative_fields(file_bytes, path, meta)
    print(json.dumps(result, indent=2))
