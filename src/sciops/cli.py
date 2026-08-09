from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from dotenv import find_dotenv, load_dotenv
from rich.console import Console
from rich.table import Table

from sciops.audit import audit_project
from sciops.chinese_sources import list_chinese_literature_sources
from sciops.data import DataValidationError, validate_csv
from sciops.doctor import run_checks
from sciops.figures import FigureError, available_backends, load_figure_spec, render_figure
from sciops.literature import (
    append_bibtex,
    deduplicate_csv,
    list_zotero_collections,
    merge_csv,
    preview_csv,
    pull_zotero_csl_json,
    pull_zotero_csv,
    pull_zotero_json,
    search_chinese_openalex,
    search_crossref,
    search_openalex,
    write_records,
)
from sciops.onboarding import (
    OnboardingError,
    activate_project,
    build_resume_report,
    checkpoint_project,
    enable_trusted_mode,
)
from sciops.project import initialize_project, package_project
from sciops.writing import lint_manuscript

dotenv_path = find_dotenv(usecwd=True)
if dotenv_path:
    load_dotenv(dotenv_path)

app = typer.Typer(no_args_is_help=True, help="SCI Workflow OS: G0-G10 可执行科研工作流")
literature_app = typer.Typer(no_args_is_help=True, help="联网文献检索、去重和引用")
zotero_app = typer.Typer(no_args_is_help=True, help="Zotero 文献库连接")
data_app = typer.Typer(no_args_is_help=True, help="研究数据质量检查")
writing_app = typer.Typer(no_args_is_help=True, help="陈述句、证据与相关性写作质量门")
figure_app = typer.Typer(no_args_is_help=True, help="OriginPro 与开放后端科研图表")
codex_app = typer.Typer(no_args_is_help=True, help="Codex 项目接管、恢复与交接")
app.add_typer(literature_app, name="literature")
app.add_typer(zotero_app, name="zotero")
app.add_typer(data_app, name="data")
app.add_typer(writing_app, name="writing")
app.add_typer(figure_app, name="figure")
app.add_typer(codex_app, name="codex")
console = Console()


@codex_app.command("resume")
def codex_resume(
    project: Annotated[
        Path | None,
        typer.Argument(help="研究项目目录；省略时使用活动项目"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="输出机器可读 JSON")] = False,
) -> None:
    """生成最小接管上下文，避免重新扫描整个仓库。"""
    try:
        report = build_resume_report(project)
    except OnboardingError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc
    if json_output:
        console.print_json(json.dumps(report, ensure_ascii=False))
        return
    console.print(f"[bold]状态[/bold] {report['status']}")
    console.print(f"[bold]活动项目[/bold] {report['active_project'] or '未选择'}")
    if report.get("active_stage"):
        console.print(f"[bold]当前阶段[/bold] {report['active_stage']}")
    for action in report.get("next_actions", [report.get("next_action")]):
        if action:
            console.print(f"[cyan]NEXT[/cyan] {action}")


@codex_app.command("activate")
def codex_activate(project: Annotated[Path, typer.Argument(help="要设为活动项目的目录")]) -> None:
    """设置下次 Codex 会话自动恢复的研究项目。"""
    try:
        selected = activate_project(project)
    except OnboardingError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc
    console.print(f"[green]活动项目[/green] {selected}")


@codex_app.command("trust")
def codex_trust(
    confirmed: Annotated[bool, typer.Option("--yes", help="确认启用本机可信自动化")] = False,
) -> None:
    """为本机启用可信模式；配置文件不会提交或打包。"""
    if not confirmed:
        console.print("[yellow]需要 --yes 明确确认。[/yellow]")
        raise typer.Exit(2)
    target = enable_trusted_mode()
    console.print(f"[green]已启用 trusted 模式[/green] {target}")
    console.print("平台权限、凭据、外部发布和不可逆操作仍受确认边界约束。")


@codex_app.command("checkpoint")
def codex_checkpoint(
    completed: Annotated[str, typer.Option("--completed", help="本次完成的可核验动作")],
    project: Annotated[Path | None, typer.Option("--project", help="研究项目目录")] = None,
    stage: Annotated[str | None, typer.Option("--stage", help="下一活动阶段，如 G2")] = None,
    next_action: Annotated[
        list[str] | None,
        typer.Option("--next", help="有序下一动作，可重复"),
    ] = None,
    decision: Annotated[
        list[str] | None,
        typer.Option("--decision", help="新增决策，可重复"),
    ] = None,
    blocker: Annotated[
        list[str] | None,
        typer.Option("--blocker", help="当前阻塞，可重复；不传则保留"),
    ] = None,
) -> None:
    """写入可跨会话恢复的研究交接状态。"""
    try:
        target = checkpoint_project(
            project,
            completed=completed,
            stage=stage,
            next_actions=next_action,
            decisions=decision,
            blockers=blocker,
        )
    except OnboardingError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc
    console.print(f"[green]已更新交接状态[/green] {target}")


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
    """从通用 G0-G10 方法论和双语工作包创建研究项目。"""
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


