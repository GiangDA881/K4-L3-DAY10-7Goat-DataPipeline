from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.config import Settings, load_settings, normalized_provider, require_llm_credentials
from core.utils import ensure_parent, now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex


def save_dataframe(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    write_csv(df, csv_path)
    ensure_parent(json_path)
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)


def load_dataframe(json_path: Path) -> pd.DataFrame:
    return pd.read_json(json_path)


def _load_records(settings: Settings):
    raw_path = settings.paths.raw_records_json
    if settings.refresh_source or not raw_path.exists():
        return fetch_source_records(settings)
    return load_raw_records(raw_path)


def _ensure_test_set(settings: Settings, clean_df: pd.DataFrame) -> None:
    test_path = settings.paths.eval_testset
    if settings.refresh_test_set or not test_path.exists():
        build_test_set(clean_df, test_path)


def _run_agent_demo(settings: Settings, index: LocalEmbeddingIndex) -> None:
    try:
        require_llm_credentials(settings)
    except RuntimeError as exc:
        print(f"Bo qua agent demo: {exc}")
        return

    test_path = settings.paths.eval_testset
    if not test_path.exists():
        print("Bo qua agent demo: chua co test set.")
        return

    questions = [item["question"] for item in read_json(test_path)[:3]]
    if not questions:
        print("Bo qua agent demo: test set rong.")
        return

    try:
        agent = build_agent(settings, index)
        answers = [
            {"question": question, "answer": run_agent_question(agent, question)}
            for question in questions
        ]
    except Exception as exc:
        print(f"Bo qua agent demo: {exc}")
        write_json(settings.paths.demo_answers, {"skipped": str(exc), "provider": normalized_provider(settings)})
        return

    write_json(settings.paths.demo_answers, answers)
    print(f"Agent demo: {len(answers)} cau -> {settings.paths.demo_answers}")


def main() -> None:
    """Baseline pipeline: raw -> clean -> quality -> index -> evaluate -> report."""
    settings = load_settings()
    records = _load_records(settings)
    clean_df = build_clean_dataframe(records, now_utc())
    save_dataframe(clean_df, settings.paths.clean_csv, settings.paths.clean_json)
    print(f"Clean: {len(clean_df)} dong -> {settings.paths.clean_csv}")

    index = LocalEmbeddingIndex.build(
        clean_df,
        settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    print(f"Index: collection {index.collection_name} ({len(index.documents)} docs)")

    _ensure_test_set(settings, clean_df)
    evaluation = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    summary = evaluation.summary
    print(
        "Baseline metrics: "
        f"retrieval_hit_rate={summary.get('retrieval_hit_rate')} "
        f"mean_token_f1={summary.get('mean_token_f1')}"
    )

    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    print(f"Quality success={quality.get('success')} is_fresh={freshness.get('is_fresh')}")

    source_summary = {
        "source_api": settings.source_api,
        "query": settings.source_query,
        "source_filter": settings.source_filter,
        "raw_records": len(records),
        "clean_rows": int(len(clean_df)),
        "collection": index.collection_name,
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary,
        summary,
        quality,
        freshness,
    )
    print(f"Phase 1 report: {settings.paths.baseline_report}")

    _run_agent_demo(settings, index)
