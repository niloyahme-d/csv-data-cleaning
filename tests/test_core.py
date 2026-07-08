from __future__ import annotations

import csv
from pathlib import Path

import pytest

from data_cleaner.core import (
    CleanedRecord,
    clean_row,
    deduplicate,
    is_valid_email,
    load_rows,
    normalize_phone,
    run_cleaning,
    validate_columns,
    write_clean_csv,
    write_issues_csv,
)

# ---------------------------------------------------------------------------
# normalize_phone
# ---------------------------------------------------------------------------


class TestNormalizePhone:
    def test_local_format_with_leading_zero(self):
        assert normalize_phone("01711223344") == "+8801711223344"

    def test_already_has_country_code(self):
        assert normalize_phone("+8801711223344") == "+8801711223344"

    def test_country_code_no_plus(self):
        assert normalize_phone("8801711223344") == "+8801711223344"

    def test_spaces_and_dashes(self):
        assert normalize_phone("01711-223 344") == "+8801711223344"

    def test_parentheses_format(self):
        assert normalize_phone("(880) 1711-223344") == "+8801711223344"

    def test_none_input(self):
        assert normalize_phone(None) is None

    def test_empty_string(self):
        assert normalize_phone("") is None

    def test_too_short(self):
        assert normalize_phone("12345") is None

    def test_too_long(self):
        assert normalize_phone("017112233445566") is None

    def test_non_numeric_garbage(self):
        assert normalize_phone("call-me-maybe") is None

    def test_multiple_leading_zeros(self):
        assert normalize_phone("001711223344") == "+8801711223344"


# ---------------------------------------------------------------------------
# is_valid_email
# ---------------------------------------------------------------------------


class TestIsValidEmail:
    @pytest.mark.parametrize(
        "email",
        [
            "user@example.com",
            "first.last@sub.example.co",
            "a@b.co",
        ],
    )
    def test_valid_emails(self, email):
        assert is_valid_email(email) is True

    @pytest.mark.parametrize(
        "email",
        [
            "",
            "no-at-symbol.com",
            "missing-domain@",
            "@missing-local.com",
            "spaces in@email.com",
            "double@@at.com",
        ],
    )
    def test_invalid_emails(self, email):
        assert is_valid_email(email) is False


# ---------------------------------------------------------------------------
# clean_row
# ---------------------------------------------------------------------------


class TestCleanRow:
    def test_casing_and_whitespace_normalized(self):
        row = {
            "Company Name": "  aCme corp  ",
            "Contact Email": "  USER@EXAMPLE.COM  ",
            "Phone": "01711223344",
            "City": " dhaka ",
        }
        record = clean_row(row)
        assert record.company_name == "Acme Corp"
        assert record.contact_email == "user@example.com"
        assert record.city == "Dhaka"
        assert record.phone == "+8801711223344"
        assert record.is_valid

    def test_flags_missing_email(self):
        row = {"Company Name": "Acme", "Contact Email": "", "Phone": "01711223344", "City": "Dhaka"}
        record = clean_row(row)
        assert not record.is_valid
        assert "missing/invalid email" in record.issues

    def test_flags_invalid_phone(self):
        row = {"Company Name": "Acme", "Contact Email": "a@b.com", "Phone": "123", "City": "Dhaka"}
        record = clean_row(row)
        assert not record.is_valid
        assert "missing/invalid phone" in record.issues

    def test_flags_both_issues(self):
        row = {"Company Name": "Acme", "Contact Email": "bad-email", "Phone": "", "City": "Dhaka"}
        record = clean_row(row)
        assert set(record.issues) == {"missing/invalid email", "missing/invalid phone"}

    def test_missing_keys_do_not_raise(self):
        # Simulates a malformed row missing an expected column entirely.
        row = {"Company Name": "Acme"}
        record = clean_row(row)
        assert not record.is_valid


# ---------------------------------------------------------------------------
# deduplicate
# ---------------------------------------------------------------------------


