from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_codegraph(root: Path) -> Path | None:
    candidates = (
        root / ".tools/codegraph/node_modules/.bin/codegraph",
        root / ".tools/codegraph/node_modules/.bin/codegraph.cmd",
        root / ".tools/codegraph-standalone/v1.5.0/bin/codegraph",
        root
        / ".tools/codegraph-standalone/v1.5.0/codegraph-win32-x64/bin/codegraph.cmd",
        root
        / ".tools/codegraph-standalone/v1.5.0/codegraph-win32-arm64/bin/codegraph.cmd",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    found = shutil.which("codegraph")
    return Path(found) if found else None


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    executable = find_codegraph(root)
    if executable is None:
        print(
            "CodeGraph is optional and not installed. Run SETUP-CODEX or use filesystem search.",
            file=sys.stderr,
        )
        return 127
    command = [str(executable), "serve", "--mcp"]
    if os.name == "nt" and executable.suffix.lower() in {".cmd", ".bat"}:
        command = [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", *command]
    try:
        return subprocess.call(
            command,
            cwd=root,
        )
    except OSError as exc:
        print(f"CodeGraph failed to start: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
