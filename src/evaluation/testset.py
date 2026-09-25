from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

MIN_DOCUMENTS = 5

_RANDOM_STATE = 42

# (question_type, question_template) - templates use keywords that
# retrieval.qa._extract_answer routes on, so the ground truth lines up
# with what the RAG agent will actually return on clean data.
_QUESTION_PLAN: tuple[tuple[str, str], ...] = (
    ("summary", "What is the paper '{title}' about?"),
    ("summary", "Can you summarize the paper '{title}'?"),
    ("summary", "Give a short summary of '{title}'."),
    ("authors", "Who authored the paper '{title}'?"),
    ("authors", "List the authors of '{title}'."),
    ("authors", "Who authored '{title}'?"),
    ("date", "When was '{title}' published?"),
    ("date", "What is the publication date of '{title}'?"),
    ("categories", "What categories does '{title}' belong to?"),
    ("categories", "What categories does the paper '{title}' fall under?"),
)


def _ground_truth(question_type: str, row: pd.Series) -> str:
    if question_type == "authors":
        return row["authors_joined"]
    if question_type == "date":
        return row["published"]
    if question_type == "categories":
        return row["categories_joined"]
    return first_sentence(row["summary"])


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build the evaluation test set from the cleaned dataframe.

    Picks a representative sample of papers and generates questions across
    the 4 business categories (summary, authors, date, categories), then
    writes the rows to `output_path` as JSON.
    """
    if len(df) < MIN_DOCUMENTS:
        raise ValueError(
            f"Can toi thieu {MIN_DOCUMENTS} document de sinh test set, hien co {len(df)}."
        )

    sample_size = min(len(_QUESTION_PLAN), len(df))
    sample = df.sample(n=sample_size, random_state=_RANDOM_STATE).reset_index(drop=True)

    rows: list[dict[str, Any]] = []
    for idx, (question_type, template) in enumerate(_QUESTION_PLAN):
        row = sample.iloc[idx % len(sample)]
        rows.append(
            {
                "id": f"q{idx + 1:02d}",
                "question_type": question_type,
                "question": template.format(title=row["title"]),
                "ground_truth": _ground_truth(question_type, row),
                "ground_truth_doc_ids": [row["paper_id"]],
            }
        )

    write_json(output_path, rows)
    return rows
