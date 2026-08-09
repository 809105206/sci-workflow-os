"use client";

import { useMemo, useState } from "react";
import FigureStudio from "./FigureStudio";

type View = "overview" | "literature" | "writing" | "figures";
type Decision = "待判断" | "纳入" | "排除";
type StageState = "done" | "active" | "next";

const navItems: Array<{ id: View; label: string; mark: string }> = [
  { id: "overview", label: "研究总览", mark: "⌂" },
  { id: "literature", label: "文献雷达", mark: "⌕" },
  { id: "writing", label: "写作质检", mark: "✓" },
  { id: "figures", label: "图表工坊", mark: "◇" },
];

const stages: ReadonlyArray<{ id: string; title: string; detail: string; state: StageState }> = [
  { id: "G0", title: "方向与章程", detail: "等待输入新课题方向、资源和边界", state: "active" },
  { id: "G1", title: "选题筛选", detail: "候选问题评分与 Go / Pivot / Stop", state: "next" },
  { id: "G2", title: "文献与缺口", detail: "中英文检索、证据地图与最近邻分析", state: "next" },
  { id: "G3", title: "研究设计", detail: "目标、变量、对照、统计与识别条件", state: "next" },
  { id: "G4", title: "数据就绪", detail: "来源、质量、许可、切分与泄漏控制", state: "next" },
  { id: "G5", title: "核心结果", detail: "主实验、强基线、效应量与不确定性", state: "next" },
  { id: "G6", title: "证据加固", detail: "消融、稳健性、误差与外部验证", state: "next" },
  { id: "G7", title: "双语成稿", detail: "中英全文、大纲、论证链与对齐记录", state: "next" },
  { id: "G8", title: "选刊投稿", detail: "期刊适配、格式、伦理与投稿包", state: "next" },
  { id: "G9", title: "同行评审", detail: "意见矩阵、证据补强与版本记录", state: "next" },
  { id: "G10", title: "发表归档", detail: "校样、数据代码归档与成果传播", state: "next" },
];

const papers = [
  { id: 1, title: "示例英文题录：研究问题与领域证据", source: "导入后显示来源", year: 2026, type: "英文", relevance: 92, doi: "演示记录" },
  { id: 2, title: "示例英文题录：方法与强基线", source: "导入后显示来源", year: 2025, type: "英文", relevance: 88, doi: "演示记录" },
  { id: 3, title: "示例中文题录：研究对象与应用场景", source: "导入后显示来源", year: 2026, type: "中文", relevance: 90, doi: "演示记录" },
  { id: 4, title: "示例中文题录：现有方法与研究边界", source: "导入后显示来源", year: 2024, type: "中文", relevance: 84, doi: "演示记录" },
];

const initialDraft = `本研究评估候选方法对目标结果的影响。研究采用预先冻结的设计控制主要偏差来源。为什么该方法更可靠？当然可以通过更多实验进一步证明。结果显著提升了预测能力。`;

function lintDraft(text: string) {
  const checks = [
    { rule: "非陈述句", severity: "error", pattern: /[?？]/g, message: "删除疑问句，并将研究问题改写为可检验的陈述。" },
    { rule: "对话式表达", severity: "error", pattern: /(当然可以|如有需要|欢迎|让我们|请注意|I hope this helps|let us)/gi, message: "删除对读者的指令或对话式措辞。" },
    { rule: "空泛结论", severity: "warning", pattern: /(显著提升|至关重要|不言而喻|毋庸置疑)/g, message: "补充效应量、置信区间或来源，避免无证据强化。" },
    { rule: "生成式元话语", severity: "error", pattern: /(作为(?:一个)?AI|根据您的要求|以下是|下面将|接下来我们)/g, message: "删除生成过程、任务说明和结构播报。" },
    { rule: "未完成占位", severity: "error", pattern: /(TODO|TBD|待补充|待填写|XX期刊)/gi, message: "提交前必须替换全部占位内容。" },
  ];

  const issues = checks.flatMap((check) => {
    const matches = text.match(check.pattern) ?? [];
    return matches.map((match) => ({ ...check, match }));
  });
  const errors = issues.filter((issue) => issue.severity === "error").length;
  const warnings = issues.length - errors;
  const score = Math.max(0, 100 - errors * 16 - warnings * 7);
  return { issues, errors, warnings, score };
}

function StatusPill({ state }: { state: StageState }) {
  const labels = { done: "已完成", active: "进行中", next: "待启动" };
  return <span className={`stage-status ${state}`}>{labels[state]}</span>;
}

