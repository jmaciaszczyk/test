"""Derive a Tailwind-style color ramp from a single brand hex color."""

from __future__ import annotations

# Each stop mixes the base color toward white or black by the given amount.
_STOPS: dict[int, tuple[str, float]] = {
    50: ("white", 0.95),
    100: ("white", 0.90),
    200: ("white", 0.75),
    300: ("white", 0.55),
    400: ("white", 0.28),
    500: ("base", 0.0),
    600: ("black", 0.12),
    700: ("black", 0.28),
    800: ("black", 0.44),
    900: ("black", 0.60),
    950: ("black", 0.74),
}


def normalize_hex(value: str) -> str | None:
    """Return a canonical ``#rrggbb`` string, or None if value is not a hex color."""
    text = value.strip()
    if not text.startswith("#"):
        return None
    digits = text[1:]
    if len(digits) == 3:
        digits = "".join(char * 2 for char in digits)
    if len(digits) != 6:
        return None
    try:
        int(digits, 16)
    except ValueError:
        return None
    return "#" + digits.lower()


def to_rgb(hex_color: str) -> tuple[int, int, int]:
    digits = hex_color.lstrip("#")
    return int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)


def _mix(channel: int, target: int, amount: float) -> int:
    return round(channel + (target - channel) * amount)


def ramp(hex_color: str) -> dict[int, str]:
    """Build a 50-950 ramp around ``hex_color``, which sits at stop 500."""
    red, green, blue = to_rgb(hex_color)
    shades: dict[int, str] = {}
    for stop, (direction, amount) in _STOPS.items():
        if direction == "base":
            shades[stop] = hex_color
            continue
        target = 255 if direction == "white" else 0
        mixed = (
            _mix(red, target, amount),
            _mix(green, target, amount),
            _mix(blue, target, amount),
        )
        shades[stop] = "#{:02x}{:02x}{:02x}".format(*mixed)
    return shades


# Lightness per stop for the neutral ramp, which carries a trace of the brand
# hue so greys sit with the brand instead of against it.
_NEUTRAL_LIGHTNESS = {
    50: 0.98,
    100: 0.96,
    200: 0.90,
    300: 0.82,
    400: 0.64,
    500: 0.47,
    600: 0.36,
    700: 0.28,
    800: 0.19,
    900: 0.12,
    950: 0.07,
}


def _rgb_to_hsl(red: int, green: int, blue: int) -> tuple[float, float, float]:
    r, g, b = red / 255, green / 255, blue / 255
    high, low = max(r, g, b), min(r, g, b)
    lightness = (high + low) / 2

    if high == low:
        return 0.0, 0.0, lightness

    delta = high - low
    saturation = delta / (2 - high - low) if lightness > 0.5 else delta / (high + low)
    if high == r:
        hue = ((g - b) / delta) % 6
    elif high == g:
        hue = (b - r) / delta + 2
    else:
        hue = (r - g) / delta + 4
    return hue * 60, saturation, lightness


def _hsl_to_rgb(hue: float, saturation: float, lightness: float) -> tuple[int, int, int]:
    chroma = (1 - abs(2 * lightness - 1)) * saturation
    second = chroma * (1 - abs(((hue / 60) % 2) - 1))
    match = lightness - chroma / 2

    if hue < 60:
        rgb = (chroma, second, 0.0)
    elif hue < 120:
        rgb = (second, chroma, 0.0)
    elif hue < 180:
        rgb = (0.0, chroma, second)
    elif hue < 240:
        rgb = (0.0, second, chroma)
    elif hue < 300:
        rgb = (second, 0.0, chroma)
    else:
        rgb = (chroma, 0.0, second)

    return tuple(round((channel + match) * 255) for channel in rgb)


def neutral_ramp(hex_color: str, saturation: float = 0.08) -> dict[int, str]:
    """Build a near-grey ramp that keeps a hint of the brand hue."""
    hue, _, _ = _rgb_to_hsl(*to_rgb(hex_color))
    shades = {}
    for stop, lightness in _NEUTRAL_LIGHTNESS.items():
        red, green, blue = _hsl_to_rgb(hue, saturation, lightness)
        shades[stop] = f"#{red:02x}{green:02x}{blue:02x}"
    return shades


def _channel_luminance(channel: int) -> float:
    ratio = channel / 255
    return ratio / 12.92 if ratio <= 0.04045 else ((ratio + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    red, green, blue = (_channel_luminance(c) for c in to_rgb(hex_color))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def best_foreground(hex_color: str) -> str:
    """Pick near-black or white text for legibility against a filled brand color."""
    return "#0f172a" if luminance(hex_color) > 0.4 else "#ffffff"
