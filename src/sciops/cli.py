from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from sciops.audit import audit_project
from sciops.data import DataValidationError, validate_csv
from sciops.doctor import run_checks
from sciops.literature import (
    append_bibtex,
    deduplicate_csv,
    pull_zotero_json,
    search_crossref,
    search_openalex,
    write_records,
)
from sciops.project import initialize_project, package_project

app = typer.Typer(no_args_is_help=True, help="SCI Workflow OS: G0-G10 可执行科研工作流")
literature_app = typer.Typer(no_args_is_help=True, help="联网文献检索、去重和引用")
zotero_app = typer.Typer(no_args_is_help=True, help="Zotero 文献库连接")
data_app = typer.Typer(no_args_is_help=True, help="研究数据质量检查")
app.add_typer(literature_app, name="literature")
app.add_typer(zotero_app, name="zotero")
app.add_typer(data_app, name="data")
console = Console()


@app.command()
def doctor() -> None:
    """检查本机依赖、GitHub 登录和可选联网凭据。"""
    table = Table(title="SCI Workflow OS doctor")
    table.add_column("组件")
    table.add_column("状态")
    table.add_column("详情")
    required_failed = False
    for check in run_checks():
        ok = "[green]OK[/green]" if check.ok else "[yellow]MISSING[/yellow]"
        table.add_row(check.name, ok, check.detail)
        required_failed = required_failed or (check.required and not check.ok)
    console.print(table)
    if required_failed:
        raise typer.Exit(1)


@app.command("init")
def init_project(
    destination: Annotated[Path, typer.Argument(help="新研究项目目录")],
    title: Annotated[str, typer.Option("--title", "-t", help="研究项目标题")],
    force: Annotated[bool, typer.Option(help="允许写入已有目录")] = False,
) -> None:
    """从 12 项最小工作包创建研究项目。"""
    try:
        created = initialize_project(destination, title=title, force=force)
    except (FileNotFoundError, FileExistsError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc
    console.print(f"[green]已创建[/green] {created}")


@app.command()
def audit(
    project: Annotated[Path, typer.Argument(help="研究项目目录")] = Path("."),
    strict: Annotated[bool, typer.Option(help="要求 G0-G10 全部 passed")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="输出 JSON")] = False,
) -> None:
    """检查工作包结构与 G0-G10 阶段状态。"""
    result = audit_project(project, strict=strict)
    if json_output:
        console.print_json(json.dumps(result.as_dict(), ensure_ascii=False))
    else:
        table = Table(title=f"G0-G10 audit: {result.root}")
        table.add_column("阶段")
        table.add_column("状态")
        for stage, status in result.stages.items():
            color = "green" if status == "passed" else "yellow"
            table.add_row(stage, f"[{color}]{status}[/{color}]")
        console.print(table)
        for warning in result.warnings:
            console.print(f"[yellow]WARN[/yellow] {warning}")
        for error in result.errors:
            console.print(f"[red]ERROR[/red] {error}")
        console.print("[green]PASS[/green]" if result.passed else "[red]FAIL[/red]")
    if not result.passed:
        raise typer.Exit(1)


@data_app.command("validate-csv")
def data_validate_csv(
    data: Annotated[Path, typer.Argument(help="待验证 CSV")],
    schema: Annotated[Path, typer.Argument(help="YAML schema")],
) -> None:
    """用 Pandera 和声明式 YAML schema 验证表格数据。"""
    try:
        result = validate_csv(data, schema)
    except (OSError, DataValidationError) as exc:
        console.print(f"[red]{exc}[/red]")
        if isinstance(exc, DataValidationError):
            for case in exc.failure_cases[:20]:
                console.print(f"[yellow]FAIL[/yellow] {case}")
        raise typer.Exit(2) from exc
    console.print(f"[green]PASS[/green] {result.rows} rows × {result.columns} columns")


@app.command("package")
def package(
    project: Annotated[Path, typer.Argument(help="要打包的研究项目")],
    output: Annotated[Path, typer.Option("--output", "-o", help="输出 ZIP")] = Path(
        "dist/research-package.zip"
    ),
    max_file_mib: Annotated[int, typer.Option(help="单文件大小上限")] = 100,
) -> None:
    """生成默认排除密钥、原始数据和模型权重的安全下载包。"""
    result = package_project(project, output, max_file_mib=max_file_mib)
    console.print(f"[green]已生成[/green] {result.output}")
    console.print(f"包含 {len(result.included)} 个文件；跳过 {len(result.skipped)} 个文件")
    for item in result.skipped[:20]:
        console.print(f"[yellow]SKIP[/yellow] {item}")


@literature_app.command("search")
def literature_search(
    query: Annotated[str, typer.Argument(help="OpenAlex 检索式")],
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, max=10_000)] = 50,
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("literature/openalex.csv"),
) -> None:
    """通过 OpenAlex 联网检索题录并导出 CSV。"""
    try:
        records = search_openalex(query, limit=limit)
        path = write_records(records, output)
    except Exception as exc:
        console.print(f"[red]OpenAlex 检索失败：{exc}[/red]")
        console.print("请设置 OPENALEX_API_KEY，并检查网络与检索式。")
        raise typer.Exit(2) from exc
    console.print(f"[green]已保存 {len(records)} 条记录[/green] {path}")
    console.print("引用前必须阅读原文并人工核验题录、结论、版本与许可。")


@literature_app.command("crossref-search")
def literature_crossref_search(
    query: Annotated[str, typer.Argument(help="Crossref 检索式")],
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, max=1_000)] = 50,
    output: Annotated[Path, typer.Option("--output", "-o")] = Path(
        "literature/crossref.csv"
    ),
) -> None:
    """无需 API key，通过 Crossref 联网检索题录并导出 CSV。"""
    try:
        records = search_crossref(query, limit=limit)
        path = write_records(records, output)
    except Exception as exc:
        console.print(f"[red]Crossref 检索失败：{exc}[/red]")
        raise typer.Exit(2) from exc
    console.print(f"[green]已保存 {len(records)} 条记录[/green] {path}")
    console.print("Crossref 覆盖范围与 OpenAlex 不同；引用前必须核验原文。")


@literature_app.command("dedupe")
def literature_dedupe(
    source: Annotated[Path, typer.Argument(help="输入 CSV")],
    output: Annotated[Path, typer.Argument(help="去重后 CSV")],
) -> None:
    """优先按 DOI、其次按规范化标题去重。"""
    try:
        path, before, after = deduplicate_csv(source, output)
    except (OSError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc
    console.print(f"[green]{before} → {after}[/green] {path}")


@literature_app.command("bibtex")
def literature_bibtex(
    doi: Annotated[str, typer.Argument(help="DOI")],
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("manuscript/references.bib"),
) -> None:
    """从 Crossref 获取单条 BibTeX，并在无重复时追加。"""
    try:
        path = append_bibtex(doi, output)
    except Exception as exc:
        console.print(f"[red]BibTeX 获取失败：{exc}[/red]")
        raise typer.Exit(2) from exc
    console.print(f"[green]已更新[/green] {path}")


@zotero_app.command("pull")
def zotero_pull(
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("literature/zotero.json"),
    collection: Annotated[str | None, typer.Option(help="可选 Zotero collection key")] = None,
) -> None:
    """从授权的 Zotero 库拉取 JSON 元数据。"""
    try:
        path, count = pull_zotero_json(output, collection=collection)
    except Exception as exc:
        console.print(f"[red]Zotero 拉取失败：{exc}[/red]")
        raise typer.Exit(2) from exc
    console.print(f"[green]已保存 {count} 条记录[/green] {path}")


if __name__ == "__main__":
    app()
