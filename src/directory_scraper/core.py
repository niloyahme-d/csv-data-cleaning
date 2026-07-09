"""
Core parsing logic for extracting structured business records from a
directory-style HTML page.

Design notes
------------
Field extraction is per-field fault-tolerant: a single missing/malformed
element on one listing card is recorded as an issue on that record rather
than raising and aborting the entire parse. This mirrors real-world
directory pages, which are rarely perfectly consistent across every card.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

# CSS selectors for each field, relative to a `.listing-card` element.
# Centralized here so adapting to a different site only requires editing
# this mapping.
FIELD_SELECTORS: dict[str, str] = {
    "company_name": ".company-name",
    "category": ".category",
    "address": ".address",
    "phone": ".phone",
    "email": ".email",
}

LISTING_CARD_SELECTOR = ".listing-card"
REQUEST_TIMEOUT_SECONDS = 10
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DirectoryScraper/1.0)"}


@dataclass
class ListingRecord:
    """A single extracted business listing."""

    company_name: str
    category: str
    address: str
    phone: str
    email: str
    issues: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.issues

    def to_row(self) -> dict[str, str]:
        return {
            "Company Name": self.company_name,
            "Category": self.category,
            "Address": self.address,
            "Phone": self.phone,
            "Email": self.email,
        }

    def to_issue_row(self) -> dict[str, str]:
        row = self.to_row()
        row["_issues"] = "; ".join(self.issues)
        return row


@dataclass
class ParseResult:
    """Aggregate result of parsing a directory page."""

    valid_records: list[ListingRecord]
    flagged_records: list[ListingRecord]
    total_cards_found: int


def clean_text(value: str | None) -> str:
    """Collapse internal whitespace/newlines and strip leading/trailing space."""
    return re.sub(r"\s+", " ", value or "").strip()


def is_url(source: str) -> bool:
    return urlparse(source).scheme in ("http", "https")


def fetch_html(source: str) -> str:
    """
    Load page HTML from either a local file path or a live URL.

    Raises FileNotFoundError for a missing local file, or
    requests.HTTPError / requests.ConnectionError for a failed fetch.
    """
    if is_url(source):
        response = requests.get(source, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.text

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Local source file not found: {path}")
    return path.read_text(encoding="utf-8")


def _extract_field(card: Tag, field_name: str, selector: str) -> tuple[str, str | None]:
    """
    Extract a single field from a listing card.

    Returns (value, issue). value is "" and issue is a description string
    when the selector doesn't match or the element has no text.
    """
    element = card.select_one(selector)
    if element is None:
        return "", f"missing {field_name}"

    text = clean_text(element.get_text())
    if not text:
        return "", f"empty {field_name}"

    return text, None


def parse_listings(html: str) -> ParseResult:
    """Extract structured records from every listing card on the page."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(LISTING_CARD_SELECTOR)

    valid_records: list[ListingRecord] = []
    flagged_records: list[ListingRecord] = []

    for card in cards:
        values: dict[str, str] = {}
        issues: list[str] = []

        for field_name, selector in FIELD_SELECTORS.items():
            value, issue = _extract_field(card, field_name, selector)
            values[field_name] = value
            if issue:
                issues.append(issue)

        record = ListingRecord(
            company_name=values["company_name"],
            category=values["category"],
            address=values["address"],
            phone=values["phone"],
            email=values["email"],
            issues=issues,
        )

        if record.is_valid:
            valid_records.append(record)
        else:
            flagged_records.append(record)

    return ParseResult(
        valid_records=valid_records,
        flagged_records=flagged_records,
        total_cards_found=len(cards),
    )


def write_clean_csv(records: list[ListingRecord], output_path: Path) -> None:
    import csv

    fieldnames = ["Company Name", "Category", "Address", "Phone", "Email"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_row())


def write_issues_csv(records: list[ListingRecord], output_path: Path) -> None:
    import csv

    fieldnames = ["Company Name", "Category", "Address", "Phone", "Email", "_issues"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_issue_row())
