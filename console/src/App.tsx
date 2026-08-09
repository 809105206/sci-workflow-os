"use client";

import { useMemo, useState } from "react";

type View = "overview" | "literature" | "writing" | "figures";
type Decision = "待判断" | "纳入" | "排除";

const navItems: Array<{ id: View; label: string; mark: string }> = [
  { id: "overview", label: "研究总览", mark: "⌂" },
  { id: "literature", label: "文献雷达", mark: "⌕" },
  { id: "writing", label: "写作质检", mark: "✓" },
  { id: "figures", label: "图表工坊", mark: "◇" },
];

const stages = [
  { id: "G0", title: "研究问题", detail: "高维扰动对机械钻速的参数效应", state: "done" },
  { id: "G1", title: "证据检索", detail: "OpenAlex、Zotero 与中文候选池", state: "active" },
  { id: "G2", title: "选题验证", detail: "可识别性、创新性与数据可得性", state: "active" },
  { id: "G3", title: "研究设计", detail: "双重机器学习与交叉拟合", state: "next" },
  { id: "G4", title: "数据治理", detail: "变量字典、缺失机制与版本记录", state: "next" },
  { id: "G5", title: "模型与估计", detail: "扰动参数、异质效应与稳健性", state: "next" },
  { id: "G6", title: "结果复核", detail: "安慰剂、敏感性与外推边界", state: "next" },
  { id: "G7", title: "图表生成", detail: "OriginPro 或开放后备链", state: "next" },
  { id: "G8", title: "论文写作", detail: "陈述句、证据约束与去模板化", state: "next" },
  { id: "G9", title: "投稿质检", detail: "期刊适配、清单与可复现包", state: "next" },
  { id: "G10", title: "投稿响应", detail: "审稿意见矩阵与版本归档", state: "next" },
] as const;

const papers = [
  { id: 1, title: "Double/debiased machine learning for treatment and structural parameters", source: "The Econometrics Journal", year: 2018, type: "英文", relevance: 98, doi: "10.1111/ectj.12097" },
  { id: 2, title: "Double machine learning for treatment and causal parameters", source: "arXiv", year: 2016, type: "英文", relevance: 94, doi: "10.48550/arXiv.1608.00060" },
  { id: 3, title: "基于机器学习的机械钻速预测方法研究", source: "石油钻探技术", year: 2023, type: "中文", relevance: 91, doi: "候选记录" },
  { id: 4, title: "钻井参数优化及机械钻速智能预测研究进展", source: "钻采工艺", year: 2022, type: "中文", relevance: 88, doi: "候选记录" },
  { id: 5, title: "Causal machine learning and its application in drilling optimization", source: "Journal of Petroleum Science and Engineering", year: 2021, type: "英文", relevance: 86, doi: "待核验" },
  { id: 6, title: "复杂地层钻井参数对机械钻速的影响分析", source: "断块油气田", year: 2020, type: "中文", relevance: 82, doi: "候选记录" },
];

const initialDraft = `本文估计钻压、转速和排量扰动对机械钻速的条件平均效应。研究采用交叉拟合的双重机器学习方法控制高维地层与工况混杂因素。为什么该方法更可靠？当然可以通过更多模型进一步证明。结果显著提升了预测能力。`;

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

function StatusPill({ state }: { state: "done" | "active" | "next" }) {
  const labels = { done: "已完成", active: "进行中", next: "待启动" };
  return <span className={`stage-status ${state}`}>{labels[state]}</span>;
}

