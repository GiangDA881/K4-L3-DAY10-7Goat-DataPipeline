from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


from core.utils import first_sentence, read_json, write_json


class TestSet(list):
    """Wrapper danh sách câu hỏi test set hỗ trợ cả len(ts) lẫn len(ts.samples)."""

    def __init__(self, samples: list[dict[str, Any]]):
        super().__init__(samples)
        self.samples = samples


def _format_authors(row: dict[str, Any]) -> str:
    val = row.get("authors_joined") or row.get("authors")
    if isinstance(val, list):
        return ", ".join(str(a) for a in val if a)
    if val and not pd.isna(val):
        return str(val)
    return "Unknown"


def _format_categories(row: dict[str, Any]) -> str:
    val = row.get("categories_joined") or row.get("categories") or row.get("primary_category")
    if isinstance(val, list):
        return ", ".join(str(c) for c in val if c)
    if val and not pd.isna(val):
        return str(val)
    return "General"


def build_test_set(
    df: pd.DataFrame,
    output_path: Path | str | None = None,
    target_count: int = 5,
) -> TestSet:
    """Xây dựng bộ câu hỏi Benchmark Test Set từ DataFrame bài báo khoa học.

    Tạo 5 dạng câu hỏi theo nội dung thực tế:
    1. summary: Tóm tắt nội dung nghiên cứu chính.
    2. authors: Ai là tác giả của nghiên cứu về chủ đề X?
    3. date: Nghiên cứu Y được công bố vào năm/tháng nào?
    4. category: Công trình này thuộc lĩnh vực chuyên môn nào?
    5. multi_hop: Câu hỏi kết hợp liên ngành giữa hai chủ đề.
    """
    if df.empty:
        raise ValueError("DataFrame is empty, cannot generate test set.")

    records = df.to_dict(orient="records")
    n_records = len(records)
    samples: list[dict[str, Any]] = []

    # 1. Dạng summary
    r0 = records[0 % n_records]
    samples.append({
        "id": "eval_001",
        "type": "summary",
        "question_type": "summary",
        "question": f"What is the summary of the paper '{r0['title']}'?",
        "ground_truth": first_sentence(str(r0.get("summary", ""))) or str(r0.get("summary", "")),
        "ground_truth_doc_ids": [str(r0["paper_id"])],
    })

    # 2. Dạng authors
    r1 = records[1 % n_records]
    samples.append({
        "id": "eval_002",
        "type": "authors",
        "question_type": "authors",
        "question": f"Who are the authors of the paper titled '{r1['title']}'?",
        "ground_truth": _format_authors(r1),
        "ground_truth_doc_ids": [str(r1["paper_id"])],
    })

    # 3. Dạng date
    r2 = records[2 % n_records]
    samples.append({
        "id": "eval_003",
        "type": "date",
        "question_type": "date",
        "question": f"When was the research paper '{r2['title']}' published?",
        "ground_truth": str(r2.get("published", "")),
        "ground_truth_doc_ids": [str(r2["paper_id"])],
    })

    # 4. Dạng category
    r3 = records[3 % n_records]
    samples.append({
        "id": "eval_004",
        "type": "category",
        "question_type": "category",
        "question": f"What category does the paper '{r3['title']}' belong to?",
        "ground_truth": _format_categories(r3),
        "ground_truth_doc_ids": [str(r3["paper_id"])],
    })

    # 5. Dạng multi_hop
    p1 = records[0 % n_records]
    p2 = records[min(4, n_records - 1)]
    samples.append({
        "id": "eval_005",
        "type": "multi_hop",
        "question_type": "multi_hop",
        "question": (
            f"Between '{p1['title']}' and '{p2['title']}', what are their"
            " respective publication dates and research domains?"
        ),
        "ground_truth": (
            f"The paper '{p1['title']}' was published on {p1.get('published', '')}"
            f" in {_format_categories(p1)}, while '{p2['title']}' was published on"
            f" {p2.get('published', '')} in {_format_categories(p2)}."
        ),
        "ground_truth_doc_ids": [str(p1["paper_id"]), str(p2["paper_id"])],
    })

    # Nếu target_count > 5 (ví dụ 10 câu), bổ sung tiếp các câu hỏi
    if target_count > 5 and n_records >= 5:
        types_cycle = ["summary", "authors", "date", "category", "multi_hop"]
        for i in range(5, target_count):
            q_type = types_cycle[i % len(types_cycle)]
            rec = records[i % n_records]
            eval_id = f"eval_{i + 1:03d}"
            if q_type == "summary":
                samples.append({
                    "id": eval_id,
                    "type": q_type,
                    "question_type": q_type,
                    "question": f"What is the main summary of the research titled '{rec['title']}'?",
                    "ground_truth": first_sentence(str(rec.get("summary", ""))) or str(rec.get("summary", "")),
                    "ground_truth_doc_ids": [str(rec["paper_id"])],
                })
            elif q_type == "authors":
                samples.append({
                    "id": eval_id,
                    "type": q_type,
                    "question_type": q_type,
                    "question": f"Who wrote the paper with title '{rec['title']}'?",
                    "ground_truth": _format_authors(rec),
                    "ground_truth_doc_ids": [str(rec["paper_id"])],
                })
            elif q_type == "date":
                samples.append({
                    "id": eval_id,
                    "type": q_type,
                    "question_type": q_type,
                    "question": f"In what year or month was '{rec['title']}' published?",
                    "ground_truth": str(rec.get("published", "")),
                    "ground_truth_doc_ids": [str(rec["paper_id"])],
                })
            elif q_type == "category":
                samples.append({
                    "id": eval_id,
                    "type": q_type,
                    "question_type": q_type,
                    "question": f"Which academic discipline or field is '{rec['title']}' classified under?",
                    "ground_truth": _format_categories(rec),
                    "ground_truth_doc_ids": [str(rec["paper_id"])],
                })
            elif q_type == "multi_hop":
                other_rec = records[(i + 1) % n_records]
                samples.append({
                    "id": eval_id,
                    "type": q_type,
                    "question_type": q_type,
                    "question": f"Compare the publication dates and primary fields between the papers '{rec['title']}' and '{other_rec['title']}'.",
                    "ground_truth": (
                        f"'{rec['title']}' was published on {rec.get('published', '')}"
                        f" in {_format_categories(rec)}, whereas '{other_rec['title']}'"
                        f" was published on {other_rec.get('published', '')} in"
                        f" {_format_categories(other_rec)}."
                    ),
                    "ground_truth_doc_ids": [str(rec["paper_id"]), str(other_rec["paper_id"])],
                })

    if output_path is not None:
        write_json(Path(output_path), [dict(s) for s in samples])

    return TestSet(samples)


def load_or_create_test_set(
    df: pd.DataFrame,
    output_path: Path | str | None = None,
    target_count: int = 5,
) -> TestSet:
    """Nạp bộ test set có sẵn nếu đã tồn tại file, ngược lại tự động tạo mới."""
    if output_path is not None:
        p = Path(output_path)
        if p.exists():
            items = read_json(p)
            if isinstance(items, list) and len(items) > 0:
                return TestSet(items)
    return build_test_set(df, output_path, target_count=target_count)
