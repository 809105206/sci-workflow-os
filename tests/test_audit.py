from pathlib import Path

from sciops.audit import audit_project


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
