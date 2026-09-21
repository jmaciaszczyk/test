"""A local web UI for filling in a business and generating its website.

Runs on the standard library only and binds to the loopback interface, so the
form is reachable from this machine and nowhere else.
"""

from __future__ import annotations

import io
import json
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import yaml

from sitegen import generator
from sitegen.model import ConfigError, build_site_data

BUILDER_PAGE = Path(__file__).parent / "templates" / "builder.html"

# Far larger than any business description, small enough to refuse junk.
MAX_BODY_BYTES = 1 << 20

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def split_error(text: str) -> dict[str, str]:
    """Turn "business.name: is required" into a path and a message.

    The form uses the path to attach the message to the field that caused it.
    """
    path, separator, message = text.partition(": ")
    if not separator:
        return {"path": "", "message": text}
    return {"path": path, "message": message}


class BuilderHandler(BaseHTTPRequestHandler):
    server_version = "sitegen"

    def do_GET(self) -> None:  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        if self.path in ("/", "/index.html"):
            self._send_bytes(200, "text/html; charset=utf-8", BUILDER_PAGE.read_bytes())
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        routes = {
            "/api/validate": self._validate,
            "/api/yaml": self._yaml,
            "/api/generate": self._generate,
        }
        route = routes.get(self.path)
        if route is None:
            self._send_json(404, {"error": "not found"})
            return

        payload = self._read_json()
        if payload is None:
            return
        route(payload)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"  {self.command} {self.path}")

    def _read_json(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "invalid Content-Length"})
            return None
        if length > MAX_BODY_BYTES:
            self._send_json(413, {"error": "request too large"})
            return None

        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "invalid JSON"})
            return None
        if not isinstance(payload, dict):
            self._send_json(400, {"error": "expected an object"})
            return None
        return payload

    def _build(self, payload: dict) -> tuple[dict, list[str]] | None:
        """Validate, or answer with the field-level errors and stop."""
        try:
            return build_site_data(payload)
        except ConfigError as exc:
            self._send_json(
                422,
                {"ok": False, "errors": [split_error(item) for item in exc.errors]},
            )
            return None

    def _validate(self, payload: dict) -> None:
        built = self._build(payload)
        if built is None:
            return
        data, warnings = built
        self._send_json(
            200,
            {
                "ok": True,
                "errors": [],
                "warnings": warnings,
                "brand": data["brand"],
                "seo": data["seo"],
                "structuredData": data["structuredData"],
            },
        )

    def _yaml(self, payload: dict) -> None:
        if self._build(payload) is None:
            return
        text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
        self._send_bytes(
            200,
            "application/yaml; charset=utf-8",
            text.encode("utf-8"),
            filename="business.yaml",
        )

    def _generate(self, payload: dict) -> None:
        built = self._build(payload)
        if built is None:
            return
        data, _ = built
        slug = generator.project_slug(data["business"]["name"])

        with TemporaryDirectory() as workspace:
            site = Path(workspace) / "site"
            generator.generate(data, site)
            archive = io.BytesIO()
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                for path in sorted(site.rglob("*")):
                    if path.is_file():
                        bundle.write(path, f"{slug}/{path.relative_to(site).as_posix()}")

        self._send_bytes(
            200, "application/zip", archive.getvalue(), filename=f"{slug}.zip"
        )

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, "application/json; charset=utf-8", body)

    def _send_bytes(
        self, status: int, content_type: str, body: bytes, filename: str | None = None
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if filename:
            # project_slug only ever yields [a-z0-9-], so this is header-safe.
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    with ThreadingHTTPServer((host, port), BuilderHandler) as httpd:
        print(f"sitegen builder running at http://{host}:{port}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
