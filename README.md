# Data Cleaner

[![CI](https://github.com/niloyahme-d/csv-data-cleaning/actions/workflows/ci.yml/badge.svg)](https://github.com/niloyahme-d/csv-data-cleaning/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A small, well-tested Python toolkit for cleaning, validating, and deduplicating
contact-list CSV exports (CRM exports, lead lists, scraped datasets).

## Why this exists

Raw contact data collected from forms, CRMs, or manual entry is rarely
consistent — inconsistent casing, mixed phone number formats, missing or
malformed emails, and duplicate records under slightly different spellings.
This toolkit turns that into a deterministic, testable pipeline rather than a
one-off script: normalization and validation rules live in a pure, unit-tested
core module, decoupled from I/O and the CLI layer.

## Features

- Whitespace trimming and Title Case normalization for names/cities
- Phone number normalization to a single canonical format (`+880XXXXXXXXXX`)
- Email format validation
- Case-insensitive duplicate detection on (company name, phone)
- Two output streams: clean, ready-to-use records and a separate report of
  flagged rows for human review
- Configurable input/output paths via a proper CLI (no hardcoded file paths)

## Project structure

```
csv-data-cleaning/
├── src/data_cleaner/
│   ├── core.py        # pure business logic: normalization, validation, dedup
│   └── cli.py          # thin CLI wrapper (argparse + logging)
├── tests/
│   └── test_core.py    # unit + end-to-end tests (pytest)
├── sample_data/
│   └── messy_sample.csv
├── .github/workflows/ci.yml   # lint + type-check + test on every push
├── pyproject.toml
└── LICENSE
```

## Installation

```bash
git clone https://github.com/niloyahme-d/csv-data-cleaning.git
cd csv-data-cleaning
pip install -e ".[dev]"
```

## Usage

```bash
clean-data --input sample_data/messy_sample.csv --output-dir output/
```

This writes two files to `output/`:

- `cleaned_output.csv` — validated, deduplicated, ready-to-use records
- `issues_report.csv` — rows flagged for manual review, with a reason per row

Run `clean-data --help` for all options.

## Development

Run the test suite (with coverage):

```bash
pytest
```

Lint and type-check:

```bash
ruff check .
mypy src
```

All three run automatically on every push via GitHub Actions.

## Design notes

- **Core logic is I/O-free.** `core.py` operates on plain dicts and dataclasses
  in, dataclasses out — no file handles are opened inside the cleaning
  functions. This is what makes every rule (phone normalization, email
  validation, dedup key logic) testable in isolation without touching disk.
- **Dataclasses over dicts for results.** `CleanedRecord` and `CleaningResult`
  give typed, self-documenting structures instead of passing loosely-shaped
  dictionaries between functions.
- **Deduplication key.** Records are deduplicated on
  `(company_name.lower(), normalized_phone)` rather than raw string equality,
  since the same company frequently appears with different casing/spacing
  across data sources.

## License

MIT — see [LICENSE](LICENSE).
