import platform
from pathlib import Path

import pytest

from sciops.figures import FigureError, load_figure_spec, render_origin


def test_load_figure_spec_resolves_relative_paths(tmp_path: Path) -> None:
    (tmp_path / "data.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    spec_path = tmp_path / "figure.yaml"
    spec_path.write_text(
        "data: data.csv\nx: x\ny: y\nkind: scatter\noutputs:\n  - output/figure.svg\n",
        encoding="utf-8",
    )
    spec = load_figure_spec(spec_path)
    assert spec.data == (tmp_path / "data.csv").resolve()
    assert spec.outputs == ((tmp_path / "output/figure.svg").resolve(),)
    assert spec.kind == "scatter"


def test_load_figure_spec_rejects_missing_fields(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("x: x\n", encoding="utf-8")
    with pytest.raises(FigureError, match="缺少字段"):
        load_figure_spec(path)


@pytest.mark.skipif(platform.system() == "Windows", reason="Linux/macOS guard only")
def test_origin_backend_has_clear_platform_guard(tmp_path: Path) -> None:
    spec_path = tmp_path / "figure.yaml"
    spec_path.write_text(
        "data: data.csv\nx: x\ny: y\noutputs:\n  - figure.svg\n",
        encoding="utf-8",
    )
    spec = load_figure_spec(spec_path)
    with pytest.raises(FigureError, match="Windows"):
        render_origin(spec)
