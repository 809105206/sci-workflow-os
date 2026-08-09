import csv
from pathlib import Path

from sciops.literature import deduplicate_csv


def test_dedupe_prefers_doi_and_title(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["doi", "title", "source"])
        writer.writeheader()
        writer.writerows(
            [
                {"doi": "https://doi.org/10.1/ABC", "title": "Same paper", "source": "A"},
                {"doi": "10.1/abc", "title": "Same paper", "source": ""},
                {"doi": "", "title": "A New Method!", "source": "B"},
                {"doi": "", "title": "a new method", "source": ""},
            ]
        )

    output, before, after = deduplicate_csv(source, tmp_path / "output.csv")
    assert output.exists()
    assert before == 4
    assert after == 2
