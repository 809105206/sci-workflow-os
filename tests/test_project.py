import zipfile
from pathlib import Path

from sciops.project import initialize_project, package_project


def test_initialize_project(tmp_path: Path, monkeypatch) -> None:
    repository = Path(__file__).parents[1]
    monkeypatch.setenv("SCIOPS_REPOSITORY_ROOT", str(repository))
    destination = initialize_project(tmp_path / "study", title="Test Study")
    assert (destination / "01_project_charter.md").exists()
    assert "Test Study" in (destination / "01_project_charter.md").read_text(encoding="utf-8")


def test_package_excludes_secrets_and_raw_data(tmp_path: Path) -> None:
    source = tmp_path / "study"
    (source / "data/raw").mkdir(parents=True)
    (source / ".quarto/idx").mkdir(parents=True)
    (source / "workspace/private-study").mkdir(parents=True)
    (source / "notes.md").write_text("public", encoding="utf-8")
    (source / ".env").write_text("TOKEN=secret", encoding="utf-8")
    (source / "data/raw/private.csv").write_text("secret", encoding="utf-8")
    (source / ".quarto/idx/cache.json").write_text("generated", encoding="utf-8")
    (source / "workspace/private-study/notes.md").write_text("secret", encoding="utf-8")

    result = package_project(source, tmp_path / "package.zip")
    with zipfile.ZipFile(result.output) as archive:
        names = set(archive.namelist())
    assert "notes.md" in names
    assert "MANIFEST.sha256" in names
    assert ".env" not in names
    assert "data/raw/private.csv" not in names
    assert ".quarto/idx/cache.json" not in names
    assert "workspace/private-study/notes.md" not in names
