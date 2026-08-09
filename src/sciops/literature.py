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
    "doi",
    "title",
    "publication_year",
    "work_type",
    "source",
    "authors",
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
        "doi": work.get("doi") or "",
        "title": work.get("title") or work.get("display_name") or "",
        "publication_year": work.get("publication_year") or "",
        "work_type": work.get("type") or "",
        "source": source,
        "authors": authors,
        "cited_by_count": work.get("cited_by_count") or 0,
        "is_oa": bool((work.get("open_access") or {}).get("is_oa")),
        "landing_page": landing_page,
        "abstract": _abstract_from_inverted_index(work.get("abstract_inverted_index")),
        "retrieved_at": datetime.now(UTC).isoformat(),
    }


def search_openalex(query: str, *, limit: int = 50) -> list[dict[str, str | int | bool]]:
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

    records: list[dict[str, str | int | bool]] = []
    pager = Works().search(query).paginate(per_page=min(limit, 200), n_max=limit)
    for page in pager:
        for work in page:
            records.append(_record_from_work(work))
            if len(records) >= limit:
                return records
    return records


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
                "doi": doi,
                "title": title,
                "publication_year": _crossref_year(item),
                "work_type": item.get("type") or "",
                "source": source,
                "authors": "; ".join(author_names),
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


def deduplicate_csv(source: Path, output: Path) -> tuple[Path, int, int]:
    source = source.expanduser().resolve()
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("输入 CSV 没有记录")

    unique: dict[str, dict[str, str]] = {}
    for index, row in enumerate(rows):
        doi = _normalize_doi(row.get("doi", ""))
        title = _normalize_title(row.get("title", ""))
        key = f"doi:{doi}" if doi else f"title:{title or index}"
        current = unique.get(key)
        current_score = sum(bool(value) for value in current.values()) if current else -1
        candidate_score = sum(bool(value) for value in row.values())
        if candidate_score > current_score:
            unique[key] = row

    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(unique.values())
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


def pull_zotero_json(output: Path, *, collection: str | None = None) -> tuple[Path, int]:
    library_id = os.getenv("ZOTERO_LIBRARY_ID", "").strip()
    library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user").strip() or "user"
    api_key = os.getenv("ZOTERO_API_KEY", "").strip() or None
    if not library_id:
        raise ValueError("缺少 ZOTERO_LIBRARY_ID")

    client = zotero.Zotero(library_id, library_type, api_key)
    first_page = client.collection_items(collection) if collection else client.items()
    items = client.everything(first_page)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return output, len(items)