@writing_app.command("lint")
def writing_lint(
    manuscript: Annotated[Path, typer.Argument(help="Markdown 或 Quarto 稿件")],
    strict: Annotated[bool, typer.Option(help="警告也阻断通过")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="输出 JSON")] = False,
) -> None:
    """检查疑问句、对话式元话语、占位符、空泛强化与模板化表达。"""
    try:
        result = lint_manuscript(manuscript, strict=strict)
    except OSError as exc:
        console.print(f"[red]稿件读取失败：{exc}[/red]")
        raise typer.Exit(2) from exc
    if json_output:
        console.print_json(json.dumps(result.as_dict(), ensure_ascii=False))
    else:
        table = Table(title=f"Writing gate · {result.source.name}")
        table.add_column("级别")
        table.add_column("行")
        table.add_column("规则")
        table.add_column("命中")
        table.add_column("修订要求")
        for issue in result.issues:
            color = "red" if issue.severity == "error" else "yellow"
            table.add_row(
                f"[{color}]{issue.severity.upper()}[/{color}]",
                str(issue.line),
                issue.rule,
                issue.match,
                issue.message,
            )
        console.print(table)
        console.print(
            f"规范分 {result.score}；{result.errors} errors；{result.warnings} warnings"
        )
        console.print("[green]PASS[/green]" if result.passed else "[red]FAIL[/red]")
    if not result.passed:
        raise typer.Exit(1)


@figure_app.command("doctor")
def figure_doctor() -> None:
    """检查 OriginPro、Matplotlib 与 Plotly 渲染后端。"""
    table = Table(title="Figure backends")
    table.add_column("后端")
    table.add_column("状态")
    table.add_column("说明")
    for name, item in available_backends().items():
        status = "[green]OK[/green]" if item["available"] else "[yellow]UNAVAILABLE[/yellow]"
        table.add_row(name, status, str(item["detail"]))
    console.print(table)


@figure_app.command("render")
def figure_render(
    specification: Annotated[Path, typer.Argument(help="YAML 图形规范")],
    backend: Annotated[
        str,
        typer.Option(help="auto、origin、matplotlib 或 plotly"),
    ] = "auto",
    project: Annotated[
        Path | None,
        typer.Option("--project", help="可选 Origin OPJU 项目路径"),
    ] = None,
) -> None:
    """用统一规范生成投稿图表；Origin 不可用时可复现地回退到开放后端。"""
    try:
        spec = load_figure_spec(specification)
        selected, outputs = render_figure(spec, backend=backend, project=project)
    except (OSError, FigureError) as exc:
        console.print(f"[red]图表生成失败：{exc}[/red]")
        raise typer.Exit(2) from exc
    console.print(f"[green]已使用 {selected} 生成 {len(outputs)} 个文件[/green]")
    for output in outputs:
        console.print(output)


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


@literature_app.command("search-cn")
def literature_search_cn(
    query: Annotated[str, typer.Argument(help="中文主题或中文检索式")],
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, max=10_000)] = 50,
    from_year: Annotated[int | None, typer.Option("--from-year", min=1000, max=2100)] = None,
    to_year: Annotated[int | None, typer.Option("--to-year", min=1000, max=2100)] = None,
    output: Annotated[Path, typer.Option("--output", "-o")] = Path(
        "literature/openalex-zh.csv"
    ),
) -> None:
    """通过 OpenAlex 的中文语言过滤检索题录并导出标准 CSV。"""
    try:
        records = search_chinese_openalex(
            query,
            limit=limit,
            from_year=from_year,
            to_year=to_year,
        )
        path = write_records(records, output)
    except Exception as exc:
        console.print(f"[red]OpenAlex 中文检索失败：{exc}[/red]")
        console.print("请设置 OPENALEX_API_KEY，并检查网络、年份和检索式。")
        raise typer.Exit(2) from exc
    console.print(f"[green]已保存 {len(records)} 条中文记录[/green] {path}")
    console.print("语言标注可能不完整；仍需在中文专业库补检，并回到原文核验。")


