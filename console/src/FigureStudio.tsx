import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import * as echarts from "echarts/core";
import { BarChart, LineChart, ScatterChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  ToolboxComponent,
  TooltipComponent,
} from "echarts/components";
import { SVGRenderer } from "echarts/renderers";

echarts.use([
  BarChart,
  LineChart,
  ScatterChart,
  GridComponent,
  LegendComponent,
  TitleComponent,
  ToolboxComponent,
  TooltipComponent,
  SVGRenderer,
]);

type ChartKind = "line" | "scatter" | "bar";
type DataRow = Record<string, string>;

type ParsedDataset = {
  columns: string[];
  numericColumns: string[];
  rows: DataRow[];
};

type FigureStudioProps = {
  onNotice: (message: string) => void;
};

const demoCsv = `exposure_change,effect_estimate,ci_low,ci_high
-15,-0.20,-0.38,-0.02
-10,-0.08,-0.24,0.08
-5,0.21,0.05,0.37
0,0.48,0.31,0.65
5,0.66,0.47,0.85
10,0.78,0.55,1.01
15,0.91,0.65,1.17`;

function parseCsvRows(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    const next = text[index + 1];
    if (character === '"' && quoted && next === '"') {
      field += '"';
      index += 1;
    } else if (character === '"') {
      quoted = !quoted;
    } else if (character === "," && !quoted) {
      row.push(field.trim());
      field = "";
    } else if ((character === "\n" || character === "\r") && !quoted) {
      if (character === "\r" && next === "\n") index += 1;
      row.push(field.trim());
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      field = "";
    } else {
      field += character;
    }
  }
  row.push(field.trim());
  if (row.some((value) => value !== "")) rows.push(row);
  return rows;
}

function uniqueHeaders(raw: string[]): string[] {
  const counts = new Map<string, number>();
  return raw.map((item, index) => {
    const base = item.trim() || `column_${index + 1}`;
    const count = (counts.get(base) ?? 0) + 1;
    counts.set(base, count);
    return count === 1 ? base : `${base}_${count}`;
  });
}

function parseCsv(text: string): ParsedDataset {
  const matrix = parseCsvRows(text.replace(/^\uFEFF/, ""));
  if (matrix.length < 2) throw new Error("CSV 至少需要表头和一行数据。 ");
  const columns = uniqueHeaders(matrix[0]);
  if (columns.length < 2) throw new Error("CSV 至少需要两列。 ");
  const rows = matrix.slice(1).map((values) => Object.fromEntries(
    columns.map((column, index) => [column, values[index] ?? ""]),
  ));
  const numericColumns = columns.filter((column) => {
    const values = rows.map((row) => row[column]).filter((value) => value !== "");
    return values.length > 0 && values.every((value) => Number.isFinite(Number(value)));
  });
  if (!numericColumns.length) throw new Error("CSV 至少需要一列数值。 ");
  return { columns, numericColumns, rows };
}

function csvEscape(value: string): string {
  return /[",\n\r]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value;
}

function toCsv(dataset: ParsedDataset): string {
  const lines = [dataset.columns.map(csvEscape).join(",")];
  dataset.rows.forEach((row) => {
    lines.push(dataset.columns.map((column) => csvEscape(row[column] ?? "")).join(","));
  });
  return `${lines.join("\n")}\n`;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 500);
}

function safeStem(filename: string): string {
  return filename.replace(/\.[^.]+$/, "").replace(/[^\w\u4e00-\u9fff-]+/g, "-") || "figure";
}