export default function App() {
  const [view, setView] = useState<View>("overview");
  const [query, setQuery] = useState("");
  const [language, setLanguage] = useState("全部");
  const [decisions, setDecisions] = useState<Record<number, Decision>>({});
  const [draft, setDraft] = useState(initialDraft);
  const [notice, setNotice] = useState("本地工作流已就绪");

  const filteredPapers = useMemo(() => papers.filter((paper) => {
    const matchesQuery = `${paper.title} ${paper.source} ${paper.doi}`.toLowerCase().includes(query.toLowerCase());
    return matchesQuery && (language === "全部" || paper.type === language);
  }), [query, language]);

  const lint = useMemo(() => lintDraft(draft), [draft]);

  const renderView = () => {
    if (view === "literature") {
      return (
        <section className="view-shell">
          <div className="view-heading">
            <div><p className="eyebrow">Evidence radar</p><h1>文献雷达</h1><p>先保存题名、摘要和引用地址，再由研究者决定是否下载与纳入。</p></div>
            <button className="primary-button" onClick={() => setNotice("已生成中文候选检索任务")}>新建检索</button>
          </div>
          <div className="source-strip">
            {["OpenAlex · 已连接", "Zotero · 已连接", "Crossref · 免密钥", "中文候选池 · 可用"].map((source, index) => <span className={index < 2 ? "source live" : "source"} key={source}>{source}</span>)}
          </div>
          <div className="panel literature-panel">
            <div className="toolbar">
              <label className="search-box"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="检索题名、期刊或 DOI" /></label>
              <div className="segmented" aria-label="语言筛选">{["全部", "中文", "英文"].map((item) => <button className={language === item ? "selected" : ""} onClick={() => setLanguage(item)} key={item}>{item}</button>)}</div>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>文献</th><th>年份</th><th>相关度</th><th>决策</th></tr></thead>
                <tbody>{filteredPapers.map((paper) => {
                  const decision = decisions[paper.id] ?? "待判断";
                  return <tr key={paper.id}>
                    <td><strong>{paper.title}</strong><span>{paper.source} · {paper.type} · {paper.doi}</span></td>
                    <td>{paper.year}</td>
                    <td><div className="relevance"><i style={{ width: `${paper.relevance}%` }} /><span>{paper.relevance}</span></div></td>
                    <td><select value={decision} className={`decision ${decision}`} onChange={(event) => setDecisions({ ...decisions, [paper.id]: event.target.value as Decision })}><option>待判断</option><option>纳入</option><option>排除</option></select></td>
                  </tr>;
                })}</tbody>
              </table>
            </div>
          </div>
        </section>
      );
    }

    if (view === "writing") {
      return (
        <section className="view-shell">
          <div className="view-heading"><div><p className="eyebrow">Submission gate</p><h1>写作质检</h1><p>规则层直接阻断疑问句、对话式表达、生成式元话语和无证据强化。</p></div><button className="primary-button" onClick={() => setNotice(lint.errors ? `质检未通过：${lint.errors} 个错误` : "质检通过，可进入投稿检查")}>执行完整质检</button></div>
          <div className="writing-grid">
            <div className="panel editor-panel">
              <div className="panel-title"><span>稿件片段</span><small>实时检查 · 中文 / English</small></div>
              <textarea value={draft} onChange={(event) => setDraft(event.target.value)} aria-label="待检查稿件" />
              <div className="editor-footer"><span>{draft.length} 字符</span><span>规则集：SCI Declarative v1</span></div>
            </div>
            <aside className="panel quality-panel">
              <div className="score-ring" style={{ "--score": `${lint.score * 3.6}deg` } as React.CSSProperties}><div><strong>{lint.score}</strong><span>规范分</span></div></div>
              <div className="quality-summary"><span><b>{lint.errors}</b> 错误</span><span><b>{lint.warnings}</b> 警告</span><span><b>{5}</b> 启用规则</span></div>
              <div className="issue-list">{lint.issues.length ? lint.issues.map((issue, index) => <article className={`issue ${issue.severity}`} key={`${issue.rule}-${index}`}><div><strong>{issue.rule}</strong><code>{issue.match}</code></div><p>{issue.message}</p></article>) : <div className="empty-state"><strong>当前片段通过规则检查</strong><p>仍需由作者核验论据、数据和引文。</p></div>}</div>
            </aside>
          </div>
          <div className="rule-cards">
            {[{ n: "01", t: "句式约束", d: "正文仅保留陈述句；研究问题改写为假设或目标。" }, { n: "02", t: "证据约束", d: "定量结论绑定效应量、区间、图表或可核验引文。" }, { n: "03", t: "相关性约束", d: "每段服务于研究问题、方法、结果或边界，不保留任务说明。" }, { n: "04", t: "论证链", d: "每个论点记录论据、实验、检验内容、全文作用和边界化意义。" }, { n: "05", t: "双语对齐", d: "中文稿与英文稿共享数字、单位、公式、图表、引文和结论范围。" }].map((rule) => <article key={rule.n}><span>{rule.n}</span><div><h3>{rule.t}</h3><p>{rule.d}</p></div></article>)}
          </div>
        </section>
      );
    }

    if (view === "figures") {
      return (
        <section className="view-shell">
          <div className="view-heading">
            <div><p className="eyebrow">Figure laboratory</p><h1>零安装图表工坊</h1><p>选择 CSV、指定 X/Y 变量并导出投稿图，整个过程不需要 OriginPro、MATLAB 或 Python。</p></div>
            <span className="privacy-badge"><i />浏览器本地处理</span>
          </div>
          <FigureStudio onNotice={setNotice} />
          <div className="install-paths">
            <article className="recommended"><span>默认方案</span><h3>浏览器作图</h3><p>双击单文件即可运行，支持 CSV、折线图、散点图、柱状图、SVG、PNG 和复现 YAML。</p><b>零安装</b></article>
            <article><span>批量复现</span><h3>Python 开放工具链</h3><p>一键安装 Matplotlib 与 Plotly，适合批量制图、CI 和论文复现包。</p><b>INSTALL-PLOTTING</b></article>
            <article><span>高级可选</span><h3>OriginPro 适配器</h3><p>仅在已有 Windows 与 Origin 许可证时启用，不作为项目必要条件。</p><b>可选</b></article>
          </div>
        </section>
      );
    }

    return (
      <section className="view-shell">
        <div className="view-heading"><div><p className="eyebrow">Research operating system</p><h1>研究总览</h1><p>每个新项目从独立方向输入开始，再进入选题、证据、实验、双语成稿与发表归档。</p></div><button className="primary-button" onClick={() => setNotice("请先向 Codex 说明研究方向与已有数据或资源")}>开始 G0 方向输入</button></div>
        <div className="metric-grid">
          <article className="metric-card focus"><span>当前阶段</span><strong>G0</strong><p>等待新项目方向</p><i>→</i></article>
          <article className="metric-card"><span>文献库</span><strong>0</strong><p>方向确认后建立独立候选池</p><i>—</i></article>
          <article className="metric-card"><span>质量规则</span><strong>24</strong><p>陈述句 · 证据 · 相关性</p><i>100%</i></article>
          <article className="metric-card"><span>双语交付</span><strong>5</strong><p>中英全文 · 大纲 · 论证链 · 对齐</p><i className="healthy">强制</i></article>
        </div>
        <div className="overview-grid">
          <div className="panel pipeline-panel">
            <div className="panel-title"><span>G0–G10 研究流程</span><small>等待方向输入</small></div>
            <div className="pipeline-list">{stages.map((stage) => <button key={stage.id} onClick={() => setNotice(`${stage.id} · ${stage.title}`)}><span className={`stage-mark ${stage.state}`}>{stage.state === "done" ? "✓" : stage.id.replace("G", "")}</span><div><strong>{stage.id} · {stage.title}</strong><p>{stage.detail}</p></div><StatusPill state={stage.state} /></button>)}</div>
          </div>
          <aside className="overview-aside">
            <div className="panel project-card"><p className="eyebrow">Active project</p><h2>尚未载入研究项目</h2><p>向 Codex 说明宽泛方向即可建立全新的候选选题、证据池和研究工作区。</p><div className="tag-row"><span>方向独立</span><span>G0–G10</span><span>中英双稿</span></div><div className="progress"><span><b>项目成熟度</b><em>0%</em></span><i><b style={{ width: "0%" }} /></i></div></div>
            <div className="panel activity-card"><div className="panel-title"><span>方法论能力</span><small>通用模板</small></div>{[{c:"teal",t:"新项目独立建档",d:"不继承上一课题内容",time:"G0"},{c:"gold",t:"双语证据对齐",d:"数字、图表、引文与边界一致",time:"G7"},{c:"blue",t:"论证链审计",d:"论点、实验、作用与意义闭环",time:"G6–G7"}].map((item) => <article key={item.t}><i className={item.c}/><div><strong>{item.t}</strong><p>{item.d}</p></div><time>{item.time}</time></article>)}</div>
          </aside>
        </div>
      </section>
    );
  };

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span>Σ</span><div><strong>SCI Workflow</strong><small>Research OS</small></div></div>
        <nav>{navItems.map((item) => <button key={item.id} className={view === item.id ? "active" : ""} onClick={() => setView(item.id)}><span>{item.mark}</span>{item.label}{item.id === "writing" && lint.errors > 0 ? <b>{lint.errors}</b> : null}</button>)}</nav>
        <div className="sidebar-block"><span>工作空间</span><strong>NEW-STUDY</strong><small>方向独立 · 本地优先</small></div>
        <div className="sidebar-footer"><span className="avatar">研</span><div><strong>研究者</strong><small>项目所有者</small></div><button aria-label="更多设置">•••</button></div>
      </aside>
      <div className="main-column">
        <header className="topbar"><div className="breadcrumb"><span>SCI Workflow OS</span><b>/</b><strong>{navItems.find((item) => item.id === view)?.label}</strong></div><div className="system-status"><i/><span>{notice}</span><button onClick={() => setNotice("本地工作流已就绪")}>↻</button></div></header>
        {renderView()}
      </div>
    </main>
  );
}
