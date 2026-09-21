import io
import json
import threading
import urllib.error
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer

import pytest
import yaml

from sitegen.server import BuilderHandler, split_error


@pytest.fixture
def base_url():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), BuilderHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def get(url):
    try:
        with urllib.request.urlopen(url) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read(), dict(error.headers)


def post(url, payload, raw=None):
    body = raw if raw is not None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read(), dict(error.headers)


VALID = {
    "business": {"name": "Spoke & Chain", "phone": "+44 20 7946 0812"},
    "brand": {"primary": "#1f6f5c"},
    "services": [{"name": "Puncture repair"}],
}


def test_split_error_separates_path_from_message():
    assert split_error("business.name: is required") == {
        "path": "business.name",
        "message": "is required",
    }


def test_split_error_handles_a_message_without_a_path():
    assert split_error("the input file is empty") == {
        "path": "",
        "message": "the input file is empty",
    }


def test_root_serves_the_builder_page(base_url):
    status, body, headers = get(base_url + "/")
    assert status == 200
    assert "text/html" in headers["Content-Type"]
    assert b"sitegen builder" in body


def test_unknown_path_is_not_found(base_url):
    assert get(base_url + "/secrets")[0] == 404


def test_validate_accepts_a_good_business(base_url):
    status, body, _ = post(base_url + "/api/validate", VALID)
    result = json.loads(body)
    assert status == 200
    assert result["ok"] is True
    assert result["brand"]["primaryRamp"]["500"] == "#1f6f5c"


def test_validate_reports_field_paths_for_errors(base_url):
    status, body, _ = post(base_url + "/api/validate", {"business": {}})
    result = json.loads(body)
    assert status == 422
    assert result["ok"] is False
    assert any(error["path"] == "business.name" for error in result["errors"])


def test_validate_passes_warnings_through(base_url):
    _, body, _ = post(base_url + "/api/validate", {"business": {"name": "Corner Barbers"}})
    assert json.loads(body)["warnings"]


def test_yaml_round_trips_to_the_same_business(base_url):
    status, body, headers = post(base_url + "/api/yaml", VALID)
    assert status == 200
    assert "business.yaml" in headers["Content-Disposition"]
    assert yaml.safe_load(body)["business"]["name"] == "Spoke & Chain"


def test_generate_returns_the_project_as_a_zip(base_url):
    status, body, headers = post(base_url + "/api/generate", VALID)
    assert status == 200
    assert headers["Content-Type"] == "application/zip"
    assert 'filename="spoke-chain.zip"' in headers["Content-Disposition"]

    with zipfile.ZipFile(io.BytesIO(body)) as bundle:
        names = bundle.namelist()
        assert "spoke-chain/package.json" in names
        assert "spoke-chain/src/pages/index.astro" in names
        business = json.loads(bundle.read("spoke-chain/src/data/business.json"))
        assert business["business"]["name"] == "Spoke & Chain"


def test_generate_refuses_an_invalid_business(base_url):
    status, body, _ = post(base_url + "/api/generate", {"business": {}})
    assert status == 422
    assert json.loads(body)["errors"]


def test_malformed_json_is_rejected(base_url):
    status, _, _ = post(base_url + "/api/validate", None, raw=b"{not json")
    assert status == 400


def test_a_json_array_is_rejected(base_url):
    status, _, _ = post(base_url + "/api/validate", None, raw=b"[1, 2, 3]")
    assert status == 400


def test_oversized_bodies_are_refused(base_url):
    oversized = json.dumps({"business": {"name": "x" * (1 << 21)}}).encode("utf-8")
    assert post(base_url + "/api/validate", None, raw=oversized)[0] == 413
