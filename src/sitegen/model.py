"""Validate the business YAML file and normalize it into the site data model."""

from __future__ import annotations

import re
from typing import Any

from sitegen import colors

DAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

_DAY_ABBREVIATIONS = {
    "monday": "Mo",
    "tuesday": "Tu",
    "wednesday": "We",
    "thursday": "Th",
    "friday": "Fr",
    "saturday": "Sa",
    "sunday": "Su",
}

_SOCIAL_LABELS = {
    "facebook": "Facebook",
    "instagram": "Instagram",
    "x": "X",
    "twitter": "X",
    "linkedin": "LinkedIn",
    "tiktok": "TikTok",
    "youtube": "YouTube",
    "google": "Google Business",
    "yelp": "Yelp",
}

_TOP_LEVEL_KEYS = {
    "business",
    "brand",
    "hours",
    "services",
    "about",
    "cta",
    "social",
    "seo",
    "site_url",
    "lang",
}

_CLOSED_WORDS = {"closed", "zamkniete", "zamknięte", "-", "—"}

# Matches "9:00-17:00", "09:00 – 17:30" and similar; anything else is passed
# through as display text only and left out of the structured data.
_HOURS_RE = re.compile(
    r"^\s*(\d{1,2}):(\d{2})\s*[-–—]\s*(\d{1,2}):(\d{2})\s*$"
)

DEFAULT_PRIMARY = "#2563eb"
DEFAULT_ACCENT = "#f59e0b"
DEFAULT_SITE_URL = "https://example.com"


