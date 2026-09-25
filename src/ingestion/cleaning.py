from __future__ import annotations

from datetime import datetime
import html
import re

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


_COLUMNS = [
    "paper_id", "title", "summary", "authors", "categories", "primary_category",
    "published", "updated", "abs_url", "pdf_url", "comment", "age_days",
    "authors_joined", "categories_joined", "summary_chars", "text_for_embedding",
]


def _clean_text(value: str) -> str:
    return normalize_whitespace(html.unescape(re.sub(r"<[^>]*>", " ", value or "")))


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize Crossref records into the stable schema used by RAG and quality checks."""
    rows = []
    seen_ids: set[str] = set()
    for record in records:
        paper_id = normalize_whitespace(record.paper_id).lower()
        if not paper_id or paper_id in seen_ids:
            continue
        title = _clean_text(record.title)
        summary = _clean_text(record.summary)
        if not title or not summary:
            continue
        try:
            published = pd.Timestamp(record.published).date()
            updated = pd.Timestamp(record.updated or record.published).date()
        except (TypeError, ValueError):
            continue

        authors = [_clean_text(author) for author in (record.authors or [])]
        categories = [_clean_text(category) for category in (record.categories or [])]
        authors = [author for author in authors if author]
        categories = [category for category in categories if category]
        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        primary_category = _clean_text(record.primary_category) or (categories[0] if categories else "")
        published_iso = published.isoformat()
        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published_iso,
                "updated": updated.isoformat(),
                "abs_url": normalize_whitespace(record.abs_url),
                "pdf_url": normalize_whitespace(record.pdf_url),
                "comment": _clean_text(record.comment),
                "age_days": (run_date.date() - published).days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "text_for_embedding": (
                    f"Title: {title}\n"
                    f"Authors: {authors_joined}\n"
                    f"Published: {published_iso}\n"
                    f"Categories: {categories_joined}\n"
                    f"Summary: {summary}"
                ),
            }
        )
        seen_ids.add(paper_id)

    return pd.DataFrame(rows, columns=_COLUMNS).sort_values(
        ["published", "paper_id"], ascending=[False, True]
    ).reset_index(drop=True)
