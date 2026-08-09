from pathlib import Path

import yaml

from sciops.onboarding import (
    activate_project,
    build_resume_report,
    checkpoint_project,
    enable_trusted_mode,
)
from sciops.project import initialize_project


def test_resume_and_checkpoint_active_project(tmp_path: Path, monkeypatch) -> None:
    source_repository = Path(__file__).parents[1]
    monkeypatch.setenv("SCIOPS_REPOSITORY_ROOT", str(source_repository))
    project = initialize_project(tmp_path / "repo/workspace/study", title="Test Study")

    repository = tmp_path / "repo"
    (repository / "codex-policy.toml").write_text(
        'schema_version = 1\nmode = "guided"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("SCIOPS_REPOSITORY_ROOT", str(repository))

    activate_project(project)
    report = build_resume_report()
    assert report["active_project"] == str(project.resolve())
    assert report["active_stage"] == "G0"
    assert report["next_actions"]

    state_path = checkpoint_project(
        None,
        completed="Search protocol drafted.",
        stage="G1",
        next_actions=["Run the pilot search."],
        decisions=["Use grouped validation."],
        blockers=[],
    )
    assert "Search protocol drafted." in state_path.read_text(encoding="utf-8")
    updated = build_resume_report()
    assert updated["active_stage"] == "G1"
    assert updated["next_actions"] == ["Run the pilot search."]

    local_policy = enable_trusted_mode()
    assert 'mode = "trusted"' in local_policy.read_text(encoding="utf-8")
    assert build_resume_report()["policy"]["mode"] == "trusted"


def test_resume_without_project_requests_new_direction(tmp_path: Path, monkeypatch) -> None:
    repository = tmp_path / "empty-repository"
    repository.mkdir()
    (repository / "codex-policy.toml").write_text(
        'schema_version = 1\nmode = "guided"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("SCIOPS_REPOSITORY_ROOT", str(repository))

    report = build_resume_report()
    assert report["status"] == "needs_project"
    assert "research field or direction" in report["next_action"]


def test_completed_project_requests_separate_new_direction(tmp_path: Path, monkeypatch) -> None:
    source_repository = Path(__file__).parents[1]
    monkeypatch.setenv("SCIOPS_REPOSITORY_ROOT", str(source_repository))
    project = initialize_project(tmp_path / "repo/workspace/study", title="Finished Study")
    repository = tmp_path / "repo"
    (repository / "codex-policy.toml").write_text(
        'schema_version = 1\nmode = "guided"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("SCIOPS_REPOSITORY_ROOT", str(repository))

    gates_path = project / "stage-gates.yaml"
    gates = yaml.safe_load(gates_path.read_text(encoding="utf-8"))
    for stage in gates["stages"].values():
        stage["status"] = "passed"
    gates_path.write_text(
        yaml.safe_dump(gates, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    alignment = project / "manuscript/bilingual-alignment.csv"
    rows = [
        "section,zh_status,en_status,claims_aligned,numbers_units_aligned,"
        "citations_aligned,figures_tables_aligned,scope_aligned,verified_by,"
        "verified_at,notes"
    ]
    for section in (
        "title",
        "abstract",
        "introduction",
        "methods",
        "results",
        "discussion",
        "conclusion",
        "declarations",
    ):
        rows.append(f"{section},complete,complete,true,true,true,true,true,Reviewer,2026-08-10,")
    alignment.write_text("\n".join(rows) + "\n", encoding="utf-8")
    (project / "09_claim_evidence_map.md").write_text(
        "| ID | 稿件位置 | 中文论点 | English claim | 论据或数据来源 | 实验/分析 | "
        "该实验检验的内容 | 主要结果与不确定性 | 排除的替代解释 | 对全文论证的作用 | "
        "科学或工程意义 | 图表/输出/引文 | 状态 |\n"
        "| C01 | Results | 论点 | Claim | Dataset | Analysis | Proposition | "
        "Estimate and interval | Alternative | Main support | Bounded significance | "
        "Figure 1 | verified |\n",
        encoding="utf-8",
    )
    english_section = (
        "This section reports evidence, design, results, uncertainty, limitations, and scope "
        "without adding unsupported claims. " * 10
    )
    chinese_section = (
        "本节陈述证据、研究设计、主要结果、不确定性、局限性和适用范围，"
        "所有论点均保持证据边界。" * 15
    )
    (project / "manuscript/en/paper.qmd").write_text(
        "\n".join(
            f"## {section.title()}\n\n{english_section}"
            for section in (
                "abstract",
                "introduction",
                "methods",
                "results",
                "discussion",
                "conclusion",
            )
        ),
        encoding="utf-8",
    )
    (project / "manuscript/zh/paper.qmd").write_text(
        "\n".join(
            f"## {section}\n\n{chinese_section}"
            for section in ("摘要", "引言", "方法", "结果", "讨论", "结论")
        ),
        encoding="utf-8",
    )

    activate_project(project)
    report = build_resume_report()
    assert report["status"] == "project_completed"
    assert "new research direction" in report["next_actions"][0]
