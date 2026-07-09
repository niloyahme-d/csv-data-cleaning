# Directory Scraper

[![CI](https://github.com/niloyahme-d/business-directory-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/niloyahme-d/business-directory-scraper/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A fault-tolerant Python toolkit for extracting structured business listings
(name, category, address, phone, email) from directory-style HTML pages,
whether from a local file or a live URL.

## Why this exists

Directory pages are rarely perfectly uniform — a listing card here or there
is missing a category, or has an empty field. A naive scraper that assumes
every field is always present will crash on the first inconsistency. This
toolkit treats that as the normal case: each field is extracted
independently, and a card with a missing or empty field is flagged for
review rather than aborting the entire run.

## Features

- Works against a local HTML file or a live URL — same code path either way
- Per-field fault tolerance: a missing/empty selector on one card doesn't
  stop parsing of the rest
- Two output streams: clean, ready-to-use records and a separate report of
  flagged rows with a reason per field
- Configurable input source and output location via a proper CLI
- Centralized CSS selector mapping (`core.FIELD_SELECTORS`) for adapting to
  a different site's HTML structure

## Who this is for

- **Lead generation** — building a contact list from a public business
  directory instead of copy-pasting each entry by hand.
- **Market research** — pulling structured listings (competitors, vendors,
  service providers) from a directory site for analysis.
- **Anyone automating a repetitive "copy this into a spreadsheet" task**
  against a directory-style page.

## Responsible scraping

This tool fetches whatever page it's pointed at — using it responsibly is
the operator's responsibility, not something the code enforces for you:

- Check the target site's `robots.txt` and Terms of Service before scraping it.
- Add delays between requests if scraping multiple pages; don't hammer a
  server with rapid, repeated requests.
- Only collect data you have a legitimate right to use, and respect any
  usage restrictions the site publishes.
- Prefer a site's official API if one is available.

## Project structure

```
business-directory-scraper/
├── src/directory_scraper/
│   ├── core.py   # pure parsing/fetch logic, per-field fault tolerance
│   └── cli.py     # thin CLI wrapper (argparse + logging)
├── tests/
│   ├── test_core.py
│   └── test_cli.py
├── sample_data/
│   └── sample_directory.html
├── .github/workflows/ci.yml
├── pyproject.toml
└── LICENSE
```

## Installation

```bash
git clone https://github.com/niloyahme-d/business-directory-scraper.git
cd business-directory-scraper
pip install -e ".[dev]"
```

## Usage

Against a local HTML file:

```bash
scrape-directory --source sample_data/sample_directory.html --output-dir output/
```

Against a live URL:

```bash
scrape-directory --source https://example-directory.com/listings --output-dir output/
```

This writes two files to `output/`:

- `scraped_companies.csv` — records where every field was found
- `issues_report.csv` — records with a missing/empty field, and which
  field(s) triggered the flag

Run `scrape-directory --help` for all options.

## Adapting to a different site

Update the selector mapping in `src/directory_scraper/core.py`:

```python
FIELD_SELECTORS = {
    "company_name": ".company-name",
    "category": ".category",
    "address": ".address",
    "phone": ".phone",
    "email": ".email",
}
LISTING_CARD_SELECTOR = ".listing-card"
```

Open the target page's dev tools, inspect a listing card, and update these
selectors to match. No other code changes are needed.

## Development

```bash
pytest              # run tests with coverage
ruff check .         # lint
mypy src             # type-check
```

All three run automatically on every push via GitHub Actions.

## Scope and limitations

- Selectors are configured for one page structure at a time — scraping
  multiple differently-structured sites requires maintaining separate
  selector mappings or extending the config to support per-source profiles.
- No built-in rate limiting or pagination handling; both would be
  straightforward additions for large-scale or multi-page scraping.
- JavaScript-rendered pages (content loaded client-side) aren't supported —
  this fetches raw HTML only, so a headless browser (e.g. Playwright) would
  be needed for such sites.

## License

MIT — see [LICENSE](LICENSE).

---
**Connect:**
- LinkedIn: [YOUR_LINKEDIN_URL]
