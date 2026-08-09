# SCI Workflow OS

[![CI](https://github.com/809105206/sci-workflow-os/actions/workflows/ci.yml/badge.svg)](https://github.com/809105206/sci-workflow-os/actions/workflows/ci.yml)
[![Documentation](https://github.com/809105206/sci-workflow-os/actions/workflows/pages.yml/badge.svg)](https://809105206.github.io/sci-workflow-os/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个以 `SCI.md` 为总规范、以 GitHub 为协作中枢的开源科研工作台。它把选题、文献、方案、数据、实验、写作、选刊、投稿、返修和发表归档从“说明文档”变成可执行、可审计、可分享、可下载的工作流。

## 已具备的能力

- `sciops` 命令行：项目初始化、G0–G10 阶段审计、联网文献检索、去重、DOI/BibTeX 获取和安全打包。
- 12 项最小可复现工作包与 G0–G10 阶段门模板。
- OpenAlex 联网检索和 Zotero API 接入；API 密钥仅从本地环境变量读取。
- DVC/Pandera 可选数据栈：数据版本、实验管线与表格数据验证。
- Quarto/Pandoc 写作栈：默认生成网页与 Word；安装 TinyTeX 后可启用 PDF。
- GitHub Issues、Pull Requests、Actions、Pages 与 Releases：多人协作、在线站点和版本下载。
- CI：代码测试、结构审计、文档构建和链接检查。

## 快速开始

### 1. 安装

```bash
./scripts/bootstrap.sh
```

该脚本使用 `uv` 创建隔离环境，并安装默认能力和数据工具。不会把 API 密钥写入仓库。

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

Crossref 检索无需 key。需要 OpenAlex 的引文网络与开放获取字段时，使用 `literature search`；OpenAlex 自 2026-02-13 起要求 API key，应先申请免费 key，再在未提交的 `.env` 或终端环境中设置：

```bash
export OPENALEX_EMAIL="you@example.com"
export OPENALEX_API_KEY="your-key"
```

### 5. 审计阶段完成度

```bash
uv run sciops audit workspace/my-paper
uv run sciops audit workspace/my-paper --strict
```

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
| `src/sciops/` | 可执行命令行工具 |
| `templates/project/` | 可复制研究工作包 |
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
