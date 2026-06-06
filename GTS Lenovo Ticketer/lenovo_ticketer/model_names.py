from __future__ import annotations

import re


def _map_lookup_key(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", value.upper())


def normalize_model_name(value: object, model_map: dict[str, str] | None = None) -> str:
    if value in (None, ""):
        return ""

    text = str(value).strip()
    if not text:
        return ""

    model_map = model_map or {}
    direct = model_map.get(text)
    if direct:
        return direct

    normalized_map = {_map_lookup_key(k): v for k, v in model_map.items()}
    mapped = normalized_map.get(_map_lookup_key(text))
    if mapped:
        return mapped

    upper_words = re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()
    product_match = re.search(r"\b(\d{3,4}[A-Z])\b", upper_words)
    gen_match = re.search(r"\bG(?:EN)?\s*(\d+[A-Z]?)\b", upper_words)

    if product_match:
        product = product_match.group(1)
        if gen_match:
            return f"Lenovo {product} G{gen_match.group(1)}"
        return f"Lenovo {product}"

    return text
