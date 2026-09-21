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


def _channel_luminance(channel: int) -> float:
    ratio = channel / 255
    return ratio / 12.92 if ratio <= 0.04045 else ((ratio + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    red, green, blue = (_channel_luminance(c) for c in to_rgb(hex_color))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def best_foreground(hex_color: str) -> str:
    """Pick near-black or white text for legibility against a filled brand color."""
    return "#0f172a" if luminance(hex_color) > 0.4 else "#ffffff"
