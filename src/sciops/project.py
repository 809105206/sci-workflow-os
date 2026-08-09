from __future__ import annotations

import hashlib
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from sciops.constants import EXCLUDED_DIR_NAMES, SENSITIVE_NAMES


@dataclass(slots=True)
class PackageResult:
    output: Path
    included: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def repository_root() -> Path:
    override = os.getenv("SCIOPS_REPOSITORY_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def template_root() -> Path:
    return repository_root() / "templates" / "project"


def _replace_tokens(path: Path, replacements: dict[str, str]) -> None:
    if path.suffix.lower() not in {".md", ".qmd", ".yaml", ".yml", ".csv", ".bib"}:
        return
    text = path.read_text(encoding="utf-8")
    for token, value in replacements.items():
        text = text.replace(token, value)
    path.write_text(text, encoding="utf-8")


def initialize_project(destination: Path, *, title: str, force: bool = False) -> Path:
    source = template_root()
    if not source.is_dir():
        raise FileNotFoundError(f"模板目录不存在: {source}")

    destination = destination.expanduser().resolve()
    if destination.exists() and any(destination.iterdir()) and not force:
        raise FileExistsError(f"目标目录非空: {destination}")

    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, dirs_exist_ok=True)

    replacements = {
        "{{PROJECT_TITLE}}": title,
        "{{DATE}}": date.today().isoformat(),
    }
    for path in destination.rglob("*"):
        if path.is_file():
            _replace_tokens(path, replacements)

    for relative in (
        "literature",
        "data/raw",
        "data/interim",
        "data/processed",
        "notebooks",
        "outputs",
    ):
        folder = destination / relative
        folder.mkdir(parents=True, exist_ok=True)
        (folder / ".gitkeep").touch(exist_ok=True)

    return destination


def _should_skip(relative: Path, output: Path, source: Path) -> str | None:
    if len(relative.parts) > 1 and relative.parts[:2] in {
        (".dvc", "cache"),
        (".dvc", "tmp"),
    }:
        return "DVC runtime data"
    if any(part in EXCLUDED_DIR_NAMES for part in relative.parts[:-1]):
        return "excluded directory"
    env_variant = relative.name.startswith(".env.") and relative.name != ".env.example"
    if relative.name in SENSITIVE_NAMES or env_variant:
        return "sensitive filename"
    lowered = relative.name.lower()
    if any(token in lowered for token in ("secret", "credential", "private-key", "api-key")):
        return "potential secret"
    if relative.suffix.lower() in {".pt", ".pth", ".ckpt", ".key", ".pem"}:
        return "model or private-key asset"
    try:
        if (source / relative).resolve() == output.resolve():
            return "output archive"
    except FileNotFoundError:
        pass
    return None


def package_project(source: Path, output: Path, *, max_file_mib: int = 100) -> PackageResult:
    source = source.expanduser().resolve()
    output = output.expanduser().resolve()
    if not source.is_dir():
        raise NotADirectoryError(source)
    output.parent.mkdir(parents=True, exist_ok=True)

    result = PackageResult(output=output)
    manifest: list[str] = []
    max_bytes = max_file_mib * 1024 * 1024

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(source)
            reason = _should_skip(relative, output, source)
            if reason:
                result.skipped.append(f"{relative.as_posix()}: {reason}")
                continue
            if path.stat().st_size > max_bytes:
                result.skipped.append(f"{relative.as_posix()}: larger than {max_file_mib} MiB")
                continue
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            archive.writestr(relative.as_posix(), content)
            result.included.append(relative.as_posix())
            manifest.append(f"{digest}  {relative.as_posix()}")
        archive.writestr("MANIFEST.sha256", "\n".join(manifest) + "\n")

    return result
