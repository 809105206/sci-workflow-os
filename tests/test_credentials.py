from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from sciops.credentials import (
    CREDENTIAL_KIND,
    CredentialError,
    export_dotenv_to_json,
    import_credential_payload,
    import_credentials,
    portable_credential_payload,
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
    payload = json.loads(exported.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 2
    assert payload["kind"] == CREDENTIAL_KIND
    assert payload["services"]["zotero"]["library_id"] == "12345"

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


def test_portable_schema_rejects_unknown_services_and_merges(tmp_path: Path) -> None:
    target = tmp_path / "credentials.json"
    first = portable_credential_payload({"OPENALEX_API_KEY": "oa-test"})
    import_credential_payload(first, target)
    second = portable_credential_payload(
        {
            "ZOTERO_LIBRARY_ID": "23456",
            "ZOTERO_LIBRARY_TYPE": "user",
            "ZOTERO_API_KEY": "zt-test",
        }
    )
    import_credential_payload(second, target, merge=True)
    values = read_credentials(target)
    assert values["OPENALEX_API_KEY"] == "oa-test"
    assert values["ZOTERO_API_KEY"] == "zt-test"

    invalid = {
        "schema_version": 2,
        "kind": CREDENTIAL_KIND,
        "profile": "default",
        "services": {"unknown": {"api_key": "unsafe"}},
    }
    with pytest.raises(CredentialError, match="不受支持服务"):
        import_credential_payload(invalid, target)
