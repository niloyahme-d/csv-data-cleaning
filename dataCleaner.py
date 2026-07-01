"""
Data Cleaning & Deduplication Automation — Python Demo
--------------------------------------------------------
What this does, on a messy client spreadsheet:
    1. Trims stray whitespace
    2. Standardizes text casing (Title Case for names/cities)
    3. Normalizes phone numbers to a single format: +880XXXXXXXXXX
    4. Validates email addresses (flags missing/invalid ones)
    5. Removes duplicate rows (same company + same phone, regardless of
       casing/spacing differences)
    6. Produces:
        - cleaned_output.csv   -> ready-to-use clean data
        - issues_report.csv    -> flagged rows that need human review

Run: python clean_data.py
"""

import csv
import re
from pathlib import Path

INPUT_CSV = Path(__file__).parent / "messy_sample.csv"
CLEAN_OUTPUT = Path(__file__).parent / "cleaned_output.csv"
ISSUES_OUTPUT = Path(__file__).parent / "issues_report.csv"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_DIGITS_RE = re.compile(r"\d+")


def normalize_phone(raw: str) -> str | None:
    """Convert messy phone formats into +880XXXXXXXXXX, or None if invalid."""
    digits = "".join(PHONE_DIGITS_RE.findall(raw or ""))
    digits = digits.lstrip("0")          # drop leading 0 (e.g. 01711...)
    if digits.startswith("880"):
        digits = digits[3:]
    if len(digits) != 10:
        return None
    return f"+880{digits}"


def clean_row(row: dict) -> dict:
    company = row["Company Name"].strip().title()
    email = row["Contact Email"].strip().lower()
    city = row["City"].strip().title()
    phone = normalize_phone(row["Phone"])

    issues = []
    if not email or not EMAIL_RE.match(email):
        issues.append("missing/invalid email")
    if phone is None:
        issues.append("missing/invalid phone")

    return {
        "Company Name": company,
        "Contact Email": email,
        "Phone": phone or "",
        "City": city,
        "_issues": "; ".join(issues),
    }


def main():
    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        raw_rows = list(csv.DictReader(f))

    print(f"Loaded {len(raw_rows)} raw rows from {INPUT_CSV.name}")

    cleaned_rows = [clean_row(r) for r in raw_rows]

    # Deduplicate on (company name, phone) after normalization
    seen = set()
    unique_rows, issue_rows = [], []
    duplicate_count = 0

    for row in cleaned_rows:
        key = (row["Company Name"].lower(), row["Phone"])
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)

        if row["_issues"]:
            issue_rows.append(row)
        unique_rows.append(row)

    # Write clean output (drop internal _issues column)
    with open(CLEAN_OUTPUT, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["Company Name", "Contact Email", "Phone", "City"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in unique_rows:
            writer.writerow({k: row[k] for k in fieldnames})

    # Write issues report separately for human review
    with open(ISSUES_OUTPUT, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["Company Name", "Contact Email", "Phone", "City", "_issues"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in issue_rows:
            writer.writerow(row)

    print(f"Removed {duplicate_count} duplicate row(s).")
    print(f"Clean rows saved: {len(unique_rows)} -> {CLEAN_OUTPUT.name}")
    print(f"Rows flagged for review: {len(issue_rows)} -> {ISSUES_OUTPUT.name}")


if __name__ == "__main__":
    main()
