import asyncio

from mcp import Client

from sciops.mcp_server import mcp


def test_mcp_exposes_generic_chinese_literature_tools() -> None:
    async def inspect_server() -> tuple[set[str], list[dict[str, str]]]:
        async with Client(mcp) as client:
            tools = await client.list_tools()
            result = await client.call_tool("list_chinese_sources", {})
            return {tool.name for tool in tools.tools}, result.structured_content["result"]

    tool_names, sources = asyncio.run(inspect_server())

    assert {
        "list_chinese_sources",
        "search_chinese_literature",
        "preview_chinese_candidates",
        "zotero_collections",
        "zotero_collection_records",
        "current_research_context",
        "research_memory_status",
        "search_research_memory",
    } <= tool_names
    assert any(source["key"] == "cnki" for source in sources)
