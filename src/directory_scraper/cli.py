"""
Command-line interface for the directory scraper.

Usage:
    scrape-directory --source path/to/page.html --output-dir out/
    scrape-directory --source https://example-directory.com/listings --output-dir out/
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import requests

from directory_scraper.core import fetch_html, parse_listings, write_clean_csv, write_issues_csv

logger = logging.getLogger("directory_scraper")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scrape-directory",
        description="Extract business listings from a directory page (local file or live URL).",
    )
    parser.add_argument(
        "--source",
        "-s",
        required=True,
        help="Local HTML file path or a live http(s) URL to scrape.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("."),
        help="Directory where scraped_companies.csv and issues_report.csv will be written "
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

    args.output_dir.mkdir(parents=True, exist_ok=True)
    clean_path = args.output_dir / "scraped_companies.csv"
    issues_path = args.output_dir / "issues_report.csv"

    try:
        html = fetch_html(args.source)
    except FileNotFoundError as exc:
        logger.error(str(exc))
        return 1
    except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as exc:
        logger.error("Failed to fetch source: %s", exc)
        return 1

    result = parse_listings(html)

    if result.total_cards_found == 0:
        logger.warning(
            "No listing cards found. Check that the CSS selectors in "
            "core.FIELD_SELECTORS / LISTING_CARD_SELECTOR match this page's HTML structure."
        )

    write_clean_csv(result.valid_records, clean_path)
    write_issues_csv(result.flagged_records, issues_path)

    logger.info("Listing cards found: %d", result.total_cards_found)
    logger.info("Clean records written: %d -> %s", len(result.valid_records), clean_path)
    logger.info("Records flagged for review: %d -> %s", len(result.flagged_records), issues_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
