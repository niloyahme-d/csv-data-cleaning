from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import requests

from directory_scraper.core import (
    ListingRecord,
    clean_text,
    fetch_html,
    is_url,
    parse_listings,
    write_clean_csv,
    write_issues_csv,
)

VALID_HTML = """
<div class="directory-listings">
  <div class="listing-card">
    <h2 class="company-name">Acme Corp</h2>
    <p class="category">Retail</p>
    <p class="address">123 Main St, Dhaka</p>
    <span class="phone">+8801711223344</span>
    <span class="email">contact@acme.com</span>
  </div>
</div>
"""

MISSING_FIELD_HTML = """
<div class="directory-listings">
  <div class="listing-card">
    <h2 class="company-name">Beta Ltd</h2>
    <p class="address">456 Side St, Chittagong</p>
    <span class="phone">+8801999999999</span>
    <span class="email">info@beta.com</span>
  </div>
</div>
"""

EMPTY_FIELD_HTML = """
<div class="directory-listings">
  <div class="listing-card">
    <h2 class="company-name">Gamma Inc</h2>
    <p class="category"></p>
    <p class="address">789 Third St, Sylhet</p>
    <span class="phone">+8801888888888</span>
    <span class="email">hi@gamma.com</span>
  </div>
</div>
"""

NO_CARDS_HTML = "<div class='directory-listings'></div>"


# ---------------------------------------------------------------------------
# clean_text
# ---------------------------------------------------------------------------


class TestCleanText:
    def test_collapses_whitespace(self):
        assert clean_text("  hello   world  \n") == "hello world"

    def test_none_input(self):
        assert clean_text(None) == ""

    def test_empty_string(self):
        assert clean_text("") == ""


# ---------------------------------------------------------------------------
# is_url
# ---------------------------------------------------------------------------


class TestIsUrl:
    @pytest.mark.parametrize("value", ["http://example.com", "https://example.com/page"])
    def test_recognizes_urls(self, value):
        assert is_url(value) is True

    @pytest.mark.parametrize(
        "value", ["sample.html", "/home/user/page.html", "C:\\data\\page.html"]
    )
    def test_recognizes_local_paths(self, value):
        assert is_url(value) is False


# ---------------------------------------------------------------------------
# parse_listings — the critical fault-tolerance behavior
# ---------------------------------------------------------------------------


class TestParseListings:
    def test_valid_card_parses_cleanly(self):
        result = parse_listings(VALID_HTML)
        assert result.total_cards_found == 1
        assert len(result.valid_records) == 1
        assert len(result.flagged_records) == 0
        record = result.valid_records[0]
        assert record.company_name == "Acme Corp"
        assert record.email == "contact@acme.com"

    def test_missing_selector_does_not_crash(self):
        """
        This is the core regression test: the original script called
        `.get_text()` directly on `select_one(...)`, which raises
        AttributeError when the element is absent (None). A single
        malformed card must not abort the whole parse.
        """
        result = parse_listings(MISSING_FIELD_HTML)
        assert result.total_cards_found == 1
        assert len(result.flagged_records) == 1
        assert len(result.valid_records) == 0
        flagged = result.flagged_records[0]
        assert "missing category" in flagged.issues
        assert flagged.company_name == "Beta Ltd"  # other fields still extracted

    def test_empty_element_is_flagged(self):
        result = parse_listings(EMPTY_FIELD_HTML)
        assert len(result.flagged_records) == 1
        assert "empty category" in result.flagged_records[0].issues

    def test_no_cards_found_returns_empty_result(self):
        result = parse_listings(NO_CARDS_HTML)
        assert result.total_cards_found == 0
        assert result.valid_records == []
        assert result.flagged_records == []

    def test_mixed_valid_and_invalid_cards(self):
        html = VALID_HTML + MISSING_FIELD_HTML
        result = parse_listings(html)
        assert result.total_cards_found == 2
        assert len(result.valid_records) == 1
        assert len(result.flagged_records) == 1


# ---------------------------------------------------------------------------
# fetch_html
# ---------------------------------------------------------------------------


class TestFetchHtml:
    def test_reads_local_file(self, tmp_path: Path):
        file_path = tmp_path / "page.html"
        file_path.write_text(VALID_HTML, encoding="utf-8")
        assert fetch_html(str(file_path)) == VALID_HTML

    def test_missing_local_file_raises(self, tmp_path: Path):
        missing = tmp_path / "does_not_exist.html"
        with pytest.raises(FileNotFoundError):
            fetch_html(str(missing))

    @patch("directory_scraper.core.requests.get")
    def test_fetches_live_url(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.text = VALID_HTML
        mock_response.raise_for_status.return_value = None

        result = fetch_html("https://example.com/directory")

        assert result == VALID_HTML
        mock_get.assert_called_once()

    @patch("directory_scraper.core.requests.get")
    def test_http_error_propagates(self, mock_get):
        mock_get.return_value.raise_for_status.side_effect = requests.HTTPError("404")
        with pytest.raises(requests.HTTPError):
            fetch_html("https://example.com/missing-page")


# ---------------------------------------------------------------------------
# CSV writers
# ---------------------------------------------------------------------------


class TestCsvWriters:
    def test_write_clean_csv(self, tmp_path: Path):
        records = [
            ListingRecord("Acme", "Retail", "123 St", "+880171", "a@b.com"),
        ]
        out = tmp_path / "clean.csv"
        write_clean_csv(records, out)
        content = out.read_text(encoding="utf-8")
        assert "Acme" in content
        assert "Company Name" in content

    def test_write_issues_csv_includes_issue_column(self, tmp_path: Path):
        records = [
            ListingRecord("Beta", "", "456 St", "+880199", "b@c.com", issues=["missing category"]),
        ]
        out = tmp_path / "issues.csv"
        write_issues_csv(records, out)
        content = out.read_text(encoding="utf-8")
        assert "_issues" in content
        assert "missing category" in content