@literature_app.command("preview")
def literature_preview(
    source: Annotated[Path, typer.Argument(help="OpenAlex、Zotero 或合并后的标准 CSV")],
    required: Annotated[
        list[str] | None,
        typer.Option(
            "--require",
            help="必含概念组；组内逗号表示 OR，可重复指定以表达 AND",
        ),
    ] = None,
    preferred: Annotated[
        list[str] | None,
        typer.Option("--prefer", help="排序偏好词；逗号表示 OR，可重复指定"),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, max=1_000)] = 20,
    abstract_chars: Annotated[
        int,
        typer.Option("--abstract-chars", min=80, max=10_000, help="每条摘要预览字符数"),
    ] = 600,
    output: Annotated[Path, typer.Option("--output", "-o", help="Markdown 候选预览")] = Path(
        "literature/chinese-candidate-preview.md"
    ),
    decisions: Annotated[
        Path,
        typer.Option("--decisions", help="可编辑的下载决策 CSV"),
    ] = Path("literature/chinese-download-decisions.csv"),
) -> None:
    """只用题名、引用地址和摘要生成候选预览，不下载全文。"""
    try:
        preview_path, decisions_path, count = preview_csv(
            source,
            output,
            decisions,
            required_groups=required or (),
            preferred_terms=preferred or (),
            limit=limit,
            abstract_chars=abstract_chars,
        )
    except (OSError, ValueError) as exc:
        console.print(f"[red]候选预览生成失败：{exc}[/red]")
        raise typer.Exit(2) from exc
    console.print(f"[green]已生成 {count} 条候选[/green] {preview_path}")
    console.print(f"[green]下载决策表[/green] {decisions_path}")
    console.print("先把 decision 改为 下载/跳过/稍后；只有读取原文后才能进入正式引用。")


@literature_app.command("chinese-sources")
def literature_chinese_sources(
    json_output: Annotated[bool, typer.Option("--json", help="输出 JSON")] = False,
) -> None:
    """列出跨学科中文期刊检索入口、访问方式和导入路径。"""
    sources = list_chinese_literature_sources()
    if json_output:
        console.print_json(json.dumps(sources, ensure_ascii=False))
        return
    table = Table(title="中文文献检索来源")
    table.add_column("来源")
    table.add_column("定位")
    table.add_column("检索入口")
    table.add_column("项目接入")
    for source in sources:
        table.add_row(
            source["name"],
            source["role"],
            source["search_url"],
            source["machine_access"],
        )
    console.print(table)
    console.print("专有数据库只使用本人/机构授权检索与导出；本项目不绕过访问控制。")


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


@literature_app.command("merge")
def literature_merge(
    sources: Annotated[list[Path], typer.Argument(help="两个或更多标准化 CSV")],
    output: Annotated[Path, typer.Option("--output", "-o", help="合并去重后的 CSV")] = Path(
        "literature/combined.csv"
    ),
) -> None:
    """合并 OpenAlex、Crossref 与 Zotero 中英文题录并按 DOI/标题去重。"""
    try:
        path, before, after = merge_csv(sources, output)
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


@zotero_app.command("collections")
def zotero_collections(
    json_output: Annotated[bool, typer.Option("--json", help="输出 JSON")] = False,
) -> None:
    """列出 Zotero collections 及其 key，便于按项目专题拉取。"""
    try:
        collections = list_zotero_collections()
    except Exception as exc:
        console.print(f"[red]Zotero collections 读取失败：{exc}[/red]")
        raise typer.Exit(2) from exc
    if json_output:
        console.print_json(json.dumps(collections, ensure_ascii=False))
        return
    table = Table(title="Zotero collections")
    table.add_column("名称")
    table.add_column("Collection key")
    table.add_column("父级 key")
    for collection in collections:
        table.add_row(
            str(collection["name"]),
            str(collection["key"]),
            str(collection["parent"]),
        )
    console.print(table)
    console.print(f"共 {len(collections)} 个 collection")


@zotero_app.command("export-csv")
def zotero_export_csv(
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("literature/zotero.csv"),
    collection: Annotated[str | None, typer.Option(help="可选 Zotero collection key")] = None,
) -> None:
    """将 Zotero（含各中文数据库采集项）标准化为可去重 CSV。"""
    try:
        path, count = pull_zotero_csv(output, collection=collection)
    except Exception as exc:
        console.print(f"[red]Zotero CSV 导出失败：{exc}[/red]")
        raise typer.Exit(2) from exc
    console.print(f"[green]已保存 {count} 条标准化记录[/green] {path}")


@zotero_app.command("export-csl")
def zotero_export_csl(
    output: Annotated[Path, typer.Option("--output", "-o")] = Path(
        "manuscript/references.json"
    ),
    collection: Annotated[str | None, typer.Option(help="可选 Zotero collection key")] = None,
) -> None:
    """导出 Zotero 顶层题录为 Quarto/Pandoc 可直接引用的 CSL JSON。"""
    try:
        path, count = pull_zotero_csl_json(output, collection=collection)
    except Exception as exc:
        console.print(f"[red]Zotero CSL JSON 导出失败：{exc}[/red]")
        raise typer.Exit(2) from exc
    console.print(f"[green]已保存 {count} 条 CSL JSON 引用[/green] {path}")
    console.print(
        "在 Quarto YAML 中设置 bibliography: references.json，再用 [@条目ID] 插入引用。",
        markup=False,
    )


if __name__ == "__main__":
    app()
