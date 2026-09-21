import json

import pytest
import yaml

from sitegen import generator
from sitegen.model import build_site_data


@pytest.fixture
def site_data():
    data, _ = build_site_data(
        {
            "business": {"name": "Spoke & Chain", "phone": "+44 20 7946 0812"},
            "brand": {"primary": "#1f6f5c", "font": "Source Sans 3"},
            "services": [{"name": "Puncture repair", "price": "from £12"}],
        }
    )
    return data


def test_generate_writes_a_runnable_project(site_data, tmp_path):
    generator.generate(site_data, tmp_path)

    for relative in [
        "package.json",
        "astro.config.mjs",
        "tsconfig.json",
        ".gitignore",
        "README.md",
        "public/robots.txt",
        "public/favicon.svg",
        "src/styles/global.css",
        "src/layouts/Base.astro",
        "src/pages/index.astro",
        "src/data/business.json",
    ]:
        assert (tmp_path / relative).is_file(), f"{relative} was not generated"


def test_every_component_imported_by_the_page_exists(site_data, tmp_path):
    generator.generate(site_data, tmp_path)
    components = tmp_path / "src" / "components"
    for name in [
        "Header",
        "Hero",
        "Reviews",
        "Services",
        "About",
        "Hours",
        "Contact",
        "Footer",
        "Icon",
        "Stars",
    ]:
        assert (components / f"{name}.astro").is_file()


def test_business_json_round_trips(site_data, tmp_path):
    generator.generate(site_data, tmp_path)
    written = json.loads((tmp_path / "src" / "data" / "business.json").read_text("utf-8"))
    assert written["business"]["name"] == "Spoke & Chain"
    assert written["services"][0]["price"] == "from £12"


def test_package_json_is_valid_and_pins_versions(site_data, tmp_path):
    generator.generate(site_data, tmp_path)
    package = json.loads((tmp_path / "package.json").read_text("utf-8"))
    assert package["name"] == "spoke-chain"
    assert package["dependencies"] == generator.DEPENDENCY_VERSIONS


def test_stylesheet_carries_the_brand_color_and_font(site_data, tmp_path):
    generator.generate(site_data, tmp_path)
    css = (tmp_path / "src" / "styles" / "global.css").read_text("utf-8")
    assert '@import "tailwindcss";' in css
    assert "--color-brand-500: #1f6f5c;" in css
    assert '--font-sans: "Source Sans 3"' in css


def test_stylesheet_defines_semantic_roles(site_data, tmp_path):
    generator.generate(site_data, tmp_path)
    css = (tmp_path / "src" / "styles" / "global.css").read_text("utf-8")
    for token in ["--color-background", "--color-muted-foreground", "--color-ring"]:
        assert f"{token}:" in css


def test_stylesheet_respects_reduced_motion(site_data, tmp_path):
    generator.generate(site_data, tmp_path)
    css = (tmp_path / "src" / "styles" / "global.css").read_text("utf-8")
    assert "prefers-reduced-motion: reduce" in css
    # Smooth scrolling must be opt-in, never unconditional.
    assert "prefers-reduced-motion: no-preference" in css
    assert "scroll-padding-top" in css


def test_components_use_semantic_tokens_not_raw_palette_steps(site_data, tmp_path):
    generator.generate(site_data, tmp_path)
    for path in (tmp_path / "src").rglob("*.astro"):
        assert "slate-" not in path.read_text("utf-8"), f"{path} uses a raw palette step"


def test_templates_leave_no_unrendered_jinja(site_data, tmp_path):
    generator.generate(site_data, tmp_path)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert "{{" not in path.read_text("utf-8"), f"{path} has unrendered markup"


def test_refuses_a_non_empty_directory_without_force(site_data, tmp_path):
    (tmp_path / "keep.txt").write_text("mine", encoding="utf-8")
    with pytest.raises(generator.OutputExistsError):
        generator.generate(site_data, tmp_path)
    assert (tmp_path / "keep.txt").read_text("utf-8") == "mine"


def test_force_overwrites_a_non_empty_directory(site_data, tmp_path):
    (tmp_path / "keep.txt").write_text("mine", encoding="utf-8")
    generator.generate(site_data, tmp_path, force=True)
    assert (tmp_path / "package.json").is_file()


@pytest.mark.parametrize(
    "name,expected",
    [("Spoke & Chain", "spoke-chain"), ("  ???  ", "local-business-site")],
)
def test_project_slug_is_npm_safe(name, expected):
    assert generator.project_slug(name) == expected


def test_starter_yaml_is_valid_input():
    data, _ = build_site_data(yaml.safe_load(generator.starter_yaml()))
    assert data["business"]["name"] == "Rosewood Bakery"
