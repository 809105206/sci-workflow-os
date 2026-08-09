# Contributing

## 协作方式

1. 用 Issue 提出选题、阶段门评审、缺陷或功能需求。
2. 从 `main` 创建短分支，不直接在主分支修改关键证据。
3. 一个 Pull Request 只处理一个清楚问题，并关联 Issue。
4. 数据、统计结果、引用或结论发生变化时，在 PR 中给出可复核证据。
5. 至少一名未直接执行该改动的成员完成审查后再合并。

## 本地检查

```bash
uv sync --extra data --group dev
uv run ruff check .
uv run pytest
uv run sciops audit templates/project
```

## 科研完整性

- 不提交个人敏感信息、企业保密数据、真实 API 密钥或未授权全文。
- 不把自动检索元数据当成已核验引用。
- 改动数据排除、切分、指标或分析计划时，必须说明时间和理由。
- 作者、贡献和利益冲突按项目及目标期刊政策处理。
