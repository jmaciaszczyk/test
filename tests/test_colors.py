import pytest

from sitegen import colors


@pytest.mark.parametrize(
    "value,expected",
    [
        ("#2563eb", "#2563eb"),
        ("  #2563EB  ", "#2563eb"),
        ("#abc", "#aabbcc"),
    ],
)
def test_normalize_hex_accepts_valid_colors(value, expected):
    assert colors.normalize_hex(value) == expected


@pytest.mark.parametrize("value", ["2563eb", "#12345", "#gggggg", "blue", ""])
def test_normalize_hex_rejects_invalid_colors(value):
    assert colors.normalize_hex(value) is None


def test_ramp_keeps_base_color_at_500():
    assert colors.ramp("#2563eb")[500] == "#2563eb"


def test_ramp_runs_light_to_dark():
    shades = colors.ramp("#2563eb")
    luminances = [colors.luminance(shades[stop]) for stop in sorted(shades)]
    assert luminances == sorted(luminances, reverse=True)


def test_ramp_covers_every_stop():
    assert sorted(colors.ramp("#2563eb")) == [
        50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950
    ]


def test_neutral_ramp_is_nearly_grey():
    for value in colors.neutral_ramp("#2563eb").values():
        red, green, blue = colors.to_rgb(value)
        assert max(red, green, blue) - min(red, green, blue) <= 40


def test_neutral_ramp_keeps_the_brand_hue():
    blue = colors.neutral_ramp("#2563eb")[500]
    red = colors.neutral_ramp("#eb2525")[500]
    assert colors.to_rgb(blue)[2] > colors.to_rgb(blue)[0]
    assert colors.to_rgb(red)[0] > colors.to_rgb(red)[2]


def test_neutral_ramp_runs_light_to_dark():
    shades = colors.neutral_ramp("#2563eb")
    luminances = [colors.luminance(shades[stop]) for stop in sorted(shades)]
    assert luminances == sorted(luminances, reverse=True)


def test_best_foreground_contrasts_with_background():
    assert colors.best_foreground("#111827") == "#ffffff"
    assert colors.best_foreground("#fde047") == "#0f172a"
