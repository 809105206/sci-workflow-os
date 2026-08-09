import csv
from pathlib import Path

from sciops.literature import _record_from_zotero_item, _zotero_year, deduplicate_csv, merge_csv


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


def test_zotero_chinese_item_is_normalized() -> None:
    item = {
        "key": "CNKI1234",
        "data": {
            "itemType": "journalArticle",
            "title": "基于双重机器学习的钻井参数研究",
            "creators": [
                {"creatorType": "author", "firstName": "三", "lastName": "张"},
                {"creatorType": "author", "name": "李四"},
            ],
            "publicationTitle": "石油钻探技术",
            "date": "2025-06-15",
            "DOI": "10.1234/example",
            "url": "https://example.cn/article",
            "language": "zh-CN",
            "abstractNote": "中文摘要",
            "tags": [{"tag": "双重机器学习"}, {"tag": "机械钻速"}],
        },
    }

    record = _record_from_zotero_item(item)

    assert record["zotero_key"] == "CNKI1234"
    assert record["publication_year"] == 2025
    assert record["source"] == "石油钻探技术"
    assert record["authors"] == "张三; 李四"
    assert record["keywords"] == "双重机器学习; 机械钻速"
    assert record["database"] == "Zotero"


def test_zotero_year_accepts_chinese_date() -> None:
    assert _zotero_year("2024年12月") == 2024
    assert _zotero_year("无日期") == ""


def test_merge_csv_deduplicates_across_databases(tmp_path: Path) -> None:
    openalex = tmp_path / "openalex.csv"
    zotero = tmp_path / "zotero.csv"
    openalex.write_text(
        "doi,title,database,abstract\n10.1/shared,同一篇论文,OpenAlex,\n",
        encoding="utf-8",
    )
    zotero.write_text(
        "doi,title,database,abstract,language\n"
        "https://doi.org/10.1/SHARED,同一篇论文,Zotero,更完整摘要,zh-CN\n"
        ",另一篇论文,Zotero,,zh-CN\n",
        encoding="utf-8",
    )

    output, before, after = merge_csv([openalex, zotero], tmp_path / "combined.csv")

    assert output.exists()
    assert before == 3
    assert after == 2
    with output.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    shared = next(row for row in rows if row["doi"].lower().endswith("shared"))
    assert set(shared["database"].split("; ")) == {"OpenAlex", "Zotero"}
    assert shared["abstract"] == "更完整摘要"
