from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, find_dotenv, load_dotenv

LOCAL_CREDENTIALS_FILENAME = ".sciops-credentials.local.json"
SUPPORTED_CREDENTIALS = (
    "OPENALEX_EMAIL",
    "OPENALEX_API_KEY",
    "ZOTERO_LIBRARY_ID",
    "ZOTERO_LIBRARY_TYPE",
    "ZOTERO_API_KEY",
)


class CredentialError(RuntimeError):
    pass


def _repository_root() -> Path:
    override = os.getenv("SCIOPS_REPOSITORY_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def credentials_path() -> Path:
    override = os.getenv("SCIOPS_CREDENTIALS_FILE")
    if override:
        return Path(override).expanduser().resolve()
    return _repository_root() / LOCAL_CREDENTIALS_FILENAME


def _validate_payload(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise CredentialError("凭据 JSON 必须使用 schema_version=1")
    credentials = value.get("credentials")
    if not isinstance(credentials, dict):
        raise CredentialError("凭据 JSON 缺少 credentials 映射")
    unknown = sorted(set(credentials) - set(SUPPORTED_CREDENTIALS))
    if unknown:
        raise CredentialError(f"凭据 JSON 包含不受支持字段: {', '.join(unknown)}")
    normalized: dict[str, str] = {}
    for name, raw in credentials.items():
        if raw is None:
            continue
        if not isinstance(raw, str):
            raise CredentialError(f"字段 {name} 必须是字符串")
        value = raw.strip()
        if value:
            normalized[name] = value
    return normalized


def read_credentials(path: Path | None = None) -> dict[str, str]:
    source = (path or credentials_path()).expanduser().resolve()
    if not source.is_file():
        return {}
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CredentialError(f"无法读取凭据 JSON: {source.name}") from exc
    return _validate_payload(payload)


def load_runtime_credentials(*, override: bool = False) -> dict[str, str]:
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path, override=override)
    loaded: dict[str, str] = {}
    for name, value in read_credentials().items():
        if override or name not in os.environ:
            os.environ[name] = value
            loaded[name] = value
    return loaded


def credential_status() -> dict[str, Any]:
    path = credentials_path()
    stored = read_credentials(path)
    return {
        "path": str(path),
        "file_exists": path.is_file(),
        "configured": [name for name in SUPPORTED_CREDENTIALS if os.getenv(name, "").strip()],
        "stored": [name for name in SUPPORTED_CREDENTIALS if name in stored],
        "missing": [name for name in SUPPORTED_CREDENTIALS if not os.getenv(name, "").strip()],
    }


def _write_credentials(values: dict[str, str], destination: Path) -> Path:
    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "profile": "default",
        "credentials": {name: values[name] for name in SUPPORTED_CREDENTIALS if values.get(name)},
    }
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temporary.chmod(0o600)
        os.replace(temporary, destination)
        destination.chmod(0o600)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return destination


def export_dotenv_to_json(
    source: Path | None = None,
    destination: Path | None = None,
) -> Path:
    source = (source or (_repository_root() / ".env")).expanduser().resolve()
    if not source.is_file():
        raise CredentialError("未找到本机 .env")
    parsed = dotenv_values(source)
    values = {
        name: str(parsed[name]).strip()
        for name in SUPPORTED_CREDENTIALS
        if parsed.get(name) is not None and str(parsed[name]).strip()
    }
    if not values:
        raise CredentialError(".env 中没有受支持的非空凭据字段")
    return _write_credentials(values, destination or credentials_path())


def import_credentials(source: Path, destination: Path | None = None) -> Path:
    values = read_credentials(source)
    if not values:
        raise CredentialError("导入文件没有受支持的非空凭据字段")
    target = _write_credentials(values, destination or credentials_path())
    load_runtime_credentials()
    return target
