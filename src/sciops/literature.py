from __future__ import annotations

import csv
import json
import os
import re
import unicodedata
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pyalex
from pyalex import Works
from pyzotero import zotero

LITERATURE_FIELDS = (
    "openalex_id",
    "zotero_key",
    "doi",
    "title",
    "publication_year",
    "work_type",
    "source",
    "database",
    "language",
    "authors",
    "keywords",
    "cited_by_count",
    "is_oa",
    "landing_page",
    "abstract",
    "retrieved_at",
)


def _abstract_from_inverted_index(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positioned = ((position, word) for word, positions in index.items() for position in positions)
    return " ".join(word for _, word in sorted(positioned))


def _record_from_work(work: dict) -> dict[str, str | int | bool]:
    source = (((work.get("primary_location") or {}).get("source") or {}).get("display_name")) or ""
    authors = "; ".join(
        ((entry.get("author") or {}).get("display_name") or "")
        for entry in work.get("authorships", [])
        if (entry.get("author") or {}).get("display_name")
    )
    landing_page = (work.get("primary_location") or {}).get("landing_page_url") or ""
    return {
        "openalex_id": work.get("id") or "",
        "zotero_key": "",
        "doi": work.get("doi") or "",
        "title": work.get("title") or work.get("display_name") or "",
        "publication_year": work.get("publication_year") or "",
        "work_type": work.get("type") or "",
        "source": source,
        "database": "OpenAlex",
        "language": work.get("language") or "",
        "authors": authors,
        "keywords": "; ".join(
            keyword.get("display_name", "")
            for keyword in work.get("keywords", [])
            if keyword.get("display_name")
        ),
        "cited_by_count": work.get("cited_by_count") or 0,
        "is_oa": bool((work.get("open_access") or {}).get("is_oa")),
        "landing_page": landing_page,
        "abstract": _abstract_from_inverted_index(work.get("abstract_inverted_index")),
        "retrieved_at": datetime.now(UTC).isoformat(),
    }


def _build_openalex_filters(
    *,
    language: str | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
) -> dict[str, str]:
    if from_year is not None and not 1000 <= from_year <= 2100:
        raise ValueError("from_year 必须在 1000 到 2100 之间")
    if to_year is not None and not 1000 <= to_year <= 2100:
        raise ValueError("to_year 必须在 1000 到 2100 之间")
    if from_year is not None and to_year is not None and from_year > to_year:
        raise ValueError("from_year 不能晚于 to_year")

    filters: dict[str, str] = {}
    if language and language.strip():
        filters["language"] = language.strip().lower()
    if from_year is not None:
        filters["from_publication_date"] = f"{from_year:04d}-01-01"
    if to_year is not None:
        filters["to_publication_date"] = f"{to_year:04d}-12-31"
    return filters


def search_openalex(
    query: str,
    *,
    limit: int = 50,
    language: str | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
) -> list[dict[str, str | int | bool]]:
    if not query.strip():
        raise ValueError("检索式不能为空")
    if limit < 1 or limit > 10_000:
        raise ValueError("limit 必须在 1 到 10000 之间")

    api_key = os.getenv("OPENALEX_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "缺少 OPENALEX_API_KEY；请在 OpenAlex 账户中申请免费 key 并设置本地环境变量"
        )
    pyalex.config.api_key = api_key

    filters = _build_openalex_filters(
        language=language,
        from_year=from_year,
        to_year=to_year,
    )
    works = Works().search(query)
    if filters:
        works = works.filter(**filters)

    records: list[dict[str, str | int | bool]] = []
    pager = works.paginate(per_page=min(limit, 200), n_max=limit)
    for page in pager:
        for work in page:
            records.append(_record_from_work(work))
            if len(records) >= limit:
                return records
    return records


def search_chinese_openalex(
    query: str,
    *,
    limit: int = 50,
    from_year: int | None = None,
    to_year: int | None = None,
) -> list[dict[str, str | int | bool]]:
    """Search works OpenAlex classifies as Chinese-language records."""
    return search_openalex(
        query,
        limit=limit,
        language="zh",
        from_year=from_year,
        to_year=to_year,
    )


def _crossref_year(item: dict) -> int | str:
    for field in ("published-print", "published-online", "published", "issued"):
        date_parts = ((item.get(field) or {}).get("date-parts") or [[]])[0]
        if date_parts:
            return date_parts[0]
    return ""


def search_crossref(query: str, *, limit: int = 50) -> list[dict[str, str | int | bool]]:
    if not query.strip():
        raise ValueError("检索式不能为空")
    if limit < 1 or limit > 1_000:
        raise ValueError("Crossref limit 必须在 1 到 1000 之间")

    email = os.getenv("OPENALEX_EMAIL", "").strip()
    user_agent = "SCI-Workflow-OS/0.1"
    if email:
        user_agent += f" (mailto:{email})"
    params = {
        "query": query,
        "rows": limit,
        "select": (
            "DOI,title,author,published-print,published-online,published,issued,"
            "container-title,URL,type,is-referenced-by-count,abstract"
        ),
    }
    with httpx.Client(
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": user_agent},
    ) as client:
        response = client.get("https://api.crossref.org/works", params=params)
        response.raise_for_status()
        items = response.json()["message"]["items"]

    retrieved_at = datetime.now(UTC).isoformat()
    records: list[dict[str, str | int | bool]] = []
    for item in items:
        author_names = []
        for author in item.get("author", []):
            name = " ".join(part for part in (author.get("given"), author.get("family")) if part)
            if name:
                author_names.append(name)
        abstract = re.sub(r"<[^>]+>", " ", item.get("abstract", ""))
        title = (item.get("title") or [""])[0]
        source = (item.get("container-title") or [""])[0]
        doi = item.get("DOI") or ""
        records.append(
            {
                "openalex_id": "",
                "zotero_key": "",
                "doi": doi,
                "title": title,
                "publication_year": _crossref_year(item),
                "work_type": item.get("type") or "",
                "source": source,
                "database": "Crossref",
                "language": item.get("language") or "",
                "authors": "; ".join(author_names),
                "keywords": "; ".join(item.get("subject") or []),
                "cited_by_count": item.get("is-referenced-by-count") or 0,
                "is_oa": "",
                "landing_page": item.get("URL") or (f"https://doi.org/{doi}" if doi else ""),
                "abstract": re.sub(r"\s+", " ", abstract).strip(),
                "retrieved_at": retrieved_at,
            }
        )
    return records


def write_records(records: Iterable[dict], output: Path) -> Path:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LITERATURE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    return output


def _normalize_doi(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    return value


def _normalize_title(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return "".join(char for char in value if char.isalnum())


def _deduplicate_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    unique: dict[str, dict[str, str]] = {}
    for index, row in enumerate(rows):
        doi = _normalize_doi(row.get("doi", ""))
        title = _normalize_title(row.get("title", ""))
        key = f"doi:{doi}" if doi else f"title:{title or index}"
        current = unique.get(key)
        current_score = sum(bool(value) for value in current.values()) if current else -1
        candidate_score = sum(bool(value) for value in row.values())
        if current is None:
            unique[key] = row
            continue
        primary, secondary = (row.copy(), current) if candidate_score > current_score else (
            current.copy(),
            row,
        )
        for field, value in secondary.items():
            if value and not primary.get(field):
                primary[field] = value
        databases = []
        for value in (current.get("database", ""), row.get("database", "")):
            for database in value.split(";"):
                database = database.strip()
                if database and database not in databases:
                    databases.append(database)
        if databases:
            primary["database"] = "; ".join(databases)
        unique[key] = primary
    return list(unique.values())


def deduplicate_csv(source: Path, output: Path) -> tuple[Path, int, int]:
    source = source.expanduser().resolve()
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("输入 CSV 没有记录")

    unique = _deduplicate_rows(rows)

    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(unique)
    return output, len(rows), len(unique)


def merge_csv(sources: list[Path], output: Path) -> tuple[Path, int, int]:
    if len(sources) < 2:
        raise ValueError("至少需要两个输入 CSV")

    rows: list[dict[str, str]] = []
    fieldnames: list[str] = []
    for source in sources:
        source = source.expanduser().resolve()
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError(f"输入 CSV 缺少表头: {source}")
            for field in reader.fieldnames:
                if field not in fieldnames:
                    fieldnames.append(field)
            rows.extend(reader)
    if not rows:
        raise ValueError("输入 CSV 没有记录")

    unique = _deduplicate_rows(rows)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(unique)
    return output, len(rows), len(unique)


def fetch_bibtex(doi: str) -> str:
    normalized = _normalize_doi(doi)
    if not normalized.startswith("10.") or "/" not in normalized:
        raise ValueError(f"DOI 格式无效: {doi}")
    email = os.getenv("OPENALEX_EMAIL", "").strip()
    headers = {"Accept": "application/x-bibtex", "User-Agent": "SCI-Workflow-OS/0.1"}
    if email:
        headers["User-Agent"] += f" (mailto:{email})"
    url = f"https://api.crossref.org/works/{normalized}/transform/application/x-bibtex"
    with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text.strip() + "\n"


def append_bibtex(doi: str, output: Path) -> Path:
    entry = fetch_bibtex(doi)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    existing = output.read_text(encoding="utf-8") if output.exists() else ""
    normalized = _normalize_doi(doi)
    if normalized in existing.casefold():
        return output
    with output.open("a", encoding="utf-8") as handle:
        if existing and not existing.endswith("\n\n"):
            handle.write("\n")
        handle.write(entry)
    return output


def _zotero_client() -> zotero.Zotero:
    library_id = os.getenv("ZOTERO_LIBRARY_ID", "").strip()
    library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user").strip() or "user"
    api_key = os.getenv("ZOTERO_API_KEY", "").strip() or None
    if not library_id:
        raise ValueError("缺少 ZOTERO_LIBRARY_ID")
    return zotero.Zotero(library_id, library_type, api_key)


def _fetch_zotero_items(*, collection: str | None = None) -> list[dict]:
    client = _zotero_client()
    first_page = client.collection_items_top(collection) if collection else client.top()
    return client.everything(first_page)


def _fetch_zotero_csl_json(*, collection: str | None = None) -> list[dict]:
    client = _zotero_client()
    if collection:
        first_page = client.collection_items_top(collection, content="csljson")
    else:
        first_page = client.top(content="csljson")
    return client.everything(first_page)


def list_zotero_collections() -> list[dict[str, str | int]]:
    client = _zotero_client()
    collections = client.everything(client.collections())
    return [
        {
            "key": entry.get("key") or (entry.get("data") or {}).get("key") or "",
            "name": (entry.get("data") or {}).get("name") or "",
            "parent": (entry.get("data") or {}).get("parentCollection") or "",
            "version": entry.get("version") or (entry.get("data") or {}).get("version") or 0,
        }
        for entry in collections
    ]


def _zotero_year(value: str) -> int | str:
    match = re.search(r"(?:19|20)\d{2}", value)
    return int(match.group()) if match else ""


def _record_from_zotero_item(item: dict) -> dict[str, str | int | bool]:
    data = item.get("data") or {}
    language = data.get("language") or ""
    creators = []
    for creator in data.get("creators", []):
        if creator.get("name"):
            name = creator["name"]
        elif language.lower().startswith("zh"):
            name = "".join(
                part for part in (creator.get("lastName"), creator.get("firstName")) if part
            )
        else:
            name = " ".join(
                part for part in (creator.get("firstName"), creator.get("lastName")) if part
            )
        if name:
            creators.append(name)

    tags = []
    for entry in data.get("tags", []):
        tag = entry.get("tag") if isinstance(entry, dict) else str(entry)
        if tag:
            tags.append(tag)

    doi = data.get("DOI") or ""
    url = data.get("url") or (f"https://doi.org/{_normalize_doi(doi)}" if doi else "")
    source = (
        data.get("publicationTitle")
        or data.get("proceedingsTitle")
        or data.get("university")
        or data.get("publisher")
        or ""
    )
    return {
        "openalex_id": "",
        "zotero_key": item.get("key") or data.get("key") or "",
        "doi": doi,
        "title": data.get("title") or "",
        "publication_year": _zotero_year(data.get("date") or ""),
        "work_type": data.get("itemType") or "",
        "source": source,
        "database": "Zotero",
        "language": language,
        "authors": "; ".join(creators),
        "keywords": "; ".join(tags),
        "cited_by_count": 0,
        "is_oa": "",
        "landing_page": url,
        "abstract": data.get("abstractNote") or "",
        "retrieved_at": datetime.now(UTC).isoformat(),
    }


def pull_zotero_csv(output: Path, *, collection: str | None = None) -> tuple[Path, int]:
    items = _fetch_zotero_items(collection=collection)
    records = [_record_from_zotero_item(item) for item in items]
    return write_records(records, output), len(records)


def get_zotero_records(
    *,
    collection: str | None = None,
    limit: int = 100,
) -> list[dict[str, str | int | bool]]:
    """Return normalized top-level Zotero records without writing a file."""
    if limit < 1 or limit > 1_000:
        raise ValueError("Zotero limit 必须在 1 到 1000 之间")
    items = _fetch_zotero_items(collection=collection)
    return [_record_from_zotero_item(item) for item in items[:limit]]


def pull_zotero_json(output: Path, *, collection: str | None = None) -> tuple[Path, int]:
    items = _fetch_zotero_items(collection=collection)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return output, len(items)


def pull_zotero_csl_json(output: Path, *, collection: str | None = None) -> tuple[Path, int]:
    """Export top-level Zotero items as CSL JSON for Quarto/Pandoc citations."""
    items = _fetch_zotero_csl_json(collection=collection)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return output, len(items)
