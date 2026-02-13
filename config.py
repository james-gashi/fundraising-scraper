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
JOB_SEARCH_DELAY = 1  # seconds between ATS API requests

# ATS (Applicant Tracking System) API endpoints
ATS_APIS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever": "https://api.lever.co/v0/postings/{slug}",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
}
ATS_REQUEST_TIMEOUT = 10  # seconds

# Location keywords for filtering job locations (case-insensitive)
LOCATION_KEYWORDS = ["new york", "nyc", "ny", "remote"]

# Common company name suffixes to strip when generating ATS slugs
SLUG_STRIP_SUFFIXES = [
    "inc", "llc", "co", "corp", "corporation", "company",
    "ai", "labs", "lab", "technologies", "technology", "tech",
    "health", "medical", "therapeutics", "bio", "biotechnologies",
    "systems", "security", "robotics", "holdings", "enterprises",
    "services", "solutions", "markets", "computing",
]

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
    " i ",  # e.g. "Software Engineer I" (standalone Roman numeral)
    " 1 ",  # e.g. "Analyst 1" (standalone number)
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
    " ai ",
    "devops",
    "cloud",
    "frontend",
    "front-end",
    "backend",
    "back-end",
    "fullstack",
    "full-stack",
    "sdr",
    "bdr",
    "account executive",
    "business development",
    "sales development",
    "sales engineer",
    "solutions",
    "product",
    "technical",
    " it ",
    "security",
    "qa",
    "quality assurance",
    "support engineer",
]

# Senior/executive keywords to exclude (matched case-insensitively against job title)
SENIOR_KEYWORDS = [
    "senior",
    "sr.",
    "sr ",
    "staff",
    "principal",
    "lead",
    "manager",
    "director",
    "vp ",
    "vice president",
    "head of",
    "chief",
    "architect",
    "distinguished",
    " ii",   # Roman numeral levels II+
    " iii",
    " iv",
    " v ",
    "strategist",
]

# Output directory
DATA_DIR = "data"