class ConfigError(Exception):
    """Raised when the input file cannot be turned into a valid site."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def _mapping(value: Any, path: str, errors: list[str]) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path}: expected a set of key/value pairs")
        return {}
    return value


def _text(
    data: dict,
    key: str,
    path: str,
    errors: list[str],
    *,
    required: bool = False,
    default: str = "",
) -> str:
    value = data.get(key)
    if value is None:
        if required:
            errors.append(f"{path}.{key}: is required")
        return default
    if isinstance(value, bool):
        errors.append(f"{path}.{key}: expected text")
        return default
    if isinstance(value, (int, float)):
        return str(value)
    if not isinstance(value, str):
        errors.append(f"{path}.{key}: expected text")
        return default
    return value.strip()


def _phone_href(phone: str) -> str:
    cleaned = re.sub(r"[^\d+]", "", phone)
    cleaned = cleaned[:1] + cleaned[1:].replace("+", "")
    return f"tel:{cleaned}" if cleaned.strip("+") else ""


def _paragraphs(body: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", body) if block.strip()]


def _address(raw: dict, path: str, errors: list[str]) -> dict:
    address = {
        "street": _text(raw, "street", path, errors),
        "city": _text(raw, "city", path, errors),
        "region": _text(raw, "region", path, errors),
        "postalCode": _text(raw, "postal_code", path, errors),
        "country": _text(raw, "country", path, errors),
    }
    locality = " ".join(part for part in [address["postalCode"], address["city"]] if part)
    parts = [address["street"], locality, address["region"], address["country"]]
    address["oneLine"] = ", ".join(part for part in parts if part)
    return address


def _hours(raw: Any, errors: list[str], warnings: list[str]) -> list[dict]:
    data = _mapping(raw, "hours", errors)
    for key in data:
        if str(key).lower() not in DAYS:
            warnings.append(f"hours.{key}: not a day of the week, ignored")

    entries: list[dict] = []
    for day in DAYS:
        value = data.get(day)
        if value is None:
            continue
        if not isinstance(value, str):
            errors.append(f"hours.{day}: expected text such as '9:00-17:00'")
            continue
        text = value.strip()
        closed = text.lower() in _CLOSED_WORDS
        entries.append(
            {
                "day": day.capitalize(),
                "value": "Closed" if closed else text,
                "closed": closed,
                "schema": _schema_hours(day, text) if not closed else "",
            }
        )
    return entries


def _schema_hours(day: str, text: str) -> str:
    match = _HOURS_RE.match(text)
    if not match:
        return ""
    open_h, open_m, close_h, close_m = match.groups()
    return f"{_DAY_ABBREVIATIONS[day]} {int(open_h):02d}:{open_m}-{int(close_h):02d}:{close_m}"


def _services(raw: Any, errors: list[str]) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        errors.append("services: expected a list of items")
        return []

    services = []
    for index, item in enumerate(raw):
        path = f"services[{index}]"
        data = _mapping(item, path, errors)
        if not data:
            continue
        services.append(
            {
                "name": _text(data, "name", path, errors, required=True),
                "description": _text(data, "description", path, errors),
                "price": _text(data, "price", path, errors),
            }
        )
    return services


def _social(raw: Any, errors: list[str]) -> list[dict]:
    data = _mapping(raw, "social", errors)
    links = []
    for key, value in data.items():
        name = str(key).lower()
        if not isinstance(value, str) or not value.strip():
            errors.append(f"social.{key}: expected a URL")
            continue
        links.append(
            {
                "label": _SOCIAL_LABELS.get(name, str(key).capitalize()),
                "url": value.strip(),
            }
        )
    return links


def _brand(raw: Any, errors: list[str]) -> dict:
    data = _mapping(raw, "brand", errors)

    def color(key: str, fallback: str) -> str:
        value = _text(data, key, "brand", errors)
        if not value:
            return fallback
        normalized = colors.normalize_hex(value)
        if normalized is None:
            errors.append(f"brand.{key}: '{value}' is not a hex color such as #2563eb")
            return fallback
        return normalized

    primary = color("primary", DEFAULT_PRIMARY)
    accent = color("accent", DEFAULT_ACCENT)
    font = _text(data, "font", "brand", errors)

    return {
        "primary": primary,
        "accent": accent,
        "primaryRamp": colors.ramp(primary),
        "accentRamp": colors.ramp(accent),
        "onPrimary": colors.best_foreground(primary),
        "onAccent": colors.best_foreground(accent),
        "font": font,
        "fontUrl": _google_font_url(font) if font else "",
    }


def _google_font_url(family: str) -> str:
    slug = family.strip().replace(" ", "+")
    return f"https://fonts.googleapis.com/css2?family={slug}:wght@400;500;700;800&display=swap"


def build_site_data(raw: Any) -> tuple[dict, list[str]]:
    """Turn parsed YAML into the data the templates consume.

    Returns the site data plus non-fatal warnings. Raises ConfigError if the
    input cannot produce a usable site.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if raw is None:
        raise ConfigError(["the input file is empty"])

    root = _mapping(raw, "<root>", errors)
    if errors:
        raise ConfigError(errors)

    for key in root:
        if key not in _TOP_LEVEL_KEYS:
            warnings.append(f"{key}: unknown top-level section, ignored")

    if "business" not in root:
        errors.append("business: section is required")

    business_raw = _mapping(root.get("business"), "business", errors)
    name = _text(business_raw, "name", "business", errors, required=True)
    if "name" in business_raw and not name:
        errors.append("business.name: cannot be empty")
    tagline = _text(business_raw, "tagline", "business", errors)
    description = _text(business_raw, "description", "business", errors)
    phone = _text(business_raw, "phone", "business", errors)
    email = _text(business_raw, "email", "business", errors)
    site_url = _text(root, "site_url", "<root>", errors) or DEFAULT_SITE_URL

    address = _address(
        _mapping(business_raw.get("address"), "business.address", errors),
        "business.address",
        errors,
    )

    hours = _hours(root.get("hours"), errors, warnings)
    services = _services(root.get("services"), errors)
    social = _social(root.get("social"), errors)
    brand = _brand(root.get("brand"), errors)

    about_raw = _mapping(root.get("about"), "about", errors)
    about = {
        "heading": _text(about_raw, "heading", "about", errors) or "About us",
        "paragraphs": _paragraphs(_text(about_raw, "body", "about", errors)),
    }

    cta_raw = _mapping(root.get("cta"), "cta", errors)
    cta_label = _text(cta_raw, "label", "cta", errors)
    cta_url = _text(cta_raw, "url", "cta", errors)
    if not cta_url and phone:
        cta_label = cta_label or "Call us"
        cta_url = _phone_href(phone)

    seo_raw = _mapping(root.get("seo"), "seo", errors)
    seo_title = _text(seo_raw, "title", "seo", errors)
    seo_description = _text(seo_raw, "description", "seo", errors)

    if errors:
        raise ConfigError(errors)

    if not tagline and not description:
        warnings.append(
            "business: no tagline or description, the hero section will look sparse"
        )

    map_url = _text(business_raw, "map_url", "business", errors)
    if not map_url and address["oneLine"]:
        query = address["oneLine"].replace(" ", "+").replace(",", "%2C")
        map_url = f"https://www.google.com/maps/search/?api=1&query={query}"

    data = {
        "lang": _text(root, "lang", "<root>", errors) or "en",
        "business": {
            "name": name,
            "tagline": tagline,
            "description": description,
            "type": _text(business_raw, "type", "business", errors) or "LocalBusiness",
            "phone": phone,
            "phoneHref": _phone_href(phone),
            "email": email,
            "address": address,
            "mapUrl": map_url,
        },
        "brand": brand,
        "hours": hours,
        "services": services,
        "about": about,
        "cta": {"label": cta_label, "url": cta_url},
        "social": social,
        "seo": {
            "title": seo_title or (f"{name} — {tagline}" if tagline else name),
            "description": seo_description or description or tagline,
            "siteUrl": site_url.rstrip("/"),
        },
    }
    data["structuredData"] = _structured_data(data)
    return data, warnings


def _structured_data(data: dict) -> dict:
    business = data["business"]
    address = business["address"]
    schema: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": business["type"],
        "name": business["name"],
        "url": data["seo"]["siteUrl"],
    }
    if business["description"] or business["tagline"]:
        schema["description"] = business["description"] or business["tagline"]
    if business["phone"]:
        schema["telephone"] = business["phone"]
    if business["email"]:
        schema["email"] = business["email"]

    postal = {
        key: value
        for key, value in {
            "streetAddress": address["street"],
            "addressLocality": address["city"],
            "addressRegion": address["region"],
            "postalCode": address["postalCode"],
            "addressCountry": address["country"],
        }.items()
        if value
    }
    if postal:
        schema["address"] = {"@type": "PostalAddress", **postal}

    opening = [entry["schema"] for entry in data["hours"] if entry["schema"]]
    if opening:
        schema["openingHours"] = opening

    links = [link["url"] for link in data["social"]]
    if links:
        schema["sameAs"] = links

    return schema
