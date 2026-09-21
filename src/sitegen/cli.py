"""Command line interface for sitegen."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from sitegen import __version__, generator
from sitegen.model import ConfigError, build_site_data


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def _report(errors: list[str]) -> int:
    print("error: the input file has problems:", file=sys.stderr)
    for item in errors:
        print(f"  - {item}", file=sys.stderr)
    return 1


def _warn(warnings: list[str]) -> None:
    for item in warnings:
        print(f"warning: {item}", file=sys.stderr)


def _load(path: Path) -> tuple[dict, list[str]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return build_site_data(raw)


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.output)
    if target.exists() and not args.force:
        return _fail(f"{target} already exists; pass --force to overwrite it")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(generator.starter_yaml(), encoding="utf-8", newline="\n")
    print(f"Wrote {target}")
    print("Edit it with your business details, then run:")
    print(f"  sitegen build {target}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.input)
    if not path.is_file():
        return _fail(f"{path} does not exist")
    try:
        data, warnings = _load(path)
    except yaml.YAMLError as exc:
        return _fail(f"{path} is not valid YAML:\n{exc}")
    except ConfigError as exc:
        return _report(exc.errors)
    _warn(warnings)
    print(f"{path} looks good: {data['business']['name']}")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    path = Path(args.input)
    if not path.is_file():
        return _fail(f"{path} does not exist")
    try:
        data, warnings = _load(path)
    except yaml.YAMLError as exc:
        return _fail(f"{path} is not valid YAML:\n{exc}")
    except ConfigError as exc:
        return _report(exc.errors)
    _warn(warnings)

    out_dir = Path(args.output)
    try:
        written = generator.generate(data, out_dir, force=args.force)
    except generator.OutputExistsError as exc:
        return _fail(str(exc))

    print(f"Generated {len(written)} files in {out_dir}")
    print("Next steps:")
    print(f"  cd {out_dir}")
    print("  npm install")
    print("  npm run dev")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sitegen",
        description="Generate a starter Astro website for a local business.",
    )
    parser.add_argument("--version", action="version", version=f"sitegen {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="write a starter business.yaml to fill in")
    init.add_argument("output", nargs="?", default="business.yaml")
    init.add_argument("--force", action="store_true", help="overwrite an existing file")
    init.set_defaults(func=cmd_init)

    validate = subparsers.add_parser("validate", help="check an input file without building")
    validate.add_argument("input")
    validate.set_defaults(func=cmd_validate)

    build = subparsers.add_parser("build", help="generate the Astro project")
    build.add_argument("input")
    build.add_argument("-o", "--output", default="site", help="output directory (default: site)")
    build.add_argument("--force", action="store_true", help="overwrite a non-empty output directory")
    build.set_defaults(func=cmd_build)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
