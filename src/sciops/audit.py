from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from sciops.constants import ALLOWED_STAGE_STATUSES, REQUIRED_PATHS, STAGES

ALIGNMENT_SECTIONS = {
    "title",
    "abstract",
    "introduction",
    "methods",
    "results",
    "discussion",
    "conclusion",
    "declarations",
}
ALIGNMENT_BOOLEAN_FIELDS = {
    "claims_aligned",
    "numbers_units_aligned",
    "citations_aligned",
    "figures_tables_aligned",
    "scope_aligned",
}
MANUSCRIPT_SECTIONS = {
    "manuscript/en/paper.qmd": (
        "abstract",
        "introduction",
        "methods",
        "results",
        "discussion",
        "conclusion",
    ),
    "manuscript/zh/paper.qmd": ("摘要", "引言", "方法", "结果", "讨论", "结论"),
}


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


def _audit_bilingual_outputs(root: Path, result: AuditResult) -> None:
    alignment_path = root / "manuscript/bilingual-alignment.csv"
    try:
        with alignment_path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, csv.Error) as exc:
        result.errors.append(f"无法读取双语对齐表: {exc}")
        return

    by_section = {str(row.get("section", "")).strip().lower(): row for row in rows}
    for section in sorted(ALIGNMENT_SECTIONS):
        row = by_section.get(section)
        if row is None:
            result.errors.append(f"双语对齐表缺少章节: {section}")
            continue
        for language in ("zh_status", "en_status"):
            if str(row.get(language, "")).strip().lower() != "complete":
                result.errors.append(f"双语对齐未完成: {section}.{language}")
        for alignment_field in sorted(ALIGNMENT_BOOLEAN_FIELDS):
            if str(row.get(alignment_field, "")).strip().lower() != "true":
                result.errors.append(f"双语事实未对齐: {section}.{alignment_field}")
        if not str(row.get("verified_by", "")).strip():
            result.errors.append(f"双语对齐缺少核验人: {section}")
        if not str(row.get("verified_at", "")).strip():
            result.errors.append(f"双语对齐缺少核验日期: {section}")

    argument_path = root / "09_claim_evidence_map.md"
    try:
        lines = argument_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        result.errors.append(f"无法读取论证链: {exc}")
        return
    verified_chain = False
    required_cells = (2, 3, 4, 5, 6, 7, 9, 10, 11)
    for line in lines:
        if not line.lstrip().startswith("| C"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 13:
            continue
        if cells[12].lower() in {"complete", "verified"} and all(
            cells[index] for index in required_cells
        ):
            verified_chain = True
            break
    if not verified_chain:
        result.errors.append("G7 缺少完成核验的论点—证据—实验—作用—意义链")

    for relative, required_sections in MANUSCRIPT_SECTIONS.items():
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            result.errors.append(f"无法读取双语全文 {relative}: {exc}")
            continue
        visible_length = len("".join(character for character in text if not character.isspace()))
        if visible_length < 2_000:
            result.errors.append(f"G7 全文内容不足: {relative}")
        headings: list[tuple[int, int, str]] = []
        for index, line in enumerate(text.splitlines()):
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue
            marker, _, title = stripped.partition(" ")
            if marker and set(marker) == {"#"} and title:
                headings.append((index, len(marker), title.strip().lower()))
        lines = text.splitlines()
        for section in required_sections:
            match = next((item for item in headings if item[2] == section.lower()), None)
            if match is None:
                result.errors.append(f"G7 全文缺少章节: {relative}#{section}")
                continue
            start, level, _ = match
            end = next(
                (
                    index
                    for index, next_level, _ in headings
                    if index > start and next_level <= level
                ),
                len(lines),
            )
            content = "".join(
                line.strip()
                for line in lines[start + 1 : end]
                if line.strip()
                and not line.lstrip().startswith(("#", "<!--", "|", "```", "---"))
            )
            if len(content) < 80:
                result.errors.append(f"G7 章节内容不足: {relative}#{section}")


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

    if strict or result.stages.get("G7") == "passed":
        _audit_bilingual_outputs(root, result)

    if not strict:
        pending = [stage for stage, status in result.stages.items() if status != "passed"]
        if pending:
            result.warnings.append("尚未通过的阶段: " + ", ".join(pending))

    return result