export default function App() {
  const [view, setView] = useState<View>("overview");
  const [query, setQuery] = useState("");
  const [language, setLanguage] = useState("全部");
  const [decisions, setDecisions] = useState<Record<number, Decision>>({ 1: "纳入", 2: "纳入" });
  const [draft, setDraft] = useState(initialDraft);
  const [backend, setBackend] = useState("OriginPro");
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
            {[{ n: "01", t: "句式约束", d: "正文仅保留陈述句；研究问题改写为假设或目标。" }, { n: "02", t: "证据约束", d: "定量结论绑定效应量、区间、图表或可核验引文。" }, { n: "03", t: "相关性约束", d: "每段服务于研究问题、方法、结果或边界，不保留任务说明。" }].map((rule) => <article key={rule.n}><span>{rule.n}</span><div><h3>{rule.t}</h3><p>{rule.d}</p></div></article>)}
          </div>
        </section>
      );
    }

    if (view === "figures") {
      const backends = [
        { name: "OriginPro", tag: "Windows", detail: "官方 originpro 自动化；导出 OPJU、PDF、SVG、PNG。" },
        { name: "Matplotlib", tag: "跨平台", detail: "本地与 CI 的可复现静态图后备链。" },
        { name: "Plotly", tag: "交互", detail: "生成 HTML 探索图，并支持静态格式导出。" },
        { name: "ECharts", tag: "前端", detail: "用于浏览器预览和结果交互，不替代投稿原图。" },
      ];
      return (
        <section className="view-shell">
          <div className="view-heading"><div><p className="eyebrow">Figure laboratory</p><h1>图表工坊</h1><p>同一份数据和图形规范可选择 OriginPro 或开放后端渲染。</p></div><button className="primary-button" onClick={() => setNotice(`已创建 ${backend} 渲染任务`)}>生成图表</button></div>
          <div className="figure-grid">
            <div className="panel chart-panel">
              <div className="panel-title"><span>扰动参数的条件效应</span><small>95% 置信区间</small></div>
              <div className="chart-area" role="img" aria-label="钻压扰动与机械钻速条件效应示例图">
                <div className="y-label">ROP 效应 (m/h)</div>
                <svg viewBox="0 0 720 330" aria-hidden="true">
                  <g className="grid-lines"><line x1="70" y1="45" x2="690" y2="45"/><line x1="70" y1="110" x2="690" y2="110"/><line x1="70" y1="175" x2="690" y2="175"/><line x1="70" y1="240" x2="690" y2="240"/><line x1="70" y1="305" x2="690" y2="305"/></g>
                  <line className="zero-line" x1="70" y1="240" x2="690" y2="240"/>
                  <path className="confidence" d="M90 241 C180 225, 245 201, 315 165 S465 102, 540 90 S625 76,680 60 L680 112 C620 126,570 131,520 141 S410 177,330 218 S180 276,90 286 Z" />
                  <path className="effect-line" d="M90 263 C175 250,245 224,315 192 S455 131,530 116 S625 99,680 86" />
                  {[[90,263],[180,248],[270,215],[360,170],[450,137],[540,114],[625,100],[680,86]].map(([x,y]) => <circle className="effect-point" cx={x} cy={y} r="5" key={`${x}-${y}`}/>)}
                  <g className="axis-labels"><text x="82" y="325">−15</text><text x="224" y="325">−10</text><text x="373" y="325">−5</text><text x="526" y="325">0</text><text x="673" y="325">5</text></g>
                </svg>
                <div className="x-label">钻压扰动 (%)</div>
              </div>
              <div className="chart-caption"><i /><span>双重机器学习估计</span><em>阴影区域表示 95% 置信区间</em></div>
            </div>
            <aside className="panel backend-panel">
              <div className="panel-title"><span>渲染后端</span><small>可替换</small></div>
              <div className="backend-list">{backends.map((item) => <button onClick={() => setBackend(item.name)} className={backend === item.name ? "selected" : ""} key={item.name}><span className="radio"><i /></span><div><strong>{item.name}<small>{item.tag}</small></strong><p>{item.detail}</p></div></button>)}</div>
              <div className="export-box"><span>输出格式</span><div>{["PDF", "SVG", "PNG", backend === "OriginPro" ? "OPJU" : "HTML"].map((format) => <b key={format}>{format}</b>)}</div></div>
            </aside>
          </div>
          <div className="command-card"><div><span>可复现命令</span><code>sciops figure render figures/rop-effect.yaml --backend {backend.toLowerCase()}</code></div><button onClick={() => setNotice("命令已准备，可在本地终端执行")}>复制命令</button></div>
        </section>
      );
    }

    return (
      <section className="view-shell">
        <div className="view-heading"><div><p className="eyebrow">Research operating system</p><h1>研究总览</h1><p>从研究问题、证据筛选到规范写作和投稿图表，全部落在可复现流程中。</p></div><button className="primary-button" onClick={() => setView("literature")}>继续 G1 检索</button></div>
        <div className="metric-grid">
          <article className="metric-card focus"><span>当前阶段</span><strong>G1–G2</strong><p>证据检索与选题验证</p><i>→</i></article>
          <article className="metric-card"><span>文献库</span><strong>18</strong><p>11 条 Zotero · 7 条中文候选</p><i>+6</i></article>
          <article className="metric-card"><span>质量规则</span><strong>24</strong><p>陈述句 · 证据 · 相关性</p><i>100%</i></article>
          <article className="metric-card"><span>自动检查</span><strong>22</strong><p>当前测试全部通过</p><i className="healthy">健康</i></article>
        </div>
        <div className="overview-grid">
          <div className="panel pipeline-panel">
            <div className="panel-title"><span>G0–G10 研究流程</span><small>2 / 11 已启动</small></div>
            <div className="pipeline-list">{stages.map((stage) => <button key={stage.id} onClick={() => setNotice(`${stage.id} · ${stage.title}`)}><span className={`stage-mark ${stage.state}`}>{stage.state === "done" ? "✓" : stage.id.replace("G", "")}</span><div><strong>{stage.id} · {stage.title}</strong><p>{stage.detail}</p></div><StatusPill state={stage.state} /></button>)}</div>
          </div>
          <aside className="overview-aside">
            <div className="panel project-card"><p className="eyebrow">Active project</p><h2>高维扰动与机械钻速参数效应</h2><p>以双重机器学习估计钻压、转速、排量等参数扰动的因果效应与异质性。</p><div className="tag-row"><span>DML</span><span>高维控制</span><span>钻井优化</span></div><div className="progress"><span><b>项目成熟度</b><em>28%</em></span><i><b /></i></div></div>
            <div className="panel activity-card"><div className="panel-title"><span>近期活动</span><small>本地记录</small></div>{[{c:"teal",t:"Zotero 连接已验证",d:"研究库可写入与去重",time:"今天"},{c:"gold",t:"中文候选池已生成",d:"题名、摘要、引用地址",time:"今天"},{c:"blue",t:"SCI.md 已整理",d:"G0–G10 标准流程",time:"昨天"}].map((item) => <article key={item.t}><i className={item.c}/><div><strong>{item.t}</strong><p>{item.d}</p></div><time>{item.time}</time></article>)}</div>
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
        <div className="sidebar-block"><span>工作空间</span><strong>ROP-DML-01</strong><small>本地优先 · Git 可追踪</small></div>
        <div className="sidebar-footer"><span className="avatar">研</span><div><strong>研究者</strong><small>项目所有者</small></div><button aria-label="更多设置">•••</button></div>
      </aside>
      <div className="main-column">
        <header className="topbar"><div className="breadcrumb"><span>SCI Workflow OS</span><b>/</b><strong>{navItems.find((item) => item.id === view)?.label}</strong></div><div className="system-status"><i/><span>{notice}</span><button onClick={() => setNotice("本地工作流已就绪")}>↻</button></div></header>
        {renderView()}
      </div>
    </main>
  );
}
