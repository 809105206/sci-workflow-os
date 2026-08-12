from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from sciops.credentials import (
    CredentialError,
    export_dotenv_to_json,
    import_credentials,
    read_credentials,
)


def test_export_and_import_credentials_without_exposing_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / ".env"
    source.write_text(
        "OPENALEX_API_KEY=secret-openalex\n"
        "ZOTERO_LIBRARY_ID=12345\n"
        "ZOTERO_LIBRARY_TYPE=user\n"
        "ZOTERO_API_KEY=secret-zotero\n",
        encoding="utf-8",
    )
    destination = tmp_path / "credentials.json"
    exported = export_dotenv_to_json(source, destination)
    assert exported.stat().st_mode & 0o777 == 0o600
    assert read_credentials(exported)["ZOTERO_LIBRARY_ID"] == "12345"

    target = tmp_path / "imported.json"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SCIOPS_REPOSITORY_ROOT", str(tmp_path))
    monkeypatch.setenv("SCIOPS_CREDENTIALS_FILE", str(target))
    for name in (
        "OPENALEX_EMAIL",
        "OPENALEX_API_KEY",
        "ZOTERO_LIBRARY_ID",
        "ZOTERO_LIBRARY_TYPE",
        "ZOTERO_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    imported = import_credentials(exported, target)
    assert imported == target
    assert os.environ["OPENALEX_API_KEY"] == "secret-openalex"


def test_rejects_arbitrary_environment_fields(tmp_path: Path) -> None:
    source = tmp_path / "bad.json"
    source.write_text(
        json.dumps({"schema_version": 1, "credentials": {"PATH": "/unsafe"}}),
        encoding="utf-8",
    )
    with pytest.raises(CredentialError, match="不受支持"):
        read_credentials(source)
