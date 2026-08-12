from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, find_dotenv, load_dotenv

LOCAL_CREDENTIALS_FILENAME = ".sciops-credentials.local.json"
CREDENTIAL_KIND = "sciops-portable-credentials"
CREDENTIAL_SCHEMA_VERSION = 2
MAX_CREDENTIAL_FILE_BYTES = 64 * 1024


@dataclass(frozen=True, slots=True)
class CredentialField:
    key: str
    env: str
    label: str
    secret: bool = False
    required: bool = False


@dataclass(frozen=True, slots=True)
class CredentialProvider:
    key: str
    label: str
    description: str
    fields: tuple[CredentialField, ...]


CREDENTIAL_PROVIDERS = (
    CredentialProvider(
        key="openalex",
        label="OpenAlex",
        description="文献检索、引文网络与开放获取元数据",
        fields=(
            CredentialField("email", "OPENALEX_EMAIL", "联系邮箱"),
            CredentialField("api_key", "OPENALEX_API_KEY", "API Key", secret=True, required=True),
        ),
    ),
    CredentialProvider(
        key="zotero",
        label="Zotero",
        description="个人或群组文献库的只读题录访问",
        fields=(
            CredentialField("library_id", "ZOTERO_LIBRARY_ID", "Library ID", required=True),
            CredentialField("library_type", "ZOTERO_LIBRARY_TYPE", "Library Type", required=True),
            CredentialField("api_key", "ZOTERO_API_KEY", "API Key", secret=True, required=True),
        ),
    ),
)

SUPPORTED_CREDENTIALS = tuple(
    field.env for provider in CREDENTIAL_PROVIDERS for field in provider.fields
)
_PROVIDER_BY_KEY = {provider.key: provider for provider in CREDENTIAL_PROVIDERS}
_PROFILE_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


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


def _profile(value: Any) -> str:
    profile = str(value or "default").strip()
    if not _PROFILE_PATTERN.fullmatch(profile):
        raise CredentialError("凭据 profile 仅允许字母、数字、点、下划线和连字符")
    return profile


def _normalize_legacy_payload(value: dict[str, Any]) -> tuple[str, dict[str, str]]:
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
        item = raw.strip()
        if item:
            normalized[name] = item
    return _profile(value.get("profile")), normalized


def _normalize_portable_payload(value: dict[str, Any]) -> tuple[str, dict[str, str]]:
    if value.get("kind") != CREDENTIAL_KIND:
        raise CredentialError(f"凭据 JSON 的 kind 必须是 {CREDENTIAL_KIND}")
    services = value.get("services")
    if not isinstance(services, dict):
        raise CredentialError("凭据 JSON 缺少 services 映射")
    unknown_services = sorted(set(services) - set(_PROVIDER_BY_KEY))
    if unknown_services:
        raise CredentialError(f"凭据 JSON 包含不受支持服务: {', '.join(unknown_services)}")
    normalized: dict[str, str] = {}
    for provider_key, raw_service in services.items():
        if not isinstance(raw_service, dict):
            raise CredentialError(f"服务 {provider_key} 必须是映射")
        provider = _PROVIDER_BY_KEY[provider_key]
        field_by_key = {field.key: field for field in provider.fields}
        unknown_fields = sorted(set(raw_service) - set(field_by_key))
        if unknown_fields:
            raise CredentialError(
                f"服务 {provider_key} 包含不受支持字段: {', '.join(unknown_fields)}"
            )
        for field_key, raw in raw_service.items():
            if raw is None:
                continue
            if not isinstance(raw, str):
                raise CredentialError(f"字段 {provider_key}.{field_key} 必须是字符串")
            item = raw.strip()
            if item:
                normalized[field_by_key[field_key].env] = item
    return _profile(value.get("profile")), normalized


def normalize_credential_payload(value: Any) -> tuple[str, dict[str, str]]:
    """Validate supported schema versions and return profile plus environment-style values."""
    if not isinstance(value, dict):
        raise CredentialError("凭据 JSON 顶层必须是对象")
    version = value.get("schema_version")
    if version == 1:
        return _normalize_legacy_payload(value)
    if version == CREDENTIAL_SCHEMA_VERSION:
        return _normalize_portable_payload(value)
    raise CredentialError("凭据 JSON 必须使用受支持的 schema_version")


def portable_credential_payload(
    values: dict[str, str], *, profile: str = "default"
) -> dict[str, Any]:
    services: dict[str, dict[str, str]] = {}
    for provider in CREDENTIAL_PROVIDERS:
        service = {
            field.key: str(values[field.env]).strip()
            for field in provider.fields
            if str(values.get(field.env, "")).strip()
        }
        if service:
            services[provider.key] = service
    return {
        "schema_version": CREDENTIAL_SCHEMA_VERSION,
        "kind": CREDENTIAL_KIND,
        "profile": _profile(profile),
        "services": services,
    }


