import zipfile
from pathlib import Path

from sciops.project import initialize_project, package_project


def test_initialize_project(tmp_path: Path, monkeypatch) -> None:
    repository = Path(__file__).parents[1]
    monkeypatch.setenv("SCIOPS_REPOSITORY_ROOT", str(repository))
    destination = initialize_project(tmp_path / "study", title="Test Study")
    assert (destination / "01_project_charter.md").exists()
    assert "Test Study" in (destination / "01_project_charter.md").read_text(encoding="utf-8")
    chinese_strategy = destination / "literature/chinese-search-strategy.md"
    assert chinese_strategy.exists()
    assert "Test Study" in chinese_strategy.read_text(encoding="utf-8")
    assert (destination / "literature/chinese-download-decisions.csv").exists()
    assert (destination / "writing-style.yaml").exists()
    assert (destination / ".vale.ini").exists()
    assert (destination / "figures/rop-effect.example.yaml").exists()
    assert (destination / "research-state.yaml").exists()


def test_package_excludes_secrets_and_raw_data(tmp_path: Path) -> None:
    source = tmp_path / "study"
    (source / "data/raw").mkdir(parents=True)
    (source / ".quarto/idx").mkdir(parents=True)
    (source / ".dvc/tmp").mkdir(parents=True)
    (source / "workspace/private-study").mkdir(parents=True)
    (source / "console/node_modules/package").mkdir(parents=True)
    (source / "console/dist").mkdir(parents=True)
    (source / ".codegraph").mkdir(parents=True)
    (source / "notes.md").write_text("public", encoding="utf-8")
    (source / ".env").write_text("TOKEN=secret", encoding="utf-8")
    (source / ".sciops-active").write_text("workspace/private-study", encoding="utf-8")
    (source / ".sciops-local.toml").write_text('mode = "trusted"', encoding="utf-8")
    (source / ".codegraph/index.db").write_text("generated", encoding="utf-8")
    (source / "data/raw/private.csv").write_text("secret", encoding="utf-8")
    (source / ".quarto/idx/cache.json").write_text("generated", encoding="utf-8")
    (source / ".dvc/config").write_text("[core]", encoding="utf-8")
    (source / ".dvc/tmp/runtime").write_text("generated", encoding="utf-8")
    (source / "workspace/private-study/notes.md").write_text("secret", encoding="utf-8")
    (source / "console/node_modules/package/index.js").write_text("generated", encoding="utf-8")
    (source / "console/dist/index.html").write_text("console", encoding="utf-8")

    result = package_project(source, tmp_path / "package.zip")
    with zipfile.ZipFile(result.output) as archive:
        names = set(archive.namelist())
    assert "notes.md" in names
    assert "MANIFEST.sha256" in names
    assert ".env" not in names
    assert ".sciops-active" not in names
    assert ".sciops-local.toml" not in names
    assert ".codegraph/index.db" not in names
    assert "data/raw/private.csv" not in names
    assert ".quarto/idx/cache.json" not in names
    assert ".dvc/config" in names
    assert ".dvc/tmp/runtime" not in names
    assert "workspace/private-study/notes.md" not in names
    assert "console/node_modules/package/index.js" not in names
    assert "console/dist/index.html" in names
    assert "SCI-WORKFLOW-CONSOLE.html" in names
