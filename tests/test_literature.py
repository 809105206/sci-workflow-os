import csv
import json
from pathlib import Path

import pytest

from sciops.chinese_sources import list_chinese_literature_sources
from sciops.literature import (
    _build_openalex_filters,
    _record_from_zotero_item,
    _zotero_year,
    deduplicate_csv,
    merge_csv,
    prepare_candidate_previews,
    preview_csv,
    pull_zotero_csl_json,
)


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


def test_openalex_chinese_filters_include_language_and_complete_years() -> None:
    filters = _build_openalex_filters(language="ZH", from_year=2020, to_year=2026)

    assert filters == {
        "language": "zh",
        "from_publication_date": "2020-01-01",
        "to_publication_date": "2026-12-31",
    }


def test_openalex_year_range_rejects_reverse_order() -> None:
    with pytest.raises(ValueError, match="不能晚于"):
        _build_openalex_filters(from_year=2026, to_year=2020)


def test_chinese_source_registry_has_general_and_domain_sources() -> None:
    sources = {source["key"]: source for source in list_chinese_literature_sources()}

    assert {"openalex", "cnki", "wanfang", "cqvip", "ncpssd", "sinomed"} <= sources.keys()
    assert all(source["search_url"].startswith("https://") for source in sources.values())
    assert "不模拟登录" in sources["cnki"]["machine_access"]


def test_zotero_csl_json_export_preserves_chinese_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    items = [{"id": "ZH001", "type": "article-journal", "title": "中文期刊论文"}]
    monkeypatch.setattr("sciops.literature._fetch_zotero_csl_json", lambda collection=None: items)

    output, count = pull_zotero_csl_json(tmp_path / "references.json", collection="COLL")

    assert count == 1
    assert json.loads(output.read_text(encoding="utf-8")) == items


def test_candidate_preview_filters_concept_groups_and_ranks_preferences() -> None:
    records = [
        {
            "title": "基于机器学习的机械钻速预测",
            "publication_year": "2024",
            "source": "钻井期刊",
            "doi": "10.1/rop",
            "abstract": "使用钻压、转速和排量等钻井参数建立机械钻速预测模型。" * 5,
            "keywords": "机械钻速; 机器学习",
        },
        {
            "title": "机械钻速经验模型",
            "publication_year": "2025",
            "source": "钻井期刊",
            "abstract": "研究机械钻速。" * 10,
            "keywords": "机械钻速",
        },
        {
            "title": "城市交通速度预测",
            "publication_year": "2026",
            "source": "交通期刊",
            "abstract": "与钻井无关。" * 10,
            "keywords": "机器学习",
        },
    ]

    previews = prepare_candidate_previews(
        records,
        required_groups=["机械钻速,钻速", "钻井,钻井参数"],
        preferred_terms=["机器学习,因果推断"],
        limit=10,
        abstract_chars=80,
    )

    assert [record["candidate_id"] for record in previews] == ["CN-001", "CN-002"]
    assert previews[0]["title"] == "基于机器学习的机械钻速预测"
    assert previews[0]["abstract_truncated"] is True
    assert "机器学习" in str(previews[0]["matched_terms"])
    assert previews[0]["citation_url"] == "https://doi.org/10.1/rop"


def test_preview_csv_writes_markdown_and_download_decisions(tmp_path: Path) -> None:
    source = tmp_path / "records.csv"
    source.write_text(
        "title,publication_year,source,authors,landing_page,abstract,keywords\n"
        "双重机器学习方法,2025,方法期刊,张三,https://example.cn/dml,"
        "双重机器学习用于高维因果推断并控制大量混杂变量。双重机器学习用于高维因果推断。,"
        "双重机器学习;因果推断\n",
        encoding="utf-8",
    )

    preview, decisions, count = preview_csv(
        source,
        tmp_path / "preview.md",
        tmp_path / "decisions.csv",
        required_groups=["双重机器学习,DML"],
    )

    assert count == 1
    assert "CN-001" in preview.read_text(encoding="utf-8")
    assert "https://example.cn/dml" in preview.read_text(encoding="utf-8")
    with decisions.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["decision"] == "待定"
    assert rows[0]["full_text_status"] == "未获取"