def read_credential_payload(path: Path | None = None) -> dict[str, Any]:
    source = (path or credentials_path()).expanduser().resolve()
    if not source.is_file():
        return portable_credential_payload({})
    if source.stat().st_size > MAX_CREDENTIAL_FILE_BYTES:
        raise CredentialError("凭据 JSON 超过 64 KiB 上限")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CredentialError(f"无法读取凭据 JSON: {source.name}") from exc
    profile, values = normalize_credential_payload(payload)
    return portable_credential_payload(values, profile=profile)


def read_credentials(path: Path | None = None) -> dict[str, str]:
    source = (path or credentials_path()).expanduser().resolve()
    if not source.is_file():
        return {}
    if source.stat().st_size > MAX_CREDENTIAL_FILE_BYTES:
        raise CredentialError("凭据 JSON 超过 64 KiB 上限")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CredentialError(f"无法读取凭据 JSON: {source.name}") from exc
    _, values = normalize_credential_payload(payload)
    return values


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


def credential_catalog() -> list[dict[str, Any]]:
    return [
        {
            "key": provider.key,
            "label": provider.label,
            "description": provider.description,
            "fields": [
                {
                    "key": field.key,
                    "env": field.env,
                    "label": field.label,
                    "secret": field.secret,
                    "required": field.required,
                }
                for field in provider.fields
            ],
        }
        for provider in CREDENTIAL_PROVIDERS
    ]


def credential_status() -> dict[str, Any]:
    path = credentials_path()
    stored = read_credentials(path)
    catalog = credential_catalog()
    providers = []
    for index, provider in enumerate(CREDENTIAL_PROVIDERS):
        configured_fields = [
            field.key for field in provider.fields if os.getenv(field.env, "").strip()
        ]
        stored_fields = [field.key for field in provider.fields if field.env in stored]
        required = [field.key for field in provider.fields if field.required]
        providers.append(
            {
                "key": provider.key,
                "label": provider.label,
                "description": provider.description,
                "configured": all(field in configured_fields for field in required),
                "configured_fields": configured_fields,
                "stored_fields": stored_fields,
                "fields": catalog[index]["fields"],
            }
        )
    return {
        "path": str(path),
        "file_exists": path.is_file(),
        "schema_version": CREDENTIAL_SCHEMA_VERSION,
        "providers": providers,
        "configured": [name for name in SUPPORTED_CREDENTIALS if os.getenv(name, "").strip()],
        "stored": [name for name in SUPPORTED_CREDENTIALS if name in stored],
        "missing": [name for name in SUPPORTED_CREDENTIALS if not os.getenv(name, "").strip()],
    }


def _write_credentials(
    values: dict[str, str], destination: Path, *, profile: str = "default"
) -> Path:
    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = portable_credential_payload(values, profile=profile)
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


def runtime_credentials() -> dict[str, str]:
    """Collect only whitelisted configured values; never include arbitrary environment fields."""
    load_runtime_credentials()
    return {
        name: os.environ[name].strip()
        for name in SUPPORTED_CREDENTIALS
        if os.getenv(name, "").strip()
    }


def export_runtime_to_json(destination: Path | None = None, *, profile: str = "default") -> Path:
    values = runtime_credentials()
    if not values:
        raise CredentialError("当前环境没有受支持的非空凭据字段")
    return _write_credentials(values, destination or credentials_path(), profile=profile)


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


def import_credential_payload(
    payload: Any, destination: Path | None = None, *, merge: bool = True
) -> Path:
    profile, values = normalize_credential_payload(payload)
    if not values:
        raise CredentialError("导入文件没有受支持的非空凭据字段")
    target = (destination or credentials_path()).expanduser().resolve()
    if merge and target.is_file():
        values = {**read_credentials(target), **values}
    result = _write_credentials(values, target, profile=profile)
    for name, value in values.items():
        os.environ[name] = value
    return result


def import_credentials(
    source: Path, destination: Path | None = None, *, merge: bool = True
) -> Path:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise CredentialError("未找到待导入的凭据 JSON")
    if source.stat().st_size > MAX_CREDENTIAL_FILE_BYTES:
        raise CredentialError("凭据 JSON 超过 64 KiB 上限")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CredentialError("无法读取待导入的凭据 JSON") from exc
    return import_credential_payload(payload, destination, merge=merge)
