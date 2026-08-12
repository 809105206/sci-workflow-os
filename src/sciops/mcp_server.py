from __future__ import annotations

import json
from pathlib import Path

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from sciops.chinese_sources import list_chinese_literature_sources
from sciops.credentials import load_runtime_credentials
from sciops.literature import (
    get_zotero_records,
    list_zotero_collections,
    prepare_candidate_previews,
    search_chinese_openalex,
)
from sciops.memory import compile_context, memory_health, search_memory
from sciops.onboarding import OnboardingError, active_project

load_runtime_credentials()

INSTRUCTIONS = (
    "Use this server for project-scoped research context and reusable Chinese-language "
    "scholarly discovery and citation metadata. "
    "OpenAlex tools are automated; CNKI, Wanfang, CQVIP and other licensed databases must be "
    "searched through the user's authorized access and imported through Zotero. Never claim a "
    "candidate record was read or supports a conclusion until the original text is verified."
)

mcp = MCPServer("SCI Workflow OS", instructions=INSTRUCTIONS)


def _selected_project() -> Path:
    selected, _ = active_project()
    if selected is None:
        raise OnboardingError("没有活动研究项目；先运行 sciops codex activate")
    return selected


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def current_research_context() -> dict[str, object]:
    """Return the bounded current-stage context for the active research project."""
    return compile_context(_selected_project())


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def research_memory_status() -> dict[str, object]:
    """Check active-project memory availability, integrity and capacity without exposing secrets."""
    return memory_health(_selected_project())


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def search_research_memory(query: str, limit: int = 20) -> list[dict[str, object]]:
    """Search all decisions and milestone events on demand without enlarging core context."""
    return search_memory(_selected_project(), query, limit=limit)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def list_chinese_sources() -> list[dict[str, str]]:
    """List maintained Chinese-journal search links, coverage, access and import routes."""
    return list_chinese_literature_sources()


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
def search_chinese_literature(
    query: str,
    limit: int = 20,
    from_year: int | None = None,
    to_year: int | None = None,
) -> list[dict[str, str | int | bool]]:
    """Search OpenAlex for Chinese-language scholarly records using a topic and year range."""
    return search_chinese_openalex(
        query,
        limit=limit,
        from_year=from_year,
        to_year=to_year,
    )


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
def preview_chinese_candidates(
    query: str,
    limit: int = 20,
    fetch_limit: int = 100,
    from_year: int | None = None,
    to_year: int | None = None,
    required_groups: list[str] | None = None,
    preferred_terms: list[str] | None = None,
    abstract_chars: int = 600,
) -> list[dict[str, str | int | bool]]:
    """Search and rank Chinese citation candidates without downloading article full text.

    Use comma-separated alternatives inside each required group. Every required group must
    match; preferred terms only influence ranking.
    """
    if limit < 1 or limit > 1_000:
        raise ValueError("limit 必须在 1 到 1000 之间")
    if fetch_limit < 1 or fetch_limit > 10_000:
        raise ValueError("fetch_limit 必须在 1 到 10000 之间")
    if fetch_limit < limit:
        raise ValueError("fetch_limit 不能小于 limit")
    records = search_chinese_openalex(
        query,
        limit=fetch_limit,
        from_year=from_year,
        to_year=to_year,
    )
    return prepare_candidate_previews(
        records,
        required_groups=required_groups or (),
        preferred_terms=preferred_terms or (),
        limit=limit,
        abstract_chars=abstract_chars,
    )


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
def zotero_collections() -> list[dict[str, str | int]]:
    """List collections in the configured Zotero library without exposing the API key."""
    return list_zotero_collections()


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
def zotero_collection_records(
    collection: str | None = None,
    limit: int = 100,
) -> list[dict[str, str | int | bool]]:
    """Read normalized top-level citation records from a Zotero collection or library."""
    return get_zotero_records(collection=collection, limit=limit)


@mcp.resource("sciops://chinese-literature/sources")
def chinese_sources_resource() -> str:
    """Machine-readable registry of Chinese scholarly search sources."""
    return json.dumps(list_chinese_literature_sources(), ensure_ascii=False, indent=2)


@mcp.resource("sciops://research/context")
def research_context_resource() -> str:
    """Machine-readable bounded context for the active research project."""
    return json.dumps(current_research_context(), ensure_ascii=False, indent=2)


@mcp.prompt()
def plan_chinese_literature_search(topic: str, discipline: str = "跨学科") -> str:
    """Create an auditable, database-independent Chinese literature search plan."""
    return f"""请为“{topic}”（学科：{discipline}）制定可复现的中文文献检索方案。

要求：
1. 将主题拆成研究对象、现象/结局、方法/机制、场景四个概念块；
2. 为每个概念块给出中文同义词、旧称、全称/缩写和必要英文词；
3. 从本服务器的中文来源目录选择通用库和学科专业库，分别记录完整检索式；
4. OpenAlex 中文过滤用于自动初检，知网/万方/维普等通过授权网页补检；
5. 每库记录日期、字段、时间范围、命中数、导出数和纳入数；
6. 题录进入 Zotero 后按 DOI、规范化标题、作者、年份和期刊人工复核重复项；
7. 只有阅读并核验原文后，才能把记录加入论证和正文引用。"""


def main() -> None:
    """Run the local stdio MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
