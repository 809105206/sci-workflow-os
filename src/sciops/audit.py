from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from sciops.constants import ALLOWED_STAGE_STATUSES, REQUIRED_PATHS, STAGES


@dataclass(slots=True)
class AuditResult:
    root: Path
    strict: bool
    stages: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "strict": self.strict,
            "passed": self.passed,
            "stages": self.stages,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _load_stage_gates(path: Path, result: AuditResult) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        result.errors.append(f"无法读取阶段门文件 {path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        result.errors.append("stage-gates.yaml 顶层必须是映射")
        return {}
    stages = payload.get("stages", {})
    if not isinstance(stages, dict):
        result.errors.append("stage-gates.yaml 的 stages 必须是映射")
        return {}
    return stages


def audit_project(root: Path, *, strict: bool = False) -> AuditResult:
    root = root.expanduser().resolve()
    result = AuditResult(root=root, strict=strict)

    if not root.is_dir():
        result.errors.append(f"项目目录不存在: {root}")
        return result

    for relative in REQUIRED_PATHS:
        target = root / relative
        if not target.exists():
            result.errors.append(f"缺少必需文件: {relative.as_posix()}")
        elif target.is_file() and target.stat().st_size == 0:
            result.errors.append(f"文件为空: {relative.as_posix()}")

    gate_path = root / "stage-gates.yaml"
    if not gate_path.exists():
        return result

    stage_payload = _load_stage_gates(gate_path, result)
    for stage in STAGES:
        entry = stage_payload.get(stage)
        if not isinstance(entry, dict):
            result.errors.append(f"阶段门缺少或格式错误: {stage}")
            continue
        status = str(entry.get("status", "")).strip()
        result.stages[stage] = status or "missing"
        if status not in ALLOWED_STAGE_STATUSES:
            result.errors.append(f"{stage} 状态无效: {status or '<empty>'}")
        elif strict and status != "passed":
            result.errors.append(f"{stage} 尚未通过，当前状态: {status}")

        owner = str(entry.get("owner", "")).strip()
        evidence = entry.get("evidence", [])
        if strict and not owner:
            result.errors.append(f"{stage} 缺少 owner")
        if strict and (not isinstance(evidence, list) or not evidence):
            result.errors.append(f"{stage} 缺少 evidence")

    if not strict:
        pending = [stage for stage, status in result.stages.items() if status != "passed"]
        if pending:
            result.warnings.append("尚未通过的阶段: " + ", ".join(pending))

    return result
