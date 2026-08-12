# SCI Workflow OS

[![CI](https://github.com/809105206/sci-workflow-os/actions/workflows/ci.yml/badge.svg)](https://github.com/809105206/sci-workflow-os/actions/workflows/ci.yml)
[![Documentation](https://github.com/809105206/sci-workflow-os/actions/workflows/pages.yml/badge.svg)](https://809105206.github.io/sci-workflow-os/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**公开 Research Console：<https://809105206.github.io/sci-workflow-os/console/>**

**即时部署：<https://sci-workflow-console.z809105206.chatgpt.site>**

一个以 `SCI.md` 为总规范、以 GitHub 为协作中枢的开源科研工作台。它把选题、文献、方案、数据、实验、写作、选刊、投稿、返修和发表归档从“说明文档”变成可执行、可审计、可分享、可下载的工作流。

## 已具备的能力

- `sciops` 命令行：项目初始化、G0–G10 阶段审计、联网文献检索、去重、DOI/BibTeX 获取和安全打包。
- Codex 即开即用接管层：`AGENTS.md`、仓库级科研编排 Skill、活动项目指针和 `research-state.yaml` 共同恢复当前阶段与下一动作。
- 课题级科研记忆：受字符预算约束的当前上下文、带来源语义记忆、追加式里程碑和按需历史检索；不同课题完全隔离。
- 可迁移本机凭据包：前端或双击脚本一键导出/导入 OpenAlex、Zotero 配置；服务注册表可扩展，Git、研究 ZIP 和 Release 强制排除。
- CodeGraph 可选本地索引：为 Codex 提供代码结构、调用关系和影响分析，并在文件修改或重新连接时增量同步。
- Research Console 前端：研究总览、文献纳入决策、稿件实时质检，以及无需安装软件的浏览器科研作图。
- 14 类最小可复现工作包与 G0–G10 阶段门模板，适用于任意新课题，不继承上一项目的研究内容。
- 项目级通用中文文献模块：OpenAlex 中文过滤自动检索，知网/万方/维普/PubScholar/NSTL/国家哲社中心/ChinaXiv/SinoMed 正式入口，题名/链接/摘要候选预览，下载决策表，以及 Zotero 统一导入、去重与 CSL JSON 引用。
- 本地只读 MCP：Codex/兼容客户端可调用中文来源目录、OpenAlex 中文检索和 Zotero collections/题录；API 密钥仅从本地环境变量读取。
- DVC/Pandera 可选数据栈：数据版本、实验管线与表格数据验证。
- Quarto/Pandoc 写作栈：默认生成网页与 Word；安装 TinyTeX 后可启用 PDF。
- 标准化写作质量门：正文仅使用陈述句，阻断疑问句、对话式元话语和占位符，并提示无证据强化与模板化表达。
- 双语成稿与论证闭环：每篇论文强制输出中文全文、英文全文、全文大纲、论点—证据—实验—作用—意义链和逐节双语对齐记录。
- 零门槛图表工坊：单个离线 HTML 本地读取 CSV，导出 SVG、PNG、清洗 CSV 和可复现 YAML，不依赖 OriginPro、MATLAB 或 Python。
- 开放批量绘图：Windows、macOS 与 Linux 一键安装 uv、Python 3.12、Matplotlib 和 Plotly；OriginPro 仅作为已有许可证用户的可选适配器。
- GitHub Issues、Pull Requests、Actions、Pages 与 Releases：多人协作、在线站点和版本下载。
- CI：代码测试、结构审计、文档构建和链接检查。

## 快速开始

### Codex 用户：一次设置后直接说明研究方向

Windows 普通模式双击 `SETUP-CODEX.cmd`。确认信任该仓库并允许自动配置缺失的用户级工具时，双击 `SETUP-CODEX-TRUSTED.cmd`。macOS/Linux 执行：

```bash
./SETUP-CODEX.sh
# 可信模式
./SETUP-CODEX.sh --trusted
```

设置完成后用 Codex 打开仓库，直接说明研究方向、目标或现有数据。没有活动项目且未给出方向时，Codex 会先询问宽泛研究方向和已有数据/资源约束；不会沿用上一项目的题目、数据、方法或结论。随后 Codex 读取 `AGENTS.md`，调用 `sciops codex resume` 恢复或建立活动项目，并从第一项未完成任务继续。系统级权限、登录、凭据、外部发布和不可逆操作不会因可信模式而绕过平台安全边界。完整机制见[Codex 一键接管与连续科研](https://809105206.github.io/sci-workflow-os/docs/codex-takeover.html)。

旧项目首次启用分层记忆时执行：

```bash
uv run --frozen sciops memory init workspace/my-paper
uv run --frozen sciops codex resume --json
```

原理和记忆治理见[课题级科研记忆](https://809105206.github.io/sci-workflow-os/docs/memory.html)。

### 1. 安装

```bash
./scripts/bootstrap.sh
```

该脚本使用 `uv` 创建隔离环境，并安装默认能力和数据工具。不会把 API 密钥写入仓库。

浏览器前端可以直接使用在线版本，也可以在本地开发模式运行：

```bash
./scripts/start-console.sh
```

Release 下载包根目录包含 `SCI-WORKFLOW-CONSOLE.html`。双击该文件即可独立运行图表工坊和其他前端页面，不需要命令行、Python、网络或安装过程。CSV 只在当前浏览器中处理，不会上传。`OPEN-CONSOLE.cmd` 和 `OPEN-CONSOLE.sh` 保留为兼容入口。

需要批量制图、脚本复现或 CI 时，Windows 双击 `INSTALL-PLOTTING.cmd`；macOS/Linux 执行 `./INSTALL-PLOTTING.sh`。安装器为当前项目配置隔离的开源绘图环境，不要求 OriginPro 或 MATLAB。

### 2. 检查环境

```bash
uv run sciops doctor
```

### 3. 创建一个研究项目

```bash
uv run sciops init workspace/my-paper --title "My SCI Project"
```

### 4. 联网检索文献

```bash
uv run sciops literature crossref-search \
  "multimodal well logging velocity prediction" \
  --limit 50 \
  --output workspace/my-paper/literature/crossref.csv
```

Crossref 检索无需 key。需要 OpenAlex 的引文网络与开放获取字段时，使用 `literature search`；OpenAlex 自 2026-02-13 起要求 API key，应先申请免费 key。CLI 会从当前目录或其父目录自动读取未提交的 `.env`：

```bash
cp .env.example .env
# 编辑 .env，填写 OPENALEX_API_KEY；不要将真实密钥提交到 Git。
uv run sciops doctor
```

PowerShell 可用 `Copy-Item .env.example .env`。已在终端设置的环境变量优先于 `.env`，适合 CI/CD 使用。

凭据申请入口：

- OpenAlex：登录 [API settings](https://openalex.org/settings/api) 后创建免费 key，填入 `OPENALEX_API_KEY`。
- Zotero：登录 [API Keys](https://www.zotero.org/settings/keys)，创建仅供本工具使用的 private key。只拉取文献时授予 library read access 即可；同一页面显示的数字 user ID 填入 `ZOTERO_LIBRARY_ID`，生成的 key 填入 `ZOTERO_API_KEY`。个人库保持 `ZOTERO_LIBRARY_TYPE=user`；群组库改为 `group` 并使用数字 group ID。

真实凭据只保存在本机 `.env`、未跟踪的 `.sciops-credentials.local.json`、环境变量或 CI 的加密 Secrets 中，不要放入 issue、聊天、README、命令历史或 Git 提交。把当前 `.env` 转为可重复使用的本机 JSON：

```bash
uv run --frozen sciops credentials export-env
uv run --frozen sciops credentials export
uv run --frozen sciops credentials status
# 新电脑或新副本
uv run --frozen sciops credentials import-json /path/to/your-credentials.json
```

详情见[本机凭据 JSON](https://809105206.github.io/sci-workflow-os/docs/credentials.html)。GitHub CLI OAuth 不复制到该 JSON。

完整本地项目还可通过 `OPEN-CONSOLE` 进入“凭据中心”，一键下载或导入私有 JSON。Windows 用户可直接双击 `EXPORT-CREDENTIALS.cmd`。该包只包含注册服务的 API 凭据，不包含网站密码、Cookie 或浏览器登录态。

### 中文文献：开放检索 + 授权数据库 + Zotero

此能力适用于以后任何中文或英文期刊项目，不与某篇论文绑定。先列出跨学科与专业来源，并用 OpenAlex 中文过滤做自动初检：

```bash
uv run sciops literature chinese-sources
uv run sciops literature search-cn "你的中文主题词" \
  --from-year 2020 --to-year 2026 --limit 200 \
  --output workspace/my-paper/literature/openalex-zh.csv
```

本项目不绕过数据库登录、验证码或访问控制。再用 Zotero Connector 或数据库引用导出功能，将本人/机构有权访问的中文题录保存到项目专用 Zotero collection：

```bash
uv run sciops zotero collections
uv run sciops zotero export-csv --collection COLLECTION_KEY \
  --output workspace/my-paper/literature/zotero-cn.csv
uv run sciops literature merge \
  workspace/my-paper/literature/zotero-cn.csv \
  workspace/my-paper/literature/openalex-zh.csv \
  --output workspace/my-paper/literature/combined.csv
uv run sciops literature preview workspace/my-paper/literature/combined.csv \
  --require "研究对象同义词1,研究对象同义词2" \
  --prefer "方法词1,方法词2" \
  --output workspace/my-paper/literature/chinese-candidate-preview.md \
  --decisions workspace/my-paper/literature/chinese-download-decisions.csv
uv run sciops zotero export-csl --collection COLLECTION_KEY \
  --output workspace/my-paper/manuscript/references.json
```

完整选库、通用概念块检索、标签、去重、插入引用和审计规则见[通用中文文献检索、导入与引用](https://809105206.github.io/sci-workflow-os/docs/chinese-literature.html)。

### 本地 MCP（Codex/兼容客户端）

仓库自带 `.codex/config.toml` 和 `sciops-mcp`。将项目设为 trusted、完成安装并重启对应本地客户端后，用 `/mcp` 或 `codex mcp list` 检查。ChatGPT 网页版不会读取本机项目配置。

```bash
./scripts/bootstrap.sh
uv run --frozen sciops-mcp
```

直接启动后保持安静并等待输入是正常现象。配置、八个只读工具、凭据边界和远程部署说明见[中文文献 MCP 接入](https://809105206.github.io/sci-workflow-os/docs/mcp.html)。

### 5. 审计阶段完成度

```bash
uv run sciops audit workspace/my-paper
uv run sciops audit workspace/my-paper --strict
```

稿件标准化质检：

```bash
uv run sciops writing lint workspace/my-paper/manuscript/zh/paper.qmd --strict
uv run sciops writing lint workspace/my-paper/manuscript/en/paper.qmd --strict
uv run sciops writing lint workspace/my-paper/manuscript/paper.qmd --strict
```

科研图表：

```bash
uv sync --extra figures
uv run sciops figure doctor
uv run sciops figure render \
  workspace/my-paper/figures/effect-estimate.example.yaml \
  --backend auto
```

首次使用者可跳过上述命令，直接双击 `SCI-WORKFLOW-CONSOLE.html` 完成 CSV 作图。需要开放批量绘图环境时，再运行对应系统的 `INSTALL-PLOTTING` 一键安装器。

普通模式检查结构；严格模式还检查阶段状态、空文件和未完成占位符。

数据质量验证：

```bash
uv run sciops data validate-csv data.csv data-schema.yaml
```

### 6. 生成可下载研究包

```bash
uv run sciops package workspace/my-paper --output dist/my-paper.zip
```

打包器默认排除 `.env`、令牌、Git 元数据、缓存、原始数据和模型权重，并生成 SHA-256 清单。

### 7. 预览网站与手册

```bash
./scripts/render.sh
```

站点输出到 `_site/`；推送到 GitHub 后由 Actions 自动部署 GitHub Pages。

## 项目结构

| 路径 | 用途 |
| --- | --- |
| `SCI.md` | G0–G10 总规范与质量标准 |
| `AGENTS.md` | Codex 自动载入的仓库接管、权限与验证协议 |
| `.agents/skills/run-sci-workflow/` | 随仓库分发的端到端科研编排 Skill |
| `codex-policy.toml` | 默认自动化与确认边界 |
| `src/sciops/` | 可执行命令行工具 |
| `console/` | Research Console 浏览器前端 |
| `templates/project/` | 可复制研究工作包 |
| `.codex/config.toml` | 可分享的项目级本地 MCP 配置 |
| `manuscript/` | Quarto 论文示例与参考文献 |
| `docs/` | 架构、审计、工具与协作说明 |
| `.github/` | Issue、PR、CI、Pages、Release 自动化 |
| `tests/` | 离线单元测试 |

## 设计原则

1. **证据优先**：工具不能替代研究设计、领域判断或人工核验。
2. **默认安全**：原始/保密数据、API 密钥和审稿材料默认不提交、不打包。
3. **单一事实源**：数据、实验、稿件和阶段决定均版本化，避免多个“最终版”。
4. **渐进增强**：默认栈轻量；系统综述、DVC 远程仓储、GPU 实验等按需启用。
5. **开放但不失真**：在线检索结果只是候选证据，引用前必须阅读并核验原文。

## 许可证

MIT。第三方工具仍分别遵守其上游许可证，本仓库不复制或重新授权其代码。
