"""Extract funding sections from StrictlyVC articles and parse company data."""

import logging
import re

from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)

# Regex patterns ordered by specificity (most specific first).
# StrictlyVC template: "[Company], a [age]-year-old, [location]-based [description],
#   has raised $[amount] in [round type] funding led by [investor]..."
FUNDING_PATTERNS = [
    # Pattern 1: Full template with age, location, description, amount, round, lead investor
    # "Company, a X-year-old, Location-based description, raised a $X Series Y round led by Investor."
    re.compile(
        r"^(?P<company>[A-Z][^,]+),\s+"
        r"a\s+.+?[,-]\s*"
        r"(?P<location>[A-Za-z\s.]+?)-based\s+"
        r"(?P<description>[^,]+?),\s+"
        r"(?:has\s+)?raised\s+(?:a\s+)?\$(?P<amount>[\d.,]+\s*(?:billion|million)?)\s+"
        r"(?:in\s+)?(?P<round>[^.]*?(?:round|funding|seed)[^.]*?)"
        r"(?:\s*led\s*by\s*(?P<lead_investor>[^,.]+?))?[.,]",
        re.IGNORECASE,
    ),
    # Pattern 2: Without age — "Company, a location-based description, raised..."
    re.compile(
        r"^(?P<company>[A-Z][^,]+),\s+"
        r"a\s+(?P<location>[A-Za-z\s.]+?)-based\s+"
        r"(?P<description>[^,]+?),\s+"
        r"(?:has\s+)?raised\s+(?:a\s+)?\$(?P<amount>[\d.,]+\s*(?:billion|million)?)\s+"
        r"(?:in\s+)?(?P<round>[^.]*?(?:round|funding|seed)[^.]*?)"
        r"(?:\s*led\s*by\s*(?P<lead_investor>[^,.]+?))?[.,]",
        re.IGNORECASE,
    ),
    # Pattern 3: Minimal — "Company ... raised $X ... round/funding/seed"
    re.compile(
        r"^(?P<company>[A-Z][^,]+),\s+.*?"
        r"(?:has\s+)?raised\s+(?:a\s+)?\$(?P<amount>[\d.,]+\s*(?:billion|million)?)\s+"
        r"(?:in\s+)?(?P<round>[^.]*?(?:round|funding|seed)[^.]*?)"
        r"(?:\s*led\s*by\s*(?P<lead_investor>[^,.]+?))?[.,]",
        re.IGNORECASE,
    ),
]


def extract_funding_sections(html: str) -> list[dict]:
    """Find funding section headings and collect paragraphs under each.

    Beehiiv wraps each heading in its own <div>, with content <div>/<p> elements
    as siblings of that wrapper. We find the wrapper, then walk its siblings.

    Returns list of dicts: {section, paragraphs: [str]}
    """
    soup = BeautifulSoup(html, "lxml")
    sections = []

    # Find all headings that match funding section names
    heading_elements = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "strong", "b", "p"]):
        text = el.get_text(strip=True).lower()
        for heading in config.FUNDING_HEADINGS:
            if heading in text:
                heading_elements.append((el, heading))
                break

    for heading_el, section_name in heading_elements:
        paragraphs = []

        # Navigate up to the wrapper div that is a direct child of the content container.
        # Beehiiv structure: <div id="massive-fundings"><h2>...</h2></div>
        start = heading_el
        while start.parent and start.parent.name not in (None, "body", "[document]"):
            if start.parent.get("id") == "content-blocks" or "post-content" in " ".join(
                start.parent.get("class", [])
            ):
                break
            start = start.parent

        for sibling in start.find_next_siblings():
            sib_text = sibling.get_text(strip=True)
            sib_lower = sib_text.lower()

            # Stop if this sibling contains a section heading (funding or other known h2)
            inner_h = sibling.find(["h1", "h2", "h3", "h4"])
            if inner_h or any(h in sib_lower for h in config.FUNDING_HEADINGS):
                break

            if sib_text and len(sib_text) > 20:
                paragraphs.append(sib_text)

        if paragraphs:
            sections.append({"section": section_name, "paragraphs": paragraphs})
            logger.info("Section '%s': %d paragraphs", section_name, len(paragraphs))

    return sections


def parse_funding_paragraph(text: str) -> dict:
    """Apply regex patterns to extract structured data from a single funding paragraph.

    Returns dict with keys: company, amount, round, location, description,
    lead_investor, raw_text, parsed (bool).
    """
    for pattern in FUNDING_PATTERNS:
        match = pattern.search(text)
        if match:
            groups = match.groupdict()
            return {
                "company": groups.get("company", "").strip(),
                "amount": groups.get("amount", "").strip(),
                "round": groups.get("round", "").strip(),
                "location": groups.get("location", "").strip() if groups.get("location") else "",
                "description": groups.get("description", "").strip() if groups.get("description") else "",
                "lead_investor": groups.get("lead_investor", "").strip() if groups.get("lead_investor") else "",
                "raw_text": text,
                "parsed": True,
            }

    logger.warning("Could not parse funding paragraph: %.100s...", text)
    return {
        "company": "",
        "amount": "",
        "round": "",
        "location": "",
        "description": "",
        "lead_investor": "",
        "raw_text": text,
        "parsed": False,
    }


def parse_article(article: dict) -> list[dict]:
    """Parse a single article's HTML for funding entries.

    Args:
        article: dict with keys url, html, text

    Returns list of parsed funding dicts (with source_url added).
    """
    sections = extract_funding_sections(article["html"])
    entries = []

    for section in sections:
        for para in section["paragraphs"]:
            entry = parse_funding_paragraph(para)
            entry["section"] = section["section"]
            entry["source_url"] = article["url"]
            entries.append(entry)

    logger.info(
        "Article %s: %d entries (%d parsed)",
        article["url"],
        len(entries),
        sum(1 for e in entries if e["parsed"]),
    )
    return entries
