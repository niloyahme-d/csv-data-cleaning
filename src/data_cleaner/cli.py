"""
Command-line interface for the data cleaning pipeline.

Usage:
    clean-data --input path/to/messy.csv --output-dir path/to/out
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from data_cleaner.core import run_cleaning, write_clean_csv, write_issues_csv

logger = logging.getLogger("data_cleaner")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clean-data",
        description="Clean, validate, and deduplicate a contact list CSV.",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="Path to the raw input CSV file.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("."),
        help="Directory where cleaned_output.csv and issues_report.csv will be written "
        "(default: current directory).",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress INFO-level logging; only warnings/errors are shown.",
    )
    return parser


def configure_logging(quiet: bool) -> None:
    logging.basicConfig(
        level=logging.WARNING if quiet else logging.INFO,
        format="%(levelname)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.quiet)

    if not args.input.exists():
        logger.error("Input file not found: %s", args.input)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    clean_path = args.output_dir / "cleaned_output.csv"
    issues_path = args.output_dir / "issues_report.csv"

    try:
        result = run_cleaning(args.input)
    except ValueError as exc:
        logger.error(str(exc))
        return 1

    write_clean_csv(result.clean_records, clean_path)
    write_issues_csv(result.flagged_records, issues_path)

    logger.info("Loaded %d raw row(s) from %s", result.total_input_rows, args.input.name)
    logger.info("Removed %d duplicate row(s).", result.duplicate_count)
    logger.info("Clean rows written: %d -> %s", len(result.clean_records), clean_path)
    logger.info("Rows flagged for review: %d -> %s", len(result.flagged_records), issues_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
