from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from .phase1 import load_dataframe, main as run_phase1, save_dataframe
from retrieval.index import LocalEmbeddingIndex

METRIC_KEYS = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")


def _ensure_baseline(settings: Settings) -> tuple[dict, pd.DataFrame]:
    metrics_path = settings.paths.baseline_metrics
    clean_path = settings.paths.clean_json
    if not metrics_path.exists() or not clean_path.exists():
        print("Chua co baseline. Chay phase 1 truoc.")
        run_phase1()
    return read_json(metrics_path), load_dataframe(clean_path)


def _print_comparison(baseline: dict, corrupted: dict, repaired: dict) -> None:
    print(f"{'metric':<24} {'baseline':>12} {'corrupted':>12} {'repaired':>12}")
    for key in METRIC_KEYS:
        print(
            f"{key:<24} "
            f"{_format_metric(baseline.get(key)):>12} "
            f"{_format_metric(corrupted.get(key)):>12} "
            f"{_format_metric(repaired.get(key)):>12}"
        )


def _format_metric(value) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.4f}"
    return "-"


def _freshness_path(settings: Settings, name: str) -> Path:
    if name == "baseline":
        return settings.paths.freshness_report
    return settings.paths.quality_dir / f"{name}_freshness_report.json"


def main() -> None:
    """Corruption -> evaluate -> repair from raw -> compare three states."""
    settings = load_settings()
    baseline_metrics, clean_df = _ensure_baseline(settings)

    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    save_dataframe(
        corrupted_df,
        settings.paths.corrupted_clean_csv,
        settings.paths.corrupted_clean_json,
    )
    print(f"Corrupted: {len(corrupted_df)} dong -> {settings.paths.corrupted_clean_json}")

    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    corrupted_eval = evaluate_pipeline(
        settings,
        corrupted_index,
        settings.paths.eval_testset,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        _freshness_path(settings, "corrupted"),
    )
    print(
        "Corrupted quality: "
        f"success={corrupted_quality.get('success')} "
        f"is_fresh={corrupted_freshness.get('is_fresh')}"
    )

    repaired_df = build_clean_dataframe(
        load_raw_records(settings.paths.raw_records_json),
        now_utc(),
    )
    save_dataframe(
        repaired_df,
        settings.paths.repaired_clean_csv,
        settings.paths.repaired_clean_json,
    )
    print(f"Repaired from raw: {len(repaired_df)} dong -> {settings.paths.repaired_clean_json}")

    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    repaired_eval = evaluate_pipeline(
        settings,
        repaired_index,
        settings.paths.eval_testset,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        _freshness_path(settings, "repaired"),
    )

    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_eval.summary,
        repaired_eval.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    print(f"Comparison report: {settings.paths.comparison_report}")
    _print_comparison(baseline_metrics, corrupted_eval.summary, repaired_eval.summary)
