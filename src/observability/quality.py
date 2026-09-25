from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import ensure_parent, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chốt kiểm soát chất lượng dữ liệu (Data Quality Gate) sử dụng chuẩn Great Expectations 1.x.

    Sử dụng ephemeral context để chạy hoàn toàn trên RAM và thiết lập 4 expectations cốt lõi:
    1. ExpectTableRowCountToBeBetween: Số lượng bài báo hợp lệ (5 đến 5000).
    2. ExpectColumnValuesToNotBeNull: paper_id, title, text_for_embedding không được null.
    3. ExpectColumnValuesToBeUnique: paper_id là khóa duy nhất, không trùng lặp.
    4. ExpectColumnValueLengthsToBeBetween: summary có độ dài tối thiểu 30 ký tự.
    """
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"papers_source_{report_name}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{report_name}")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{report_name}")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name=f"papers_{report_name}_suite")
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"))
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))

    context.suites.add(suite)
    validation_results = batch.validate(suite)
    results_dict = validation_results.to_json_dict()

    stats = results_dict.get("statistics", {})
    success = bool(validation_results.success)

    expectation_summaries = []
    for r in results_dict.get("results", []):
        exp_config = r.get("expectation_config", {})
        expectation_summaries.append({
            "expectation_type": exp_config.get("type", ""),
            "kwargs": exp_config.get("kwargs", {}),
            "success": bool(r.get("success")),
            "result": r.get("result", {}),
        })

    report_payload = {
        "report_name": report_name,
        "success": success,
        "suite_name": suite.name,
        "statistics": stats,
        "expectations": expectation_summaries,
        "full_results": results_dict,
    }

    if report_name == "baseline":
        output_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        output_path = settings.paths.corrupted_quality_report
    elif report_name == "repaired":
        output_path = settings.paths.quality_dir / "repaired_quality_report.json"
    else:
        output_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"

    write_json(output_path, report_payload)
    return report_payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Kiểm tra Freshness SLA:

    Đo lường độ tươi mới của dữ liệu. Cảnh báo is_fresh = False nếu tỷ lệ bài báo cũ
    (age_days > 180 ngày) vượt quá 25%.
    """
    total_rows = int(len(df))
    threshold_days = settings.freshness_threshold_days
    max_stale_ratio = 0.25

    if total_rows == 0:
        payload = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "is_fresh": True,
            "threshold_days": threshold_days,
            "max_stale_ratio": max_stale_ratio,
        }
    else:
        latest_published = str(df["published"].max()) if "published" in df else None
        oldest_published = str(df["published"].min()) if "published" in df else None
        stale_rows = int((df["age_days"] > threshold_days).sum()) if "age_days" in df else 0
        stale_ratio = round(float(stale_rows / total_rows), 4)
        is_fresh = bool(stale_ratio <= max_stale_ratio)

        payload = {
            "latest_published": latest_published,
            "oldest_published": oldest_published,
            "stale_rows": stale_rows,
            "total_rows": total_rows,
            "stale_ratio": stale_ratio,
            "is_fresh": is_fresh,
            "threshold_days": threshold_days,
            "max_stale_ratio": max_stale_ratio,
        }

    target_path = Path(report_path)
    write_json(target_path, payload)
    return payload
