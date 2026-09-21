"""Render the Astro project templates into an output directory."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATE_ROOT = Path(__file__).parent / "templates"
PROJECT_TEMPLATES = TEMPLATE_ROOT / "project"
STARTER_FILE = TEMPLATE_ROOT / "starter.yaml"

# Pinned so a generated project installs a known-good toolchain.
DEPENDENCY_VERSIONS = {
    "astro": "^7.3.3",
    "tailwindcss": "^4.3.3",
    "@tailwindcss/vite": "^4.3.3",
}


class OutputExistsError(Exception):
    """Raised when the target directory already has files in it."""


def project_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "local-business-site"


def _output_name(name: str) -> str:
    if name.endswith(".j2"):
        name = name[: -len(".j2")]
    if name.startswith("dot-"):
        name = "." + name[len("dot-") :]
    return name


def starter_yaml() -> str:
    return STARTER_FILE.read_text(encoding="utf-8")


def generate(data: dict, out_dir: Path, *, force: bool = False) -> list[Path]:
    """Write the Astro project for ``data`` into ``out_dir``."""
    out_dir = Path(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()) and not force:
        raise OutputExistsError(
            f"{out_dir} is not empty; pass --force to overwrite its contents"
        )

    env = Environment(
        loader=FileSystemLoader(str(PROJECT_TEMPLATES)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )
    context = {
        **data,
        "slug": project_slug(data["business"]["name"]),
        "versions": DEPENDENCY_VERSIONS,
    }

    written: list[Path] = []
    for source in sorted(PROJECT_TEMPLATES.rglob("*")):
        if source.is_dir():
            continue
        relative = source.relative_to(PROJECT_TEMPLATES)
        destination = out_dir / relative.parent / _output_name(relative.name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix == ".j2":
            rendered = env.get_template(relative.as_posix()).render(context)
            destination.write_text(rendered, encoding="utf-8", newline="\n")
        else:
            shutil.copyfile(source, destination)
        written.append(destination)

    data_file = out_dir / "src" / "data" / "business.json"
    data_file.parent.mkdir(parents=True, exist_ok=True)
    data_file.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    written.append(data_file)

    return sorted(written)
