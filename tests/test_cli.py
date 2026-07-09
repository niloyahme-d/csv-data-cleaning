from __future__ import annotations

import csv
from pathlib import Path

from data_cleaner.cli import main


def _write_sample_csv(path: Path) -> None:
    fieldnames = ["Company Name", "Contact Email", "Phone", "City"]
    rows = [
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
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class TestCliMain:
    def test_successful_run_creates_output_files(self, tmp_path: Path):
        input_path = tmp_path / "input.csv"
        output_dir = tmp_path / "out"
        _write_sample_csv(input_path)

        exit_code = main(["--input", str(input_path), "--output-dir", str(output_dir), "--quiet"])

        assert exit_code == 0
        assert (output_dir / "cleaned_output.csv").exists()
        assert (output_dir / "issues_report.csv").exists()

        with open(output_dir / "cleaned_output.csv", encoding="utf-8") as f:
            assert len(list(csv.DictReader(f))) == 2  # 3 rows - 1 duplicate

    def test_missing_input_file_returns_error_code(self, tmp_path: Path):
        missing_path = tmp_path / "does_not_exist.csv"
        output_dir = tmp_path / "out"

        exit_code = main(["--input", str(missing_path), "--output-dir", str(output_dir)])

        assert exit_code == 1
        assert not (output_dir / "cleaned_output.csv").exists()

    def test_malformed_csv_missing_columns_returns_error_code(self, tmp_path: Path):
        input_path = tmp_path / "bad.csv"
        output_dir = tmp_path / "out"
        with open(input_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Company Name", "City"])
            writer.writeheader()
            writer.writerow({"Company Name": "Acme", "City": "Dhaka"})

        exit_code = main(["--input", str(input_path), "--output-dir", str(output_dir)])

        assert exit_code == 1

    def test_output_dir_created_if_missing(self, tmp_path: Path):
        input_path = tmp_path / "input.csv"
        output_dir = tmp_path / "nested" / "out"
        _write_sample_csv(input_path)

        exit_code = main(["--input", str(input_path), "--output-dir", str(output_dir), "--quiet"])

        assert exit_code == 0
        assert output_dir.exists()
