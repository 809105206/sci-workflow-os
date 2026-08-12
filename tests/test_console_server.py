from __future__ import annotations

import importlib.util
import json
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest


def _server_module():
    path = Path(__file__).parents[1] / "scripts/serve-console.py"
    spec = importlib.util.spec_from_file_location("sciops_console_server_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_local_credential_api_exports_and_blocks_cross_origin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _server_module()
    credentials = tmp_path / ".sciops-credentials.local.json"
    monkeypatch.setenv("SCIOPS_REPOSITORY_ROOT", str(tmp_path))
    monkeypatch.setenv("SCIOPS_CREDENTIALS_FILE", str(credentials))
    monkeypatch.setenv("OPENALEX_API_KEY", "test-openalex-value")
    monkeypatch.setenv("ZOTERO_LIBRARY_ID", "34567")
    monkeypatch.setenv("ZOTERO_LIBRARY_TYPE", "user")
    monkeypatch.setenv("ZOTERO_API_KEY", "test-zotero-value")

    handler = partial(module.ResearchConsoleHandler, directory=str(tmp_path))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urlopen(f"{origin}/api/credentials/status", timeout=5) as response:
            status_body = response.read().decode("utf-8")
        assert "test-openalex-value" not in status_body
        assert '"configured": true' in status_body

        forbidden = Request(
            f"{origin}/api/credentials/export",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(HTTPError) as error:
            urlopen(forbidden, timeout=5)
        assert error.value.code == 403

        allowed = Request(
            f"{origin}/api/credentials/export",
            data=b"{}",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Origin": origin,
                "X-Sciops-Local": "1",
            },
        )
        with urlopen(allowed, timeout=5) as response:
            payload = json.load(response)
            disposition = response.headers["Content-Disposition"]
        assert disposition.startswith("attachment;")
        assert payload["kind"] == "sciops-portable-credentials"
        assert payload["services"]["openalex"]["api_key"] == "test-openalex-value"
        assert credentials.stat().st_mode & 0o777 == 0o600
    finally:
        server.shutdown()
        server.server_close()
