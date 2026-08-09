from __future__ import annotations

import csv
import importlib.util
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class FigureError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FigureSpec:
    data: Path
    x: str
    y: str
    title: str
    x_label: str
    y_label: str
    kind: str
    outputs: tuple[Path, ...]
    lower: str | None = None
    upper: str | None = None
    sheet: str = "Data"
    graph: str = "Figure"


def load_figure_spec(path: Path) -> FigureSpec:
    path = path.expanduser().resolve()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise FigureError("图形规范必须是 YAML mapping。")
    required = ("data", "x", "y", "outputs")
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise FigureError(f"图形规范缺少字段: {', '.join(missing)}")
    kind = str(payload.get("kind", "line")).lower()
    if kind not in {"line", "scatter"}:
        raise FigureError("kind 只支持 line 或 scatter。")
    outputs_value = payload["outputs"]
    if isinstance(outputs_value, str):
        outputs_value = [outputs_value]
    if not isinstance(outputs_value, list) or not outputs_value:
        raise FigureError("outputs 必须是非空路径列表。")
    data_path = (path.parent / str(payload["data"])).resolve()
    outputs = tuple((path.parent / str(item)).resolve() for item in outputs_value)
    return FigureSpec(
        data=data_path,
        x=str(payload["x"]),
        y=str(payload["y"]),
        title=str(payload.get("title", "")),
        x_label=str(payload.get("x_label", payload["x"])),
        y_label=str(payload.get("y_label", payload["y"])),
        kind=kind,
        outputs=outputs,
        lower=str(payload["lower"]) if payload.get("lower") else None,
        upper=str(payload["upper"]) if payload.get("upper") else None,
        sheet=str(payload.get("sheet", "Data")),
        graph=str(payload.get("graph", "Figure")),
    )


def _read_rows(spec: FigureSpec) -> list[dict[str, str]]:
    if not spec.data.is_file():
        raise FigureError(f"数据文件不存在: {spec.data}")
    with spec.data.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {spec.x, spec.y, *(item for item in (spec.lower, spec.upper) if item)}
    missing = required - set(rows[0].keys() if rows else ())
    if missing:
        raise FigureError(f"CSV 缺少列: {', '.join(sorted(missing))}")
    if not rows:
        raise FigureError("CSV 没有数据行。")
    return rows


def available_backends() -> dict[str, dict[str, Any]]:
    windows = platform.system() == "Windows"
    return {
        "origin": {
            "available": windows and importlib.util.find_spec("originpro") is not None,
            "detail": "Origin 2021+ 与 originpro 可用" if windows else "仅支持 Windows",
        },
        "matplotlib": {
            "available": importlib.util.find_spec("matplotlib") is not None,
            "detail": "跨平台静态图",
        },
        "plotly": {
            "available": importlib.util.find_spec("plotly") is not None,
            "detail": "交互 HTML 与静态导出",
        },
    }


def _float_column(rows: list[dict[str, str]], name: str) -> list[float]:
    try:
        return [float(row[name]) for row in rows]
    except (KeyError, TypeError, ValueError) as exc:
        raise FigureError(f"列 {name} 必须是数值。") from exc


def render_matplotlib(spec: FigureSpec) -> tuple[Path, ...]:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise FigureError("缺少 Matplotlib；运行 uv sync --extra figures。") from exc
    rows = _read_rows(spec)
    x_values = _float_column(rows, spec.x)
    y_values = _float_column(rows, spec.y)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    figure, axis = plt.subplots(figsize=(6.3, 4.0), constrained_layout=True)
    if spec.kind == "scatter":
        axis.scatter(x_values, y_values, s=26, color="#0f6b61", edgecolor="white", linewidth=.6)
    else:
        axis.plot(x_values, y_values, marker="o", markersize=4, color="#0f6b61", linewidth=1.8)
    if spec.lower and spec.upper:
        axis.fill_between(
            x_values,
            _float_column(rows, spec.lower),
            _float_column(rows, spec.upper),
            color="#9bcfc4",
            alpha=.34,
            linewidth=0,
        )
    axis.axhline(0, color="#83918c", linewidth=.8, linestyle="--")
    axis.set(title=spec.title, xlabel=spec.x_label, ylabel=spec.y_label)
    axis.grid(axis="y", color="#e1e8e4", linewidth=.7)
    for output in spec.outputs:
        if output.suffix.lower() == ".html":
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(output, dpi=300 if output.suffix.lower() == ".png" else None)
    plt.close(figure)
    return tuple(output for output in spec.outputs if output.suffix.lower() != ".html")


