from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from sciops.project import repository_root


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _local_tool(name: str) -> Path | None:
    root = repository_root()
    candidates = {
        "gh": (root / ".tools/gh/gh",),
        "quarto": (root / ".tools/quarto/bin/quarto", root / ".tools/quarto/quarto/bin/quarto"),
    }
    for candidate in candidates.get(name, ()):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    found = shutil.which(name)
    return Path(found) if found else None


def _version(path: Path, *args: str) -> str:
    try:
        process = subprocess.run(
            [str(path), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return str(exc)
    line = (process.stdout or process.stderr).splitlines()
    return line[0].strip() if line else f"exit={process.returncode}"


def run_checks() -> list[Check]:
    checks = [
        Check("Python", sys.version_info >= (3, 11), sys.version.split()[0]),
    ]
    for name, required in (("git", True), ("uv", True), ("pandoc", False), ("quarto", False)):
        path = _local_tool(name)
        checks.append(
            Check(
                name,
                path is not None,
                _version(path, "--version") if path else "not found",
                required,
            )
        )

    gh = _local_tool("gh")
    checks.append(Check("gh", gh is not None, _version(gh, "--version") if gh else "not found"))
    if gh:
        auth = subprocess.run(
            [str(gh), "auth", "status"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        checks.append(
            Check(
                "GitHub auth",
                auth.returncode == 0,
                "authenticated" if auth.returncode == 0 else "not authenticated",
                False,
            )
        )

    checks.extend(
        [
            Check(
                "OpenAlex key",
                bool(os.getenv("OPENALEX_API_KEY", "").strip()),
                "configured" if os.getenv("OPENALEX_API_KEY", "").strip() else "not configured",
                False,
            ),
            Check(
                "Zotero credentials",
                bool(os.getenv("ZOTERO_LIBRARY_ID", "").strip()),
                "configured" if os.getenv("ZOTERO_LIBRARY_ID", "").strip() else "not configured",
                False,
            ),
        ]
    )
    return checks
