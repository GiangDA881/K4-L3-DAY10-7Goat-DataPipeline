from __future__ import annotations

from datetime import date
import random
from typing import Any

import pandas as pd

from core.utils import write_json

_SEED = 42
_DROP_RATIO = 0.2
_BLANK_RATIO = 0.15
_NOISE_RATIO = 0.15
_TRUNCATE_RATIO = 0.1
_STALE_RATIO = 0.15
_DUPLICATE_RATIO = 0.1
_NOISE_SUFFIX = " ##!!NOISE-INJECTED-RANDOM-TOKENS!!##"
_STALE_DATE = "2015-01-01"
_TRUNCATE_MAX_LEN = 7


def _rebuild_text_for_embedding(row: pd.Series) -> str:
    return (
        f"Title: {row['title']}\n"
        f"Authors: {row['authors_joined']}\n"
        f"Published: {row['published']}\n"
        f"Categories: {row['categories_joined']}\n"
        f"Summary: {row['summary']}"
    )


def _pick(pool: list[int], ratio: float) -> list[int]:
    if not pool:
        return []
    n = min(max(1, round(len(pool) * ratio)), len(pool))
    picked, remaining = pool[:n], pool[n:]
    pool[:] = remaining
    return picked


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate 6 realistic data-corruption scenarios on the cleaned dataframe.

    1. Drop the most recent 20% of records (silent data loss upstream).
    2. Blank the summary on a slice of rows.
    3. Inject noise tokens into the summary text on another slice.
    4. Truncate the title below 8 characters on another slice.
    5. Push the published date far into the past (stale data) on another slice.
    6. Duplicate a handful of untouched rows.
    Then rebuild `text_for_embedding` for every row and log what was done.
    """
    rng = random.Random(_SEED)
    working = df.reset_index(drop=True).copy()
    log: dict[str, Any] = {"seed": _SEED, "original_rows": int(len(working))}

    drop_count = min(max(1, round(len(working) * _DROP_RATIO)), len(working))
    dropped_ids = working.loc[: drop_count - 1, "paper_id"].tolist()
    working = working.iloc[drop_count:].reset_index(drop=True)
    log["dropped_latest_records"] = {"count": drop_count, "paper_ids": dropped_ids}

    pool = list(range(len(working)))
    rng.shuffle(pool)

    blanked = _pick(pool, _BLANK_RATIO)
    for pos in blanked:
        working.loc[pos, "summary"] = ""
        working.loc[pos, "summary_chars"] = 0
    log["blanked_summary"] = {
        "count": len(blanked),
        "paper_ids": working.loc[blanked, "paper_id"].tolist(),
    }

    noised = _pick(pool, _NOISE_RATIO)
    for pos in noised:
        noisy_summary = f"{working.loc[pos, 'summary']}{_NOISE_SUFFIX}".strip()
        working.loc[pos, "summary"] = noisy_summary
        working.loc[pos, "summary_chars"] = len(noisy_summary)
    log["injected_noise"] = {
        "count": len(noised),
        "paper_ids": working.loc[noised, "paper_id"].tolist(),
    }

    truncated = _pick(pool, _TRUNCATE_RATIO)
    for pos in truncated:
        working.loc[pos, "title"] = str(working.loc[pos, "title"])[:_TRUNCATE_MAX_LEN]
    log["truncated_title"] = {
        "count": len(truncated),
        "paper_ids": working.loc[truncated, "paper_id"].tolist(),
    }

    staled = _pick(pool, _STALE_RATIO)
    stale_age_days = (date.today() - date.fromisoformat(_STALE_DATE)).days
    for pos in staled:
        working.loc[pos, "published"] = _STALE_DATE
        working.loc[pos, "age_days"] = stale_age_days
    log["stale_date"] = {
        "count": len(staled),
        "paper_ids": working.loc[staled, "paper_id"].tolist(),
    }

    already_corrupted = set(blanked) | set(noised) | set(truncated) | set(staled)
    dup_candidates = [i for i in range(len(working)) if i not in already_corrupted]
    dup_count = min(max(1, round(len(working) * _DUPLICATE_RATIO)), len(dup_candidates))
    dup_positions = rng.sample(dup_candidates, k=dup_count) if dup_candidates else []
    duplicate_rows = working.loc[dup_positions]
    working = pd.concat([working, duplicate_rows], ignore_index=True)
    log["duplicated_rows"] = {
        "count": len(dup_positions),
        "paper_ids": duplicate_rows["paper_id"].tolist(),
    }

    working["text_for_embedding"] = working.apply(_rebuild_text_for_embedding, axis=1)

    log["final_rows"] = int(len(working))
    write_json(output_log_path, log)
    return working
