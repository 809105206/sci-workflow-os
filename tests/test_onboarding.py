from pathlib import Path

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
