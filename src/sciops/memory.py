from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

MEMORY_FILES = (
    Path("memory/policy.yaml"),
    Path("memory/working-context.yaml"),
    Path("memory/semantic.yaml"),
    Path("memory/events.jsonl"),
)

DEFAULT_LIMITS = {
    "context_chars": 12_000,
    "semantic_chars": 8_000,
    "recent_events": 8,
    "event_chars": 6_000,
}

SECRET_PATTERNS = (
    re.compile(r"(?i)(?:api[_-]?key|token|password|secret)\s*[:=]\s*\S+"),
    re.compile(r"(?i)\b(?:sk|ghp|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{12,}\b"),
)
INJECTION_PATTERNS = (
    re.compile(r"(?i)ignore (?:all |any )?(?:previous|prior) instructions"),
    re.compile(r"(?i)(?:system|developer)\s*(?:prompt|message|instructions?)"),
    re.compile(r"(?i)(?:exfiltrate|reveal|print|send).{0,40}(?:secret|token|api key|password)"),
)
INVISIBLE_PATTERN = re.compile("[\u202a-\u202e\u2066-\u2069\ufeff]")


class ResearchMemoryError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ResearchMemoryError(f"无法读取 {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ResearchMemoryError(f"{path.name} 顶层必须是映射")
    return value


def _write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _safe_text(value: str, *, label: str, max_chars: int) -> str:
    text = str(value).strip()
    if not text:
        raise ResearchMemoryError(f"{label} 不能为空")
    if len(text) > max_chars:
        raise ResearchMemoryError(f"{label} 超过 {max_chars} 字符")
    if INVISIBLE_PATTERN.search(text):
        raise ResearchMemoryError(f"{label} 包含不可见双向控制字符")
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        raise ResearchMemoryError(f"{label} 疑似包含凭据；长期记忆禁止保存密钥")
    configured_secrets = (
        os.getenv(name, "").strip() for name in ("OPENALEX_API_KEY", "ZOTERO_API_KEY")
    )
    if any(secret and len(secret) >= 8 and secret in text for secret in configured_secrets):
        raise ResearchMemoryError(f"{label} 包含已配置凭据；长期记忆禁止保存密钥")
    if any(pattern.search(text) for pattern in INJECTION_PATTERNS):
        raise ResearchMemoryError(f"{label} 疑似包含提示注入或数据外传指令")
    return text


def validate_memory_payload(value: Any, *, label: str = "内容") -> None:
    if isinstance(value, str):
        if not value.strip():
            return
        _safe_text(value, label=label, max_chars=6_000)
    elif isinstance(value, dict):
        for key, item in value.items():
            validate_memory_payload(item, label=f"{label}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            validate_memory_payload(item, label=f"{label}[{index}]")


def _stage_mapping(project: Path) -> dict[str, str]:
    gates = _read_yaml(project / "stage-gates.yaml")
    stages = gates.get("stages", {})
    if not isinstance(stages, dict):
        return {}
    return {
        str(stage): str(value.get("status", "pending"))
        for stage, value in stages.items()
        if isinstance(value, dict)
    }


def infer_active_stage(stages: dict[str, str], preferred: str = "") -> str:
    if preferred in stages and stages[preferred] != "passed":
        return preferred
    blocked = [stage for stage, status in stages.items() if status == "blocked"]
    if blocked:
        return max(blocked, key=lambda item: int(item.removeprefix("G") or 0))
    progressing = [stage for stage, status in stages.items() if status == "in_progress"]
    if progressing:
        return max(progressing, key=lambda item: int(item.removeprefix("G") or 0))
    return next((stage for stage, status in stages.items() if status != "passed"), "G10")


def _policy(project: Path) -> dict[str, Any]:
    value = _read_yaml(project / "memory/policy.yaml")
    limits = value.setdefault("limits", {})
    if not isinstance(limits, dict):
        limits = {}
        value["limits"] = limits
    for key, default in DEFAULT_LIMITS.items():
        limits.setdefault(key, default)
    return value


def read_events(project: Path) -> list[dict[str, Any]]:
    path = project / "memory/events.jsonl"
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ResearchMemoryError(f"events.jsonl 第 {number} 行损坏") from exc
        if not isinstance(value, dict):
            raise ResearchMemoryError(f"events.jsonl 第 {number} 行必须是对象")
        validate_memory_payload(value, label=f"events.jsonl[{number}]")
        records.append(value)
    return records


def record_event(
    project: Path,
    *,
    event_type: str,
    action: str,
    stage: str = "",
    artifacts: list[str] | None = None,
    next_actions: list[str] | None = None,
) -> dict[str, Any]:
    project = project.expanduser().resolve()
    action = _safe_text(action, label="事件动作", max_chars=2_000)
    event_type = _safe_text(event_type, label="事件类型", max_chars=80)
    validate_memory_payload(artifacts or [], label="事件文件")
    validate_memory_payload(next_actions or [], label="后续动作")
    events = read_events(project)
    event = {
        "id": f"E{len(events) + 1:06d}",
        "timestamp": _now(),
        "type": event_type,
        "stage": stage,
        "action": action,
        "artifacts": artifacts or [],
        "next_actions": next_actions or [],
    }
    if len(json.dumps(event, ensure_ascii=False)) > int(_policy(project)["limits"]["event_chars"]):
        raise ResearchMemoryError("单条事件超过 policy.yaml 的字符上限")
    path = project / "memory/events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def _working_from_project(project: Path) -> dict[str, Any]:
    state = _read_yaml(project / "research-state.yaml")
    stages = _stage_mapping(project)
    active_stage = infer_active_stage(stages, str(state.get("active_stage") or ""))
    gate_data = _read_yaml(project / "stage-gates.yaml").get("stages", {}).get(active_stage, {})
    if not isinstance(gate_data, dict):
        gate_data = {}
    blockers = [str(item) for item in state.get("blockers", []) if str(item).strip()]
    decision = str(gate_data.get("decision") or "").strip()
    if not blockers and str(gate_data.get("status")) == "blocked" and decision:
        blockers = [decision]
    next_actions = [str(item) for item in state.get("next_actions", []) if str(item).strip()]
    if not next_actions:
        if blockers:
            next_actions = [f"Resolve {active_stage} blocker: {blockers[0]}"]
        else:
            next_actions = [f"Review the evidence and exit criteria for {active_stage}."]
    entry_files = [str(item) for item in state.get("entry_files", []) if str(item).strip()]
    defaults = ["research-state.yaml", "memory/working-context.yaml", "stage-gates.yaml"]
    evidence = [str(item) for item in gate_data.get("evidence", []) if str(item).strip()]
    files = list(dict.fromkeys([*defaults, *entry_files, *evidence]))
    return {
        "schema_version": 1,
        "updated_at": _now(),
        "project": str(state.get("project") or project.name),
        "objective": str(state.get("research_direction") or state.get("project") or project.name),
        "active_stage": active_stage,
        "stage_status": stages.get(active_stage, "pending"),
        "last_completed_action": str(state.get("last_completed_action") or ""),
        "next_actions": next_actions,
        "blockers": blockers,
        "working_set": {"files": files, "semantic_ids": [], "evidence_ids": []},
    }


def _import_semantic_items(project: Path) -> list[dict[str, Any]]:
    state = _read_yaml(project / "research-state.yaml")
    decisions = [str(item).strip() for item in state.get("decisions", []) if str(item).strip()]
    if not decisions:
        gates = _read_yaml(project / "stage-gates.yaml").get("stages", {})
        if isinstance(gates, dict):
            for stage, value in gates.items():
                if isinstance(value, dict) and str(value.get("decision") or "").strip():
                    decisions.append(f"{stage}: {value['decision']}")
    now = _now()
    items = []
    for index, statement in enumerate(decisions, start=1):
        stage_match = re.match(r"^(G\d+):", statement)
        items.append(
            {
                "id": f"M{index:04d}",
                "kind": "decision",
                "statement": statement,
                "status": "active",
                "scope": "project",
                "stage": stage_match.group(1) if stage_match else "",
                "rationale": "Imported from auditable project state.",
                "sources": ["research-state.yaml"],
                "created_at": now,
                "updated_at": now,
            }
        )
    return items


def ensure_project_memory(project: Path) -> dict[str, str]:
    project = project.expanduser().resolve()
    if not (project / "stage-gates.yaml").is_file():
        raise ResearchMemoryError(f"不是研究项目: {project}")
    memory = project / "memory"
    memory.mkdir(parents=True, exist_ok=True)
    policy_path = memory / "policy.yaml"
    if not policy_path.is_file():
        _write_yaml(
            policy_path,
            {
                "schema_version": 1,
                "limits": dict(DEFAULT_LIMITS),
                "retention": {
                    "raw_chat": False,
                    "credentials": False,
                    "superseded_decisions": True,
                },
            },
        )
    working_path = memory / "working-context.yaml"
    if not working_path.is_file():
        _write_yaml(working_path, _working_from_project(project))
    semantic_path = memory / "semantic.yaml"
    if not semantic_path.is_file():
        _write_yaml(semantic_path, {"schema_version": 1, "items": _import_semantic_items(project)})
    events_path = memory / "events.jsonl"
    if not events_path.is_file():
        events_path.touch()
        working = _read_yaml(working_path)
        record_event(
            project,
            event_type="memory_initialized",
            stage=str(working.get("active_stage") or ""),
            action="Project memory initialized from auditable project files.",
            artifacts=[str(item) for item in MEMORY_FILES],
            next_actions=[str(item) for item in working.get("next_actions", [])],
        )
    return {item.name: str(project / item) for item in MEMORY_FILES}


def _semantic_items(project: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    value = _read_yaml(project / "memory/semantic.yaml")
    items = value.get("items", [])
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise ResearchMemoryError("semantic.yaml 的 items 必须是对象列表")
    validate_memory_payload(items, label="semantic.yaml.items")
    return value, items


def remember(
    project: Path,
    statement: str,
    *,
    kind: str = "decision",
    status: str | None = None,
    scope: str = "project",
    stage: str = "",
    rationale: str = "",
    sources: list[str] | None = None,
    supersedes: str = "",
) -> dict[str, Any]:
    project = project.expanduser().resolve()
    ensure_project_memory(project)
    if kind not in {"decision", "fact", "constraint", "lesson"}:
        raise ResearchMemoryError("kind 必须是 decision、fact、constraint 或 lesson")
    statement = _safe_text(statement, label="记忆陈述", max_chars=2_000)
    if rationale:
        rationale = _safe_text(rationale, label="记忆理由", max_chars=2_000)
    scope = _safe_text(scope, label="记忆作用域", max_chars=100)
    if stage:
        stage = _safe_text(stage, label="记忆阶段", max_chars=20)
    sources = [
        _safe_text(item, label="记忆来源", max_chars=500)
        for item in (sources or [])
        if item.strip()
    ]
    item_status = status or ("verified" if kind == "fact" and sources else "active")
    if item_status not in {"active", "verified", "candidate", "superseded", "rejected"}:
        raise ResearchMemoryError("无效记忆状态")
    if kind == "fact" and item_status == "verified" and not sources:
        raise ResearchMemoryError("verified fact 必须提供来源")
    semantic, items = _semantic_items(project)
    now = _now()
    item = {
        "id": f"M{len(items) + 1:04d}",
        "kind": kind,
        "statement": statement,
        "status": item_status,
        "scope": scope,
        "stage": stage,
        "rationale": rationale,
        "sources": sources,
        "created_at": now,
        "updated_at": now,
    }
    if supersedes:
        prior = next((record for record in items if record.get("id") == supersedes), None)
        if prior is None:
            raise ResearchMemoryError(f"未找到被替代条目 {supersedes}")
        prior["status"] = "superseded"
        prior["superseded_by"] = item["id"]
        prior["updated_at"] = now
        item["supersedes"] = supersedes
    projected = len(yaml.safe_dump([*items, item], allow_unicode=True))
    limit = int(_policy(project)["limits"]["semantic_chars"])
    if projected > limit:
        raise ResearchMemoryError("长期记忆已达容量上限；请先合并或替代旧条目")
    items.append(item)
    semantic["items"] = items
    _write_yaml(project / "memory/semantic.yaml", semantic)
    return item


def memory_health(project: Path) -> dict[str, Any]:
    project = project.expanduser().resolve()
    missing = [str(item) for item in MEMORY_FILES if not (project / item).is_file()]
    if missing:
        return {
            "available": False,
            "ok": False,
            "missing": missing,
            "problems": [],
        }
    problems: list[str] = []
    try:
        policy = _policy(project)
        validate_memory_payload(
            _read_yaml(project / "memory/working-context.yaml"),
            label="working-context.yaml",
        )
        _, items = _semantic_items(project)
        events = read_events(project)
        semantic_chars = len(yaml.safe_dump(items, allow_unicode=True))
    except ResearchMemoryError as exc:
        problems.append(str(exc))
        policy = {"limits": dict(DEFAULT_LIMITS)}
        items = []
        events = []
        semantic_chars = 0
    return {
        "available": True,
        "ok": not problems,
        "missing": [],
        "problems": problems,
        "semantic_items": len(items),
        "active_semantic_items": sum(
            item.get("status") in {"active", "verified"} for item in items
        ),
        "semantic_chars": semantic_chars,
        "semantic_char_limit": int(policy["limits"]["semantic_chars"]),
        "events": len(events),
        "context_budget_chars": int(policy["limits"]["context_chars"]),
    }


def compile_context(project: Path) -> dict[str, Any]:
    project = project.expanduser().resolve()
    ensure_project_memory(project)
    working = _working_from_project(project)
    _write_yaml(project / "memory/working-context.yaml", working)
    _, items = _semantic_items(project)
    semantic = [item for item in items if item.get("status") in {"active", "verified"}]
    policy = _policy(project)
    recent_limit = int(policy["limits"]["recent_events"])
    events = read_events(project)[-recent_limit:]
    gate_data = (
        _read_yaml(project / "stage-gates.yaml").get("stages", {}).get(working["active_stage"], {})
    )
    bundle: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": _now(),
        "project": working["project"],
        "project_path": str(project),
        "objective": working["objective"],
        "active_stage": working["active_stage"],
        "stage_status": working["stage_status"],
        "last_completed_action": working["last_completed_action"],
        "next_action": working["next_actions"][0],
        "next_actions": working["next_actions"],
        "blockers": working["blockers"],
        "stop_condition": "Do not advance the stage until its evidence and exit criteria pass.",
        "gate": gate_data if isinstance(gate_data, dict) else {},
        "working_set": working["working_set"],
        "semantic_memory": semantic,
        "recent_events": events,
        "read_priority": [str(project / item) for item in working["working_set"]["files"]],
        "integrity_rules": [
            "Project files outrank chat recollection and generated summaries.",
            "Candidate or abstract-only evidence cannot support manuscript claims.",
            "Do not store raw chat, credentials, or unverified claims as durable facts.",
            "Supersede outdated decisions; preserve their audit trail.",
        ],
    }
    limit = int(policy["limits"]["context_chars"])
    omitted_events = 0
    omitted_semantic = 0
    while len(json.dumps(bundle, ensure_ascii=False)) > limit and bundle["recent_events"]:
        bundle["recent_events"].pop(0)
        omitted_events += 1
    while len(json.dumps(bundle, ensure_ascii=False)) > limit and bundle["semantic_memory"]:
        bundle["semantic_memory"].pop(0)
        omitted_semantic += 1
    used = len(json.dumps(bundle, ensure_ascii=False))
    if used > limit:
        raise ResearchMemoryError("核心课题状态超过上下文预算；请精简 research-state.yaml")
    bundle["budget"] = {
        "limit_chars": limit,
        "used_chars": used,
        "truncated": bool(omitted_events or omitted_semantic),
        "omitted_events": omitted_events,
        "omitted_semantic_items": omitted_semantic,
    }
    return bundle


def search_memory(project: Path, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    project = project.expanduser().resolve()
    query = _safe_text(query, label="检索词", max_chars=500).lower()
    _, semantic_items = _semantic_items(project)
    records = [{"memory_type": "semantic", **item} for item in semantic_items] + [
        {"memory_type": "event", **item} for item in read_events(project)
    ]
    terms = [item for item in re.split(r"\s+", query) if item]
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for record in records:
        text = json.dumps(record, ensure_ascii=False).lower()
        score = (100 if query in text else 0) + sum(10 for term in terms if term in text)
        if score:
            updated_at = str(record.get("updated_at") or record.get("timestamp") or "")
            ranked.append((score, updated_at, record))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [{"score": score, **record} for score, _, record in ranked[:limit]]


def update_checkpoint_memory(
    project: Path,
    *,
    completed: str,
    stage: str,
    next_actions: list[str],
    decisions: list[str],
) -> None:
    ensure_project_memory(project)
    working = _working_from_project(project)
    _write_yaml(project / "memory/working-context.yaml", working)
    for decision in decisions:
        remember(
            project,
            decision,
            kind="decision",
            stage=stage,
            rationale="Recorded by sciops codex checkpoint.",
            sources=["research-state.yaml"],
        )
    record_event(
        project,
        event_type="checkpoint",
        stage=stage,
        action=completed,
        artifacts=["research-state.yaml", "memory/working-context.yaml"],
        next_actions=next_actions,
    )
