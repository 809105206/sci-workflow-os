from pathlib import Path

import yaml

from sciops.audit import audit_project
from sciops.project import initialize_project


def test_template_has_complete_structure() -> None:
    root = Path(__file__).parents[1] / "templates" / "project"
    result = audit_project(root)
    assert result.passed, result.errors
    assert set(result.stages) == {f"G{i}" for i in range(11)}


def test_strict_template_is_not_false_positive() -> None:
    root = Path(__file__).parents[1] / "templates" / "project"
    result = audit_project(root, strict=True)
    assert not result.passed
    assert any("尚未通过" in error for error in result.errors)


def test_g7_pass_requires_verified_bilingual_outputs(tmp_path: Path, monkeypatch) -> None:
    repository = Path(__file__).parents[1]
    monkeypatch.setenv("SCIOPS_REPOSITORY_ROOT", str(repository))
    project = initialize_project(tmp_path / "study", title="Bilingual Study")
    gates_path = project / "stage-gates.yaml"
    gates = yaml.safe_load(gates_path.read_text(encoding="utf-8"))
    gates["stages"]["G7"]["status"] = "passed"
    gates_path.write_text(
        yaml.safe_dump(gates, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    result = audit_project(project)
    assert not result.passed
    assert any("双语对齐未完成" in error for error in result.errors)
    assert any("论点—证据—实验—作用—意义链" in error for error in result.errors)
