from pathlib import Path

from sciops.writing import lint_text


def test_declarative_evidence_bound_text_passes_strict() -> None:
    text = (
        "本文采用交叉拟合的双重机器学习方法估计参数效应。\n\n"
        "钻压增加 5% 与机械钻速提高 0.66 m/h 相关，95% 置信区间为 0.47–0.85 m/h。"
    )
    result = lint_text(text, strict=True)
    assert result.passed
    assert result.score == 100


def test_questions_meta_and_unsupported_emphasis_are_reported() -> None:
    text = "为什么该方法可靠？当然可以继续分析。结果显著提升了预测能力。"
    result = lint_text(text, strict=True)
    rules = {issue.rule for issue in result.issues}
    assert {"question", "direct-address", "unsupported-emphasis"} <= rules
    assert result.errors == 2
    assert not result.passed


def test_titles_and_headings_are_checked_but_code_is_ignored() -> None:
    text = """---
title: Why?
---
# 如何开展研究？
```python
prompt = "Can this run?"
```
模型估计量在给定条件下具有渐近正态性。
"""
    result = lint_text(text, source=Path("paper.qmd"), strict=True)
    assert not result.passed
    assert result.errors == 2
    assert result.checked_lines == 3
