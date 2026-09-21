import pytest

from sitegen.model import ConfigError, build_site_data


def build(**sections):
    sections.setdefault("business", {"name": "Test Shop"})
    return build_site_data(sections)


def test_minimal_config_only_needs_a_name():
    data, warnings = build_site_data({"business": {"name": "Corner Barbers"}})
    assert data["business"]["name"] == "Corner Barbers"
    assert data["services"] == []
    assert data["hours"] == []
    assert any("tagline" in warning for warning in warnings)


def test_empty_file_is_rejected():
    with pytest.raises(ConfigError, match="empty"):
        build_site_data(None)


def test_missing_business_section_is_rejected():
    with pytest.raises(ConfigError) as excinfo:
        build_site_data({"hours": {"monday": "9:00-17:00"}})
    assert any("business" in error for error in excinfo.value.errors)


def test_blank_name_is_rejected():
    with pytest.raises(ConfigError, match="cannot be empty"):
        build_site_data({"business": {"name": "   "}})


def test_invalid_brand_color_is_rejected():
    with pytest.raises(ConfigError, match="not a hex color"):
        build(brand={"primary": "cornflower"})


def test_unknown_top_level_section_warns_but_passes():
    _, warnings = build(mascot={"name": "Doris"})
    assert any("mascot" in warning for warning in warnings)


def test_phone_href_strips_formatting():
    data, _ = build_site_data(
        {"business": {"name": "Test Shop", "phone": "+48 (22) 123-45-67"}}
    )
    assert data["business"]["phoneHref"] == "tel:+48221234567"


def test_hours_mark_closed_days_and_keep_order():
    data, _ = build(
        hours={"sunday": "closed", "monday": "9:00-17:00"}
    )
    assert [entry["day"] for entry in data["hours"]] == ["Monday", "Sunday"]
    assert data["hours"][0]["closed"] is False
    assert data["hours"][1]["closed"] is True
    assert data["hours"][1]["value"] == "Closed"


def test_hours_produce_schema_strings_only_when_parseable():
    data, _ = build(hours={"monday": "9:00-17:00", "tuesday": "by appointment"})
    by_day = {entry["day"]: entry for entry in data["hours"]}
    assert by_day["Monday"]["schema"] == "Mo 09:00-17:00"
    assert by_day["Tuesday"]["schema"] == ""
    assert by_day["Tuesday"]["value"] == "by appointment"


def test_non_day_hours_key_warns():
    _, warnings = build(hours={"funday": "9:00-17:00"})
    assert any("funday" in warning for warning in warnings)


def test_about_body_splits_into_paragraphs():
    data, _ = build(about={"body": "First para.\n\nSecond para.\n"})
    assert data["about"]["paragraphs"] == ["First para.", "Second para."]
    assert data["about"]["heading"] == "About us"


def test_services_require_a_name():
    with pytest.raises(ConfigError) as excinfo:
        build(services=[{"description": "no name here"}])
    assert any("services[0].name" in error for error in excinfo.value.errors)


def test_cta_falls_back_to_the_phone_number():
    data, _ = build_site_data(
        {"business": {"name": "Test Shop", "phone": "555 0199"}}
    )
    assert data["cta"] == {"label": "Call us", "url": "tel:5550199"}


def test_seo_title_defaults_to_name_and_tagline():
    data, _ = build_site_data(
        {"business": {"name": "Test Shop", "tagline": "Good things"}}
    )
    assert data["seo"]["title"] == "Test Shop — Good things"


def test_map_url_is_derived_from_the_address():
    data, _ = build_site_data(
        {
            "business": {
                "name": "Test Shop",
                "address": {"street": "8 Ashfield Road", "city": "Bristol"},
            }
        }
    )
    assert "8+Ashfield+Road" in data["business"]["mapUrl"]


def test_structured_data_includes_address_and_hours():
    data, _ = build_site_data(
        {
            "business": {
                "name": "Test Shop",
                "type": "Bakery",
                "address": {"street": "8 Ashfield Road", "city": "Bristol"},
            },
            "hours": {"monday": "9:00-17:00"},
            "social": {"instagram": "https://instagram.com/example"},
        }
    )
    schema = data["structuredData"]
    assert schema["@type"] == "Bakery"
    assert schema["address"]["streetAddress"] == "8 Ashfield Road"
    assert schema["openingHours"] == ["Mo 09:00-17:00"]
    assert schema["sameAs"] == ["https://instagram.com/example"]


def test_language_defaults_to_english_and_can_be_overridden():
    assert build()[0]["lang"] == "en"
    assert build(lang="pl")[0]["lang"] == "pl"


def test_errors_are_collected_together():
    with pytest.raises(ConfigError) as excinfo:
        build_site_data({"business": {}, "brand": {"primary": "nope"}})
    assert len(excinfo.value.errors) >= 2