def render_plotly(spec: FigureSpec) -> tuple[Path, ...]:
    try:
        import plotly.graph_objects as go
    except ImportError as exc:
        raise FigureError("缺少 Plotly；运行 uv sync --extra figures。") from exc
    rows = _read_rows(spec)
    x_values = _float_column(rows, spec.x)
    y_values = _float_column(rows, spec.y)
    mode = "markers" if spec.kind == "scatter" else "lines+markers"
    figure = go.Figure(go.Scatter(x=x_values, y=y_values, mode=mode, line={"color": "#0f6b61"}))
    if spec.lower and spec.upper:
        lower = _float_column(rows, spec.lower)
        upper = _float_column(rows, spec.upper)
        figure.add_trace(
            go.Scatter(
                x=x_values + list(reversed(x_values)),
                y=upper + list(reversed(lower)),
                fill="toself",
                fillcolor="rgba(15,107,97,.18)",
                line={"color": "rgba(0,0,0,0)"},
                hoverinfo="skip",
                showlegend=False,
            )
        )
    figure.update_layout(
        template="simple_white",
        title=spec.title,
        xaxis_title=spec.x_label,
        yaxis_title=spec.y_label,
        font={"size": 11},
    )
    rendered: list[Path] = []
    for output in spec.outputs:
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.suffix.lower() == ".html":
            figure.write_html(output, include_plotlyjs="cdn")
        else:
            try:
                figure.write_image(output, scale=2)
            except Exception as exc:
                raise FigureError("Plotly 静态导出需要 Kaleido；也可先输出 HTML。") from exc
        rendered.append(output)
    return tuple(rendered)


def render_origin(spec: FigureSpec, *, project: Path | None = None) -> tuple[Path, ...]:
    if platform.system() != "Windows":
        raise FigureError("OriginPro 自动化仅支持装有 Origin 2021+ 的 Windows。")
    try:
        import originpro as op
    except ImportError as exc:
        raise FigureError("缺少官方 originpro；运行 uv sync --extra origin。") from exc
    rows = _read_rows(spec)
    x_values = _float_column(rows, spec.x)
    y_values = _float_column(rows, spec.y)
    try:
        if op.oext:
            op.set_show(False)
        worksheet = op.new_sheet("w", lname=spec.sheet)
        worksheet.from_list(0, x_values, lname=spec.x_label)
        worksheet.from_list(1, y_values, lname=spec.y_label)
        graph = op.new_graph(
            template="scatter" if spec.kind == "scatter" else "line",
            lname=spec.graph,
        )
        layer = graph[0]
        layer.add_plot(
            worksheet,
            coly="B",
            colx="A",
            type=201 if spec.kind == "scatter" else 202,
        )
        layer.rescale()
        rendered: list[Path] = []
        for output in spec.outputs:
            if output.suffix.lower() in {".opju", ".html"}:
                continue
            output.parent.mkdir(parents=True, exist_ok=True)
            graph.save_fig(str(output))
            rendered.append(output)
        project_path = project or next(
            (item for item in spec.outputs if item.suffix.lower() == ".opju"),
            None,
        )
        if project_path:
            project_path.parent.mkdir(parents=True, exist_ok=True)
            op.save(str(project_path))
            rendered.append(project_path)
        return tuple(rendered)
    finally:
        if op.oext:
            op.exit()


def render_figure(
    spec: FigureSpec,
    *,
    backend: str = "auto",
    project: Path | None = None,
) -> tuple[str, tuple[Path, ...]]:
    backend = backend.lower()
    if backend == "auto":
        backend = "matplotlib"
    if backend == "origin":
        return backend, render_origin(spec, project=project)
    if backend == "matplotlib":
        return backend, render_matplotlib(spec)
    if backend == "plotly":
        return backend, render_plotly(spec)
    raise FigureError("backend 只支持 auto、origin、matplotlib 或 plotly。")