export default function FigureStudio({ onNotice }: FigureStudioProps) {
  const initial = useMemo(() => parseCsv(demoCsv), []);
  const chartElement = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<ReturnType<typeof echarts.init> | null>(null);
  const [dataset, setDataset] = useState<ParsedDataset>(initial);
  const [filename, setFilename] = useState("effect-estimate.example.csv");
  const [xColumn, setXColumn] = useState(initial.columns[0]);
  const [yColumn, setYColumn] = useState(initial.numericColumns[1] ?? initial.numericColumns[0]);
  const [kind, setKind] = useState<ChartKind>("line");
  const [title, setTitle] = useState("不同暴露变化下的效应估计");
  const [xLabel, setXLabel] = useState("暴露变化 (%)");
  const [yLabel, setYLabel] = useState("效应估计（结局单位）");
  const [error, setError] = useState("");

  const numericX = dataset.numericColumns.includes(xColumn);
  const plottedRows = useMemo(() => dataset.rows
    .filter((row) => row[xColumn] !== "" && Number.isFinite(Number(row[yColumn])))
    .map((row) => ({
      x: numericX ? Number(row[xColumn]) : row[xColumn],
      y: Number(row[yColumn]),
    })), [dataset, numericX, xColumn, yColumn]);

  useEffect(() => {
    if (!chartElement.current) return;
    const chart = echarts.init(chartElement.current, undefined, { renderer: "svg" });
    chartInstance.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(chartElement.current);
    return () => {
      observer.disconnect();
      chart.dispose();
      chartInstance.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartInstance.current;
    if (!chart) return;
    const sorted = numericX
      ? [...plottedRows].sort((left, right) => Number(left.x) - Number(right.x))
      : plottedRows;
    const values = numericX ? sorted.map((item) => [item.x, item.y]) : sorted.map((item) => item.y);
    chart.setOption({
      animation: false,
      color: ["#0f6b61"],
      title: { text: title, left: 18, top: 12, textStyle: { fontSize: 15, fontWeight: 600, color: "#172220" } },
      tooltip: { trigger: kind === "scatter" ? "item" : "axis" },
      toolbox: { right: 14, top: 8, feature: { restore: {}, saveAsImage: { title: "导出 PNG", pixelRatio: 2 } } },
      grid: { left: 70, right: 32, top: 66, bottom: 58 },
      xAxis: {
        type: numericX ? "value" : "category",
        data: numericX ? undefined : sorted.map((item) => item.x),
        name: xLabel,
        nameLocation: "middle",
        nameGap: 36,
        axisLine: { lineStyle: { color: "#82908b" } },
        axisLabel: { color: "#64716d" },
      },
      yAxis: {
        type: "value",
        name: yLabel,
        nameLocation: "middle",
        nameGap: 50,
        splitLine: { lineStyle: { color: "#e6ece8" } },
        axisLabel: { color: "#64716d" },
      },
      series: [{
        type: kind,
        data: values,
        symbolSize: kind === "scatter" ? 9 : 7,
        showSymbol: true,
        smooth: false,
        itemStyle: { color: "#0f6b61", borderColor: "#ffffff", borderWidth: 1 },
        lineStyle: { color: "#0f6b61", width: 2 },
        barMaxWidth: 42,
      }],
    }, true);
  }, [kind, numericX, plottedRows, title, xLabel, yLabel]);

  useEffect(() => {
    try {
      localStorage.setItem("sciops.figure.preferences", JSON.stringify({ kind, title, xLabel, yLabel }));
    } catch {
      // File-mode privacy settings may disable storage; the chart still works.
    }
  }, [kind, title, xLabel, yLabel]);

  const loadDataset = (text: string, sourceName: string) => {
    const parsed = parseCsv(text);
    const defaultY = parsed.numericColumns.find((column) => column !== parsed.columns[0])
      ?? parsed.numericColumns[0];
    setDataset(parsed);
    setFilename(sourceName);
    setXColumn(parsed.columns[0]);
    setYColumn(defaultY);
    setError("");
    onNotice(`已在本地载入 ${parsed.rows.length} 行数据`);
  };

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      loadDataset(await file.text(), file.name);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "CSV 读取失败。";
      setError(message);
      onNotice(message);
    } finally {
      event.target.value = "";
    }
  };

  const getSvg = () => {
    const svg = chartElement.current?.querySelector("svg");
    if (!svg) throw new Error("图表尚未完成渲染。 ");
    const clone = svg.cloneNode(true) as SVGElement;
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    return new XMLSerializer().serializeToString(clone);
  };

  const exportSvg = () => {
    try {
      downloadBlob(new Blob([getSvg()], { type: "image/svg+xml;charset=utf-8" }), `${safeStem(filename)}.svg`);
      onNotice("已导出可编辑 SVG 矢量图");
    } catch (caught) {
      onNotice(caught instanceof Error ? caught.message : "SVG 导出失败。 ");
    }
  };

  const exportPng = () => {
    try {
      const svgBlob = new Blob([getSvg()], { type: "image/svg+xml;charset=utf-8" });
      const sourceUrl = URL.createObjectURL(svgBlob);
      const image = new Image();
      image.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = 1800;
        canvas.height = 1100;
        const context = canvas.getContext("2d");
        if (!context) {
          URL.revokeObjectURL(sourceUrl);
          onNotice("当前浏览器无法创建 PNG 画布。 ");
          return;
        }
        context.fillStyle = "#ffffff";
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        canvas.toBlob((blob) => {
          if (blob) downloadBlob(blob, `${safeStem(filename)}.png`);
          URL.revokeObjectURL(sourceUrl);
          onNotice("已导出 1800 × 1100 PNG");
        }, "image/png");
      };
      image.onerror = () => {
        URL.revokeObjectURL(sourceUrl);
        onNotice("PNG 转换失败，可先导出 SVG。 ");
      };
      image.src = sourceUrl;
    } catch (caught) {
      onNotice(caught instanceof Error ? caught.message : "PNG 导出失败。 ");
    }
  };

  const exportSpec = () => {
    const spec = [
      "version: 1",
      `data: ${JSON.stringify(filename)}`,
      `x: ${JSON.stringify(xColumn)}`,
      `y: ${JSON.stringify(yColumn)}`,
      `kind: ${kind}`,
      `title: ${JSON.stringify(title)}`,
      `x_label: ${JSON.stringify(xLabel)}`,
      `y_label: ${JSON.stringify(yLabel)}`,
      "outputs:",
      `  - ${JSON.stringify(`${safeStem(filename)}.svg`)}`,
      `  - ${JSON.stringify(`${safeStem(filename)}.png`)}`,
      "",
    ].join("\n");
    downloadBlob(new Blob([spec], { type: "text/yaml;charset=utf-8" }), `${safeStem(filename)}.yaml`);
    onNotice("已导出可复现 YAML 图形规范");
  };

  return (
    <>
      <div className="studio-grid">
        <aside className="panel studio-controls">
          <div className="panel-title"><span>三步生成投稿图</span><small>零安装 · 数据不上传</small></div>
          <div className="studio-step">
            <b>1</b><div><strong>载入 CSV</strong><p>{filename} · {dataset.rows.length} 行 × {dataset.columns.length} 列</p></div>
          </div>
          <div className="upload-actions">
            <label className="upload-button"><input type="file" accept=".csv,text/csv" onChange={handleUpload} />选择 CSV</label>
            <button onClick={() => loadDataset(demoCsv, "effect-estimate.example.csv")}>载入示例</button>
          </div>
          {error ? <p className="studio-error">{error}</p> : null}
          <div className="studio-step"><b>2</b><div><strong>选择变量</strong><p>Y 轴仅显示识别为数值的列。</p></div></div>
          <div className="field-pair">
            <label><span>X 轴</span><select value={xColumn} onChange={(event) => setXColumn(event.target.value)}>{dataset.columns.map((column) => <option key={column}>{column}</option>)}</select></label>
            <label><span>Y 轴</span><select value={yColumn} onChange={(event) => setYColumn(event.target.value)}>{dataset.numericColumns.map((column) => <option key={column}>{column}</option>)}</select></label>
          </div>
          <div className="studio-step"><b>3</b><div><strong>设置图形</strong><p>设置会保存在本机浏览器，不保存数据。</p></div></div>
          <div className="chart-kind" aria-label="图形类型">{(["line", "scatter", "bar"] as ChartKind[]).map((item) => <button className={kind === item ? "selected" : ""} onClick={() => setKind(item)} key={item}>{item === "line" ? "折线" : item === "scatter" ? "散点" : "柱状"}</button>)}</div>
          <label className="text-field"><span>图题</span><input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
          <div className="field-pair">
            <label><span>X 轴标题</span><input value={xLabel} onChange={(event) => setXLabel(event.target.value)} /></label>
            <label><span>Y 轴标题</span><input value={yLabel} onChange={(event) => setYLabel(event.target.value)} /></label>
          </div>
        </aside>
        <div className="panel studio-preview">
          <div className="panel-title"><span>浏览器科研图</span><small>Apache ECharts · SVG 渲染</small></div>
          <div ref={chartElement} className="echart-canvas" role="img" aria-label={`${title}图表`} />
          <div className="export-toolbar">
            <div><strong>{plottedRows.length}</strong><span>有效观测</span></div>
            <button onClick={exportSvg}>导出 SVG</button>
            <button onClick={exportPng}>导出 PNG</button>
            <button onClick={() => { downloadBlob(new Blob([toCsv(dataset)], { type: "text/csv;charset=utf-8" }), `${safeStem(filename)}-clean.csv`); onNotice("已导出清洗后 CSV"); }}>导出 CSV</button>
            <button className="accent" onClick={exportSpec}>导出复现 YAML</button>
          </div>
        </div>
      </div>
      <div className="data-preview panel">
        <div className="panel-title"><span>数据预览</span><small>仅显示前 5 行</small></div>
        <div className="table-wrap"><table><thead><tr>{dataset.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{dataset.rows.slice(0, 5).map((row, index) => <tr key={index}>{dataset.columns.map((column) => <td key={column}>{row[column]}</td>)}</tr>)}</tbody></table></div>
      </div>
    </>
  );
}
