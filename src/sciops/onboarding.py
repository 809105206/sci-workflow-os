from __future__ import annotations

import os
import shutil
import subprocess
import tomllib
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from sciops.audit import audit_project
from sciops.constants import STAGE_ARTIFACTS
from sciops.doctor import run_checks
from sciops.project import repository_root


class OnboardingError(RuntimeError):
    pass


def _read_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        if path.suffix == ".toml":
            with path.open("rb") as handle:
                value = tomllib.load(handle)
        else:
            value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, tomllib.TOMLDecodeError, yaml.YAMLError) as exc:
        raise OnboardingError(f"无法读取 {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise OnboardingError(f"{path.name} 顶层必须是映射")
    return value


def load_codex_policy() -> dict[str, Any]:
    root = repository_root()
    policy = _read_mapping(root / "codex-policy.toml")
    local = _read_mapping(root / ".sciops-local.toml")
    merged = dict(policy)
    for key, value in local.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def _is_research_project(path: Path) -> bool:
    return path.is_dir() and (path / "stage-gates.yaml").is_file()


def list_project_candidates() -> list[Path]:
    workspace = repository_root() / "workspace"
    if not workspace.is_dir():
        return []
    return sorted(
        (item.resolve() for item in workspace.iterdir() if _is_research_project(item)),
        key=lambda item: item.name.lower(),
    )


def active_project(explicit: Path | None = None) -> tuple[Path | None, list[Path]]:
    candidates = list_project_candidates()
    if explicit is not None:
        selected = explicit.expanduser().resolve()
        if not _is_research_project(selected):
            raise OnboardingError(f"不是 SCI Workflow OS 研究项目: {selected}")
        return selected, candidates

    pointer = repository_root() / ".sciops-active"
    if pointer.is_file():
        raw = pointer.read_text(encoding="utf-8").strip()
        if raw:
            selected = Path(raw).expanduser()
            if not selected.is_absolute():
                selected = repository_root() / selected
            selected = selected.resolve()
            if _is_research_project(selected):
                return selected, candidates

    if len(candidates) == 1:
        return candidates[0], candidates
    return None, candidates


def activate_project(project: Path) -> Path:
    selected = project.expanduser().resolve()
    if not _is_research_project(selected):
        raise OnboardingError(f"不是 SCI Workflow OS 研究项目: {selected}")
    root = repository_root()
    try:
        stored = selected.relative_to(root).as_posix()
    except ValueError:
        stored = str(selected)
    (root / ".sciops-active").write_text(f"{stored}\n", encoding="utf-8")
    return selected


def enable_trusted_mode() -> Path:
    target = repository_root() / ".sciops-local.toml"
    target.write_text(
        "schema_version = 1\n"
        'mode = "trusted"\n\n'
        "[automation]\n"
        "project_dependencies = true\n"
        "codegraph_index = true\n"
        "tests_and_builds = true\n"
        "system_packages = true\n",
        encoding="utf-8",
    )
    return target


def _codegraph_binary() -> Path | None:
    root = repository_root()
    candidates = (
        root / ".tools/codegraph/node_modules/.bin/codegraph",
        root / ".tools/codegraph/node_modules/.bin/codegraph.cmd",
        root / ".tools/codegraph/node_modules/@colbymchenry/codegraph/bin/codegraph",
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


def codegraph_status() -> dict[str, Any]:
    binary = _codegraph_binary()
    index = repository_root() / ".codegraph"
    result: dict[str, Any] = {
        "installed": binary is not None,
        "initialized": index.is_dir(),
        "binary": str(binary) if binary else None,
    }
    if not binary or not index.is_dir():
        return result
    try:
        command = [str(binary), "status"]
        if os.name == "nt" and binary.suffix.lower() in {".cmd", ".bat"}:
            command = [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", *command]
        process = subprocess.run(
            command,
            cwd=repository_root(),
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
            env={**os.environ, "NO_COLOR": "1"},
        )
        lines = (process.stdout or process.stderr).strip().splitlines()
        result["healthy"] = process.returncode == 0
        result["summary"] = " | ".join(lines[:4])
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["healthy"] = False
        result["summary"] = str(exc)
    return result


def build_resume_report(project: Path | None = None) -> dict[str, Any]:
    selected, candidates = active_project(project)
    checks = run_checks()
    environment = [
        {
            "name": check.name,
            "ok": check.ok,
            "detail": check.detail,
            "required": check.required,
        }
        for check in checks
    ]
    report: dict[str, Any] = {
        "repository": str(repository_root()),
        "policy": load_codex_policy(),
        "active_project": str(selected) if selected else None,
        "project_candidates": [str(item) for item in candidates],
        "environment": environment,
        "missing_required": [
            item["name"] for item in environment if item["required"] and not item["ok"]
        ],
        "codegraph": codegraph_status(),
    }
    if selected is None:
        report["status"] = "needs_project" if not candidates else "needs_project_selection"
        report["next_action"] = (
            "Create a project from the user's research direction."
            if not candidates
            else "Select and activate one candidate project."
        )
        return report

    state_path = selected / "research-state.yaml"
    state = _read_mapping(state_path)
    audit = audit_project(selected)
    first_incomplete = next(
        (stage for stage, status in audit.stages.items() if status != "passed"),
        "G10",
    )
    active_stage = str(state.get("active_stage") or first_incomplete)
    if audit.stages.get(active_stage) == "passed":
        active_stage = first_incomplete
    entry_files = [str(item) for item in state.get("entry_files", []) if str(item).strip()]
    if not entry_files:
        entry_files = [
            "research-state.yaml",
            "stage-gates.yaml",
            *(str(item) for item in STAGE_ARTIFACTS.get(active_stage, ())),
        ]
    next_actions = state.get("next_actions", [])
    if not next_actions:
        next_actions = [f"Review the evidence and exit criteria for {active_stage}."]
    last_completed = str(state.get("last_completed_action", ""))
    if not last_completed and not state_path.is_file():
        last_completed = (
            "Legacy project detected; persistent handoff state has not been recorded yet."
        )
    report.update(
        {
            "status": "ready" if not report["missing_required"] else "environment_incomplete",
            "active_stage": active_stage,
            "research_direction": str(state.get("research_direction", "")),
            "research_question": str(state.get("research_question", "")),
            "last_completed_action": last_completed,
            "decisions": state.get("decisions", []),
            "blockers": state.get("blockers", []),
            "next_actions": next_actions,
            "entry_files": [str(selected / item) for item in entry_files],
            "audit": audit.as_dict(),
        }
    )
    return report


def checkpoint_project(
    project: Path | None,
    *,
    completed: str,
    stage: str | None = None,
    next_actions: list[str] | None = None,
    decisions: list[str] | None = None,
    blockers: list[str] | None = None,
) -> Path:
    selected, _ = active_project(project)
    if selected is None:
        raise OnboardingError("没有活动研究项目")
    state_path = selected / "research-state.yaml"
    state = _read_mapping(state_path)
    state["schema_version"] = 1
    state["project"] = state.get("project") or selected.name
    state["updated_at"] = date.today().isoformat()
    state["last_completed_action"] = completed
    if stage:
        state["active_stage"] = stage
    if next_actions is not None:
        state["next_actions"] = next_actions
    if decisions:
        state["decisions"] = [*state.get("decisions", []), *decisions]
    if blockers is not None:
        state["blockers"] = blockers
    state_path.write_text(
        yaml.safe_dump(state, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return state_path