class TestDeduplicate:
    def test_removes_case_insensitive_duplicates(self):
        records = [
            CleanedRecord("Acme Corp", "a@b.com", "+8801711223344", "Dhaka"),
            CleanedRecord("acme corp", "a2@b.com", "+8801711223344", "Dhaka"),
        ]
        unique, dup_count = deduplicate(records)
        assert len(unique) == 1
        assert dup_count == 1

    def test_keeps_first_occurrence(self):
        records = [
            CleanedRecord("Acme Corp", "first@b.com", "+8801711223344", "Dhaka"),
            CleanedRecord("Acme Corp", "second@b.com", "+8801711223344", "Dhaka"),
        ]
        unique, _ = deduplicate(records)
        assert unique[0].contact_email == "first@b.com"

    def test_different_phone_not_a_duplicate(self):
        records = [
            CleanedRecord("Acme Corp", "a@b.com", "+8801711223344", "Dhaka"),
            CleanedRecord("Acme Corp", "a@b.com", "+8801999999999", "Dhaka"),
        ]
        unique, dup_count = deduplicate(records)
        assert len(unique) == 2
        assert dup_count == 0

    def test_no_duplicates(self):
        records = [
            CleanedRecord("Acme", "a@b.com", "+8801711223344", "Dhaka"),
            CleanedRecord("Beta", "b@c.com", "+8801999999999", "Ctg"),
        ]
        unique, dup_count = deduplicate(records)
        assert len(unique) == 2
        assert dup_count == 0


# ---------------------------------------------------------------------------
# validate_columns
# ---------------------------------------------------------------------------


class TestValidateColumns:
    def test_valid_header(self):
        validate_columns(["Company Name", "Contact Email", "Phone", "City"])  # no raise

    def test_none_header_raises(self):
        with pytest.raises(ValueError, match="no header row"):
            validate_columns(None)

    def test_missing_column_raises(self):
        with pytest.raises(ValueError, match="Phone"):
            validate_columns(["Company Name", "Contact Email", "City"])


# ---------------------------------------------------------------------------
# End-to-end pipeline (I/O), using tmp_path fixture
# ---------------------------------------------------------------------------


class TestRunCleaningEndToEnd:
    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
        fieldnames = ["Company Name", "Contact Email", "Phone", "City"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_full_pipeline(self, tmp_path: Path):
        input_path = tmp_path / "input.csv"
        self._write_csv(
            input_path,
            [
                {
                    "Company Name": "Acme corp",
                    "Contact Email": "a@b.com",
                    "Phone": "01711223344",
                    "City": "dhaka",
                },
                {
                    "Company Name": "acme CORP",
                    "Contact Email": "dup@b.com",
                    "Phone": "01711223344",
                    "City": "dhaka",
                },
                {
                    "Company Name": "Beta Ltd",
                    "Contact Email": "bad-email",
                    "Phone": "01999999999",
                    "City": "ctg",
                },
                {
                    "Company Name": "Gamma Inc",
                    "Contact Email": "g@h.com",
                    "Phone": "",
                    "City": "khulna",
                },
            ],
        )

        result = run_cleaning(input_path)

        assert result.total_input_rows == 4
        assert result.duplicate_count == 1
        assert len(result.clean_records) == 3
        assert len(result.flagged_records) == 2

        clean_out = tmp_path / "cleaned_output.csv"
        issues_out = tmp_path / "issues_report.csv"
        write_clean_csv(result.clean_records, clean_out)
        write_issues_csv(result.flagged_records, issues_out)

        assert clean_out.exists()
        assert issues_out.exists()

        with open(clean_out, encoding="utf-8") as f:
            assert len(list(csv.DictReader(f))) == 3

    def test_missing_required_column_raises(self, tmp_path: Path):
        input_path = tmp_path / "bad.csv"
        with open(input_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Company Name", "City"])
            writer.writeheader()
            writer.writerow({"Company Name": "Acme", "City": "Dhaka"})

        with pytest.raises(ValueError):
            load_rows(input_path)
