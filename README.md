# StrictlyVC Funding Scraper & Job Finder

## What It Does

An automated pipeline that reads the StrictlyVC newsletter (a daily venture capital digest), extracts every company that just raised funding, and then searches those companies' actual job boards for entry-level tech and sales development positions in the NYC area.

## How It Works

```
StrictlyVC Sitemap XML
        |
        v
  Discover recent articles (last 7 days)
        |
        v
  Render pages with Playwright
  (newsletter platform is JS-rendered)
        |
        v
  Parse funding sections with BeautifulSoup + regex
  Extract: company name, amount, round, location, investors
        |
        v
  For each company, query ATS APIs:
  Greenhouse / Lever / Ashby
        |
        v
  Filter jobs by:
  1. Role type (engineering, data, sales dev, product, etc.)
  2. Entry-level indicators (junior, associate, analyst, new grad)
  3. Exclude senior titles (senior, staff, lead, director, etc.)
  4. Location (NYC or remote)
        |
        v
  Output: CSV files + Flask web dashboard
```

## Technical Details

**Web Scraping:** Playwright for JS-rendered content, BeautifulSoup/lxml for HTML parsing, regex for structured text extraction from natural language funding paragraphs.

**ATS Integration:** Instead of searching generic job boards (which return irrelevant results), the tool queries each company's actual job board via public APIs from Greenhouse, Lever, and Ashby -- the three most common applicant tracking systems used by funded startups. Company names are converted into URL slugs with suffix-stripping logic to maximize match rates.

**Job Filtering:** Three-pass keyword system filters thousands of listings down to relevant entry-level roles while excluding senior positions, using substring matching with word-boundary awareness to avoid false positives.

**Interfaces:** CLI with configurable flags (lookback window, max articles, output format) and a Flask web UI with background pipeline execution and poll-based progress updates.

## Tech Stack

Python, Playwright, BeautifulSoup, lxml, pandas, Flask, requests

## Setup

```bash
pip install playwright beautifulsoup4 lxml pandas flask requests
playwright install chromium
```

## Usage

**CLI:**
```bash
python main.py                       # full pipeline (scrape + jobs)
python main.py --skip-jobs           # scrape fundings only
python main.py --days 14             # look back 14 days
python main.py --max-articles 10     # scrape up to 10 articles
python main.py --output-format json  # output as JSON instead of CSV
```

**Web UI:**
```bash
python app.py                        # starts Flask on http://localhost:5000
```

## Sample Output

From a single run scanning 5 articles:
- **105 funding entries** extracted (90 successfully parsed)
- **89 companies** identified and searched across 3 ATS platforms
- **30+ companies** found on at least one ATS platform
- Filtered results returned verified, entry-level positions at the actual funded companies
