from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
import html
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _plain_text(value: object) -> str:
    """Convert Crossref JATS/HTML fragments to searchable plain text."""
    if not isinstance(value, str):
        return ""
    without_tags = re.sub(r"<[^>]*>", " ", value)
    return normalize_whitespace(html.unescape(without_tags))


def _date_string(item: dict, *fields: str) -> str:
    for field in fields:
        value = item.get(field)
        if not isinstance(value, dict):
            continue
        parts = value.get("date-parts")
        if isinstance(parts, list) and parts and isinstance(parts[0], list):
            try:
                year = int(parts[0][0])
                month = int(parts[0][1]) if len(parts[0]) > 1 else 1
                day = int(parts[0][2]) if len(parts[0]) > 2 else 1
                return date(year, month, day).isoformat()
            except (IndexError, TypeError, ValueError):
                pass
        timestamp = value.get("date-time")
        if isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date().isoformat()
            except ValueError:
                pass
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref works response without changing the original payload."""
    message = payload.get("message") if isinstance(payload, dict) else None
    items = message.get("items") if isinstance(message, dict) else None
    if not isinstance(items, list):
        raise ValueError("Crossref response must contain message.items as a list.")

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        paper_id = normalize_whitespace(str(item.get("DOI") or ""))
        titles = item.get("title") or []
        title = _plain_text(titles[0] if isinstance(titles, list) and titles else titles)
        published = _date_string(item, "published", "published-online", "published-print", "created")
        if not paper_id or not title or not published:
            continue

        authors = []
        raw_authors = item.get("author")
        for author in raw_authors if isinstance(raw_authors, list) else []:
            if isinstance(author, dict):
                name = _plain_text(" ".join(str(author.get(part) or "") for part in ("given", "family")))
                if not name:
                    name = _plain_text(author.get("name"))
                if name:
                    authors.append(name)
        raw_categories = item.get("subject")
        categories = [_plain_text(subject) for subject in raw_categories if isinstance(subject, str)] if isinstance(raw_categories, list) else []
        categories = [category for category in categories if category]
        abs_url = str(item.get("URL") or f"https://doi.org/{paper_id}")
        pdf_url = next(
            (
                str(link.get("URL"))
                for link in (item.get("link") if isinstance(item.get("link"), list) else [])
                if isinstance(link, dict) and link.get("URL") and link.get("content-type") == "application/pdf"
            ),
            abs_url,
        )
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=_plain_text(item.get("abstract")),
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=_date_string(item, "deposited", "updated", "published", "created") or published,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=f"Crossref record {paper_id}",
            )
        )
    return records


def _fetch_live_payload(settings: Settings) -> tuple[dict, bytes]:
    params = {"query": settings.source_query, "filter": settings.source_filter, "rows": settings.max_results}
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(
                "https://api.crossref.org/works",
                params=params,
                headers={"User-Agent": "Day10DataPipelineLab/0.1 (Crossref academic metadata exercise)"},
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Crossref returned a non-object JSON payload.")
            return payload, response.content
        except requests.HTTPError as exc:
            last_error = exc
            if response.status_code not in {429, 500, 502, 503, 504}:
                break
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
        if attempt < 2:
            time.sleep(1 << attempt)
    raise RuntimeError("Crossref API could not be fetched after retries.") from last_error


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Use the local snapshot by default; refresh from Crossref when requested.

    A successful live response replaces the raw snapshot byte for byte. Failed
    refreshes leave it intact so the same records remain available for repair.
    """
    raw_path = settings.paths.raw_api_response
    if settings.refresh_source or not raw_path.exists():
        try:
            payload, raw_bytes = _fetch_live_payload(settings)
            records = parse_crossref_payload(payload)
            if not records:
                raise ValueError("Crossref response contained no usable records.")
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(raw_bytes)
        except (RuntimeError, ValueError) as exc:
            if not raw_path.exists():
                raise RuntimeError("Crossref fetch failed and no offline snapshot is available.") from exc
            records = parse_crossref_payload(read_json(raw_path))
    else:
        records = parse_crossref_payload(read_json(raw_path))
    if not records:
        raise ValueError("Raw Crossref snapshot contains no usable records.")
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load preserved parsed records for a repeatable clean or repair run."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError("Raw records snapshot must contain a list.")
    return [PaperRecord(**record) for record in payload]
