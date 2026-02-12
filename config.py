"""Configuration constants for the StrictlyVC funding scraper."""

# StrictlyVC sitemap
SITEMAP_URL = "https://newsletter.strictlyvc.com/sitemap.xml"

# Default scraping parameters
DEFAULT_MAX_ARTICLES = 5
DEFAULT_DAYS_BACK = 7
PAGE_LOAD_DELAY = 2  # seconds between page loads
CONTENT_SELECTOR = "#content-blocks"
PLAYWRIGHT_TIMEOUT = 30_000  # ms

# Funding section headings (case-insensitive matching)
FUNDING_HEADINGS = [
    "massive fundings",
    "big-but-not-crazy-big fundings",
    "smaller fundings",
]

# Job search parameters
JOB_SEARCH_LOCATION = "New York, NY"
JOB_SEARCH_DISTANCE_MILES = 25
JOB_SEARCH_DELAY = 4  # seconds between company searches
JOB_SEARCH_RESULTS_WANTED = 20  # per company per site

# Entry-level keywords (matched case-insensitively against job title)
ENTRY_LEVEL_KEYWORDS = [
    "entry level",
    "entry-level",
    "junior",
    "associate",
    "analyst",
    "new grad",
    "new graduate",
    "jr.",
    "jr ",
    "i ",  # e.g. "Software Engineer I"
    " 1",  # e.g. "Analyst 1"
]

# Tech/sales role keywords (matched case-insensitively against job title)
ROLE_KEYWORDS = [
    "software",
    "engineer",
    "developer",
    "programming",
    "data",
    "machine learning",
    "ml ",
    "ai ",
    "devops",
    "cloud",
    "frontend",
    "front-end",
    "backend",
    "back-end",
    "fullstack",
    "full-stack",
    "sales",
    "sdr",
    "bdr",
    "account executive",
    "business development",
    "solutions",
    "product",
    "technical",
    "it ",
    "security",
    "qa",
    "quality assurance",
    "support engineer",
]

# Output directory
DATA_DIR = "data"
