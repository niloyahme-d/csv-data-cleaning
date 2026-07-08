"""
Core data-cleaning logic for tabular contact records.

Design notes
------------
Business logic (normalization, validation, deduplication) is kept fully
decoupled from I/O. This makes every function independently unit-testable
and allows the CLI layer (see `cli.py`) to remain a thin wrapper.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DIGITS_PATTERN = re.compile(r"\d+")

REQUIRED_COLUMNS = ("Company Name", "Contact Email", "Phone", "City")


@dataclass
class CleanedRecord:
    """A single cleaned/validated record."""

    company_name: str
    contact_email: str
    phone: str
    city: str
    issues: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.issues

    @property
    def dedup_key(self) -> tuple[str, str]:
        """Key used to detect duplicate records (case-insensitive company + normalized phone)."""
        return (self.company_name.lower(), self.phone)

    def to_row(self) -> dict[str, str]:
        return {
            "Company Name": self.company_name,
            "Contact Email": self.contact_email,
            "Phone": self.phone,
            "City": self.city,
        }

    def to_issue_row(self) -> dict[str, str]:
        row = self.to_row()
        row["_issues"] = "; ".join(self.issues)
        return row


@dataclass
class CleaningResult:
    """Aggregate result of a full cleaning run."""

    clean_records: list[CleanedRecord]
    flagged_records: list[CleanedRecord]
    duplicate_count: int
    total_input_rows: int


def normalize_phone(raw: str | None) -> str | None:
    """
    Normalize a Bangladeshi phone number to the canonical `+880XXXXXXXXXX` form.

    Returns None if the input cannot be resolved to a valid 10-digit
    subscriber number after stripping the country/leading-zero prefix.
    """
    if not raw:
        return None

    digits = "".join(DIGITS_PATTERN.findall(raw))
    digits = digits.lstrip("0")

    if digits.startswith("880"):
        digits = digits[3:]

    if len(digits) != 10:
        return None

    return f"+880{digits}"


def is_valid_email(email: str) -> bool:
    return bool(email) and bool(EMAIL_PATTERN.match(email))


def clean_row(row: dict[str, str]) -> CleanedRecord:
    """Normalize and validate a single raw CSV row into a CleanedRecord."""
    company = (row.get("Company Name") or "").strip().title()
    email = (row.get("Contact Email") or "").strip().lower()
    city = (row.get("City") or "").strip().title()
    phone = normalize_phone(row.get("Phone"))

    issues: list[str] = []
    if not is_valid_email(email):
        issues.append("missing/invalid email")
    if phone is None:
        issues.append("missing/invalid phone")

    return CleanedRecord(
        company_name=company,
        contact_email=email,
        phone=phone or "",
        city=city,
        issues=issues,
    )


def validate_columns(fieldnames: Sequence[str] | None) -> None:
    if fieldnames is None:
        raise ValueError("Input CSV has no header row.")
    missing = [c for c in REQUIRED_COLUMNS if c not in fieldnames]
    if missing:
        raise ValueError(f"Input CSV is missing required column(s): {', '.join(missing)}")


def load_rows(input_path: Path) -> list[dict[str, str]]:
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        validate_columns(reader.fieldnames)
        return list(reader)


def deduplicate(records: list[CleanedRecord]) -> tuple[list[CleanedRecord], int]:
    """
    Remove duplicate records based on (company name, normalized phone).
    Returns (unique_records, duplicate_count).
    """
    seen: set[tuple[str, str]] = set()
    unique: list[CleanedRecord] = []
    duplicates = 0

    for record in records:
        key = record.dedup_key
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        unique.append(record)

    return unique, duplicates


def run_cleaning(input_path: Path) -> CleaningResult:
    """End-to-end pipeline: load -> clean -> deduplicate. Pure function, no writes."""
    raw_rows = load_rows(input_path)
    cleaned = [clean_row(r) for r in raw_rows]
    unique_records, duplicate_count = deduplicate(cleaned)
    flagged = [r for r in unique_records if not r.is_valid]

    return CleaningResult(
        clean_records=unique_records,
        flagged_records=flagged,
        duplicate_count=duplicate_count,
        total_input_rows=len(raw_rows),
    )


def write_clean_csv(records: list[CleanedRecord], output_path: Path) -> None:
    fieldnames = list(REQUIRED_COLUMNS)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_row())


def write_issues_csv(records: list[CleanedRecord], output_path: Path) -> None:
    fieldnames = [*REQUIRED_COLUMNS, "_issues"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_issue_row())
