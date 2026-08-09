from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WritingIssue:
    rule: str
    severity: str
    line: int
    match: str
    message: str

    def as_dict(self) -> dict[str, str | int]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WritingLintResult:
    source: Path
    issues: tuple[WritingIssue, ...]
    checked_lines: int
    strict: bool

    @property
    def errors(self) -> int:
        return sum(issue.severity == "error" for issue in self.issues)

    @property
    def warnings(self) -> int:
        return sum(issue.severity == "warning" for issue in self.issues)

    @property
    def score(self) -> int:
        return max(0, 100 - self.errors * 15 - self.warnings * 5)

    @property
    def passed(self) -> bool:
        return self.errors == 0 and (not self.strict or self.warnings == 0)

    def as_dict(self) -> dict[str, object]:
        return {
            "source": str(self.source),
            "strict": self.strict,
            "passed": self.passed,
            "score": self.score,
            "checked_lines": self.checked_lines,
            "errors": self.errors,
            "warnings": self.warnings,
            "issues": [issue.as_dict() for issue in self.issues],
        }


RULES: tuple[tuple[str, str, re.Pattern[str], str], ...] = (
    (
        "question",
        "error",
        re.compile(r"[?？]"),
        "正文只允许陈述句。将疑问句改写为研究目标、假设或已检验的陈述。",
    ),
    (
        "direct-address",
        "error",
        re.compile(
            r"(?:当然可以|如有需要|欢迎(?:读者)?|让我们|请(?:注意|看|考虑|参阅)|"
            r"I hope this helps|let us|you can|please note)",
            re.IGNORECASE,
        ),
        "删除面向读者的指令、邀请和对话式表达。",
    ),
    (
        "generation-meta",
        "error",
        re.compile(
            r"(?:作为(?:一个)?AI|根据您的要求|以下是|下面将|接下来(?:我们)?|"
            r"本文将(?:首先|依次)|as an AI|as requested|here(?:'s| is) the)",
            re.IGNORECASE,
        ),
        "删除生成过程、任务说明和结构播报，只保留研究内容。",
    ),
    (
        "placeholder",
        "error",
        re.compile(r"(?:TODO|TBD|FIXME|待补充|待填写|待核实|XX期刊|X+\s*%|\{\{[^}]+\}\})", re.I),
        "提交稿中不得保留占位符或待办标记。",
    ),
    (
        "unsupported-emphasis",
        "warning",
        re.compile(
            r"(?:至关重要|不言而喻|毋庸置疑|显著(?:提升|改善|降低|增加)|"
            r"具有重要的(?:理论|实践|现实)意义|填补了[^。.!！]{0,20}空白|"
            r"groundbreaking|pivotal|remarkably|significantly improved)",
            re.I,
        ),
        "将空泛强化改为有数值、区间、图表或引文支持的限定陈述。",
    ),
    (
        "template-phrase",
        "warning",
        re.compile(
            r"(?:值得注意的是|需要指出的是|总体而言|综上所述(?:可以看出)?|"
            r"深入探讨|全面揭示|提供了新的视角|有望为|"
            r"it is (?:important|worthwhile) to note|delve into|"
            r"in today's rapidly evolving|this study sheds light on)",
            re.I,
        ),
        "删除模板化过渡语，直接陈述事实、分析或边界。",
    ),
)


def _iter_content_lines(text: str) -> list[tuple[int, str, bool]]:
    lines = text.splitlines()
    content: list[tuple[int, str, bool]] = []
    in_front_matter = bool(lines and lines[0].strip() == "---")
    in_fence = False
    in_math = False

    for number, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if in_front_matter:
            if number > 1 and stripped == "---":
                in_front_matter = False
            else:
                title = re.match(r"^(?:title|subtitle):\s*[\"']?(.*?)[\"']?$", stripped, re.I)
                if title and title.group(1):
                    content.append((number, title.group(1), False))
            continue
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if stripped == "$$":
            in_math = not in_math
            continue
        if in_fence or in_math or not stripped:
            continue
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                content.append((number, heading, False))
            continue
        if stripped.startswith(("|", ">", "<!--", "![", ":::")):
            continue
        if re.match(r"^\[[^]]+\]:\s+", stripped):
            continue
        stripped = re.sub(r"^(?:[-*+] |\d+[.)]\s+)", "", stripped)
        if stripped:
            content.append((number, stripped, True))
    return content


def _supported_emphasis(line: str) -> bool:
    evidence = (
        re.search(r"\d", line)
        or re.search(r"\[@[^]]+\]", line)
        or re.search(r"\([A-Z][^)]*,\s*20\d{2}[a-z]?\)", line)
        or re.search(r"(?:图|表|Figure|Table)\s*[A-Za-z0-9一二三四五六七八九十]+", line, re.I)
    )
    return bool(evidence)


def lint_text(
    text: str,
    *,
    source: Path = Path("<text>"),
    strict: bool = False,
) -> WritingLintResult:
    issues: list[WritingIssue] = []
    content = _iter_content_lines(text)

    for line_number, line, requires_ending in content:
        for rule, severity, pattern, message in RULES:
            for match in pattern.finditer(line):
                if rule == "unsupported-emphasis" and _supported_emphasis(line):
                    continue
                issues.append(
                    WritingIssue(
                        rule=rule,
                        severity=severity,
                        line=line_number,
                        match=match.group(0),
                        message=message,
                    )
                )
        if requires_ending and len(line) >= 12 and not re.search(r"[。.!！；;：:]$", line):
            issues.append(
                WritingIssue(
                    rule="declarative-ending",
                    severity="warning",
                    line=line_number,
                    match=line[-30:],
                    message="完整正文句需要以陈述性标点结束。",
                )
            )

    return WritingLintResult(
        source=source,
        issues=tuple(issues),
        checked_lines=len(content),
        strict=strict,
    )


def lint_manuscript(path: Path, *, strict: bool = False) -> WritingLintResult:
    path = path.expanduser().resolve()
    text = path.read_text(encoding="utf-8")
    return lint_text(text, source=path, strict=strict)
