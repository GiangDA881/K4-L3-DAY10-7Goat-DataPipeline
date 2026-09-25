from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import requests

from core.config import load_settings
from core.utils import read_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records, parse_crossref_payload


ROOT = Path(__file__).resolve().parents[1]


class IngestionCleaningTests(unittest.TestCase):
    def test_offline_snapshot_and_clean_schema(self) -> None:
        settings = load_settings(ROOT)
        with TemporaryDirectory() as temp_dir:
            snapshot = Path(temp_dir) / "crossref_response.json"
            records_path = Path(temp_dir) / "crossref_records.json"
            original = settings.paths.raw_api_response.read_bytes()
            snapshot.write_bytes(original)
            paths = replace(settings.paths, raw_api_response=snapshot, raw_records_json=records_path)
            offline_settings = replace(settings, refresh_source=False, paths=paths)
            with patch("ingestion.crossref.requests.get", side_effect=AssertionError("network must not be used")):
                records = fetch_source_records(offline_settings)

            self.assertEqual(snapshot.read_bytes(), original)
            self.assertEqual(len(records), 24)
            self.assertEqual(records, load_raw_records(records_path))
            run_date = datetime(2026, 9, 25, tzinfo=timezone.utc)
            df = build_clean_dataframe(records, run_date)
            self.assertEqual(len(df), 24)
            self.assertTrue(df.paper_id.is_unique)
            self.assertEqual(df.age_days.tolist(), [
                (run_date.date() - datetime.fromisoformat(value).date()).days for value in df.published
            ])
            self.assertTrue((df.summary_chars == df.summary.str.len()).all())
            self.assertTrue(df.text_for_embedding.str.contains("Title: ", regex=False).all())
            self.assertTrue(df.text_for_embedding.str.contains("Summary: ", regex=False).all())
            self.assertFalse(df.summary.str.contains(r"<[^>]+>").any())

    def test_failing_refresh_uses_untouched_snapshot(self) -> None:
        settings = load_settings(ROOT)
        with TemporaryDirectory() as temp_dir:
            snapshot = Path(temp_dir) / "crossref_response.json"
            records_path = Path(temp_dir) / "crossref_records.json"
            original = settings.paths.raw_api_response.read_bytes()
            snapshot.write_bytes(original)
            paths = replace(settings.paths, raw_api_response=snapshot, raw_records_json=records_path)
            refresh_settings = replace(settings, refresh_source=True, paths=paths)
            with patch("ingestion.crossref._fetch_live_payload", side_effect=RuntimeError("API 429")):
                records = fetch_source_records(refresh_settings)
            self.assertEqual(len(records), 24)
            self.assertEqual(snapshot.read_bytes(), original)
            self.assertEqual(len(read_json(records_path)), 24)

    def test_live_refresh_retries_rate_limit_and_preserves_response_bytes(self) -> None:
        settings = load_settings(ROOT)
        with TemporaryDirectory() as temp_dir:
            snapshot = Path(temp_dir) / "crossref_response.json"
            records_path = Path(temp_dir) / "crossref_records.json"
            raw_bytes = settings.paths.raw_api_response.read_bytes()
            paths = replace(settings.paths, raw_api_response=snapshot, raw_records_json=records_path)
            refresh_settings = replace(settings, refresh_source=True, paths=paths)

            rate_limited = requests.Response()
            rate_limited.status_code = 429
            rate_limited._content = b"rate limited"
            success = requests.Response()
            success.status_code = 200
            success._content = raw_bytes
            with patch("ingestion.crossref.requests.get", side_effect=[rate_limited, success]) as get, patch(
                "ingestion.crossref.time.sleep"
            ):
                records = fetch_source_records(refresh_settings)
            self.assertEqual(get.call_count, 2)
            self.assertEqual(len(records), 24)
            self.assertEqual(snapshot.read_bytes(), raw_bytes)

    def test_cleaning_removes_duplicates_and_invalid_rows(self) -> None:
        payload = read_json(ROOT / "data" / "raw" / "crossref_response.json")
        first = parse_crossref_payload(payload)[0]
        noisy = replace(
            first,
            title="  <jats:p>Example &amp; Test</jats:p>  ",
            summary="<jats:p>Useful  abstract</jats:p>",
        )
        duplicate = replace(noisy, paper_id=noisy.paper_id.upper())
        invalid = replace(first, paper_id="another-doi", summary="")
        df = build_clean_dataframe([noisy, duplicate, invalid], datetime(2026, 9, 25, tzinfo=timezone.utc))
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0].title, "Example & Test")
        self.assertEqual(df.iloc[0].summary, "Useful abstract")


if __name__ == "__main__":
    unittest.main()
