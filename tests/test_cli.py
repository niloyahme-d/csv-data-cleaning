from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import patch

import requests

from directory_scraper.cli import main

SAMPLE_HTML = """
<div class="directory-listings">
  <div class="listing-card">
    <h2 class="company-name">Acme Corp</h2>
    <p class="category">Retail</p>
    <p class="address">123 Main St</p>
    <span class="phone">+8801711223344</span>
    <span class="email">contact@acme.com</span>
  </div>
  <div class="listing-card">
    <h2 class="company-name">Beta Ltd</h2>
    <p class="address">456 Side St</p>
    <span class="phone">+8801999999999</span>
    <span class="email">info@beta.com</span>
  </div>
</div>
"""


class TestCliMain:
    def test_successful_run_local_file(self, tmp_path: Path):
        source = tmp_path / "page.html"
        source.write_text(SAMPLE_HTML, encoding="utf-8")
        output_dir = tmp_path / "out"

        exit_code = main(["--source", str(source), "--output-dir", str(output_dir), "--quiet"])

        assert exit_code == 0
        clean_csv = output_dir / "scraped_companies.csv"
        issues_csv = output_dir / "issues_report.csv"
        assert clean_csv.exists()
        assert issues_csv.exists()

        with open(clean_csv, encoding="utf-8") as f:
            assert len(list(csv.DictReader(f))) == 1  # Acme only; Beta missing category

        with open(issues_csv, encoding="utf-8") as f:
            assert len(list(csv.DictReader(f))) == 1  # Beta flagged

    def test_missing_local_source_returns_error_code(self, tmp_path: Path):
        missing = tmp_path / "does_not_exist.html"
        output_dir = tmp_path / "out"

        exit_code = main(["--source", str(missing), "--output-dir", str(output_dir)])

        assert exit_code == 1

    @patch("directory_scraper.cli.fetch_html")
    def test_fetch_failure_returns_error_code(self, mock_fetch, tmp_path: Path):
        mock_fetch.side_effect = requests.HTTPError("503 Service Unavailable")
        output_dir = tmp_path / "out"

        exit_code = main(["--source", "https://example.com/page", "--output-dir", str(output_dir)])

        assert exit_code == 1

    def test_no_listing_cards_still_writes_empty_outputs(self, tmp_path: Path):
        source = tmp_path / "empty.html"
        source.write_text("<div class='directory-listings'></div>", encoding="utf-8")
        output_dir = tmp_path / "out"

        exit_code = main(["--source", str(source), "--output-dir", str(output_dir), "--quiet"])

        assert exit_code == 0
        assert (output_dir / "scraped_companies.csv").exists()
