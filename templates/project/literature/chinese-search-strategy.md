# 中文文献检索方案

- 项目：{{PROJECT_TITLE}}
- 方案版本：v0.1
- 制定日期：{{DATE}}
- 负责人：待填写
- 适用稿件：中文期刊 / 英文期刊 / 学位论文 / 综述（选择并说明）

## 1. 检索目标与边界

- 研究问题：待填写
- 文献类型：期刊论文 / 学位论文 / 会议论文 / 预印本 / 标准（选择）
- 时间范围：待填写
- 语言范围：简体中文 / 繁体中文 / 中英双语（选择）
- 学科范围：待填写
- 纳入标准：待填写
- 排除标准：待填写
- 停止日期与更新检索计划：待填写

## 2. 概念块与同义词

每个概念块内部用 `OR`，概念块之间用 `AND`。不要把方法名强制加入所有检索式，
否则容易漏掉用不同方法回答同一问题的最近邻研究。

| 概念块 | 中文首选词 | 同义词/旧称 | 缩写/全称 | 必要英文词 | 字段 |
| --- | --- | --- | --- | --- | --- |
| A 研究对象/人群 | 待填写 | 待填写 | 待填写 | 待填写 | 主题/篇名/摘要/关键词 |
| B 现象/结局/任务 | 待填写 | 待填写 | 待填写 | 待填写 | 主题/篇名/摘要/关键词 |
| C 方法/机制 | 待填写 | 待填写 | 待填写 | 待填写 | 主题/篇名/摘要/关键词 |
| D 场景/约束 | 待填写 | 待填写 | 待填写 | 待填写 | 主题/篇名/摘要/关键词 |
| E 排除概念 | 待填写 | 待填写 | — | 待填写 | NOT，谨慎使用 |

基础表达式：

```text
(A1 OR A2 OR A3) AND (B1 OR B2) AND (C1 OR C2)
```

至少保留一条高召回检索式（只用 A+B）和一条高精度检索式（A+B+C/D），分别记录命中数。

## 3. 数据库选择

先执行 `uv run sciops literature chinese-sources` 查看项目维护的实时入口。按学科选择：

- 综合主检：知网 + 万方 + 维普中的至少两个；条件允许时三库均检。
- 自然科学/工程：增加 NSTL、PubScholar；前沿线索增加 ChinaXiv。
- 人文社科：增加国家哲学社会科学文献中心。
- 医学/药学/公卫/护理：增加 SinoMed，并保留主题词与自由词两套检索。
- 自动初检：OpenAlex 中文过滤；它只作开放元数据补充，不能替代专有中文库。

本项目实际使用的数据源及理由：待填写。

## 4. 自动初检

```bash
uv run sciops literature search-cn "A词 B词 C词" \
  --from-year 2020 \
  --to-year 2026 \
  --limit 200 \
  --output literature/openalex-zh.csv
```

将实际命令、运行日期、命中数和导出文件写入 `02_search_log.csv`。OpenAlex 的语言字段可能
缺失或误判，中文专业库仍需独立补检。

## 5. 授权数据库检索与导入

在本人或机构正常授权范围内检索。优先用 Zotero Connector 保存题录；若网页识别失败，
使用数据库提供的 EndNote、RefWorks、NoteExpress、RIS 或 BibTeX 引用导出后导入 Zotero。
不共享账号、不绕过验证码、不批量抓取受限全文。

为本项目建立 Zotero collection（建议 `CN-项目简称`），并使用来源标签：

```text
source:cnki / source:wanfang / source:cqvip / source:nstl
source:pubscholar / source:ncpssd / source:chinaxiv / source:sinomed
language:zh
screening:pending / screening:include / screening:exclude
```

## 6. 合并、去重与引用插入

```bash
uv run sciops zotero collections
uv run sciops zotero export-csv --collection COLLECTION_KEY \
  --output literature/zotero-cn.csv
uv run sciops literature merge literature/openalex-zh.csv literature/zotero-cn.csv \
  --output literature/combined.csv
uv run sciops zotero export-csl --collection COLLECTION_KEY \
  --output manuscript/references.json
```

Quarto/Pandoc 稿件在 YAML 中设置：

```yaml
bibliography: references.json
```

正文用 `[@条目ID]` 插入引用。Word/LibreOffice 稿件使用 Zotero 官方文字处理器插件插入，
不要把手工编号作为长期事实源。

## 7. 去重与筛选规则

去重顺序：DOI → 规范化标题 → 作者+年份+期刊 → 摘要/数据来源人工核验。中文与英文版本、
预印本与正式发表版、学位论文与拆分期刊论文不得仅凭相似标题自动删除，应建立版本关联。

筛选采用题名/摘要初筛和全文复筛。每条排除决定使用预先定义的原因代码，并在
`03_literature_matrix.csv` 保留决定、决策人、日期与原文证据位置。

## 8. 复现与质量检查

- [ ] 每个数据库的完整检索式、字段、日期、时间范围和命中数已记录。
- [ ] 同义词包含领域旧称、中文全称/缩写和必要英文词。
- [ ] 至少一个综合中文库和一个适配学科的专业/公益库完成补检。
- [ ] 自动初检与授权数据库结果已合并，重复项已人工复核。
- [ ] 纳入文献已阅读原文，卷期页码、DOI、版本、撤稿/勘误已核验。
- [ ] 预印本、学位论文、会议论文和正式期刊版本被正确区分。
- [ ] 受限 PDF、账号、令牌和 API key 未进入 Git、公开研究包或 Release。
- [ ] 投稿前已执行更新检索，并记录新增文献对结论的影响。
