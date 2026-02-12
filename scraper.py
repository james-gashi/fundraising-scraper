"""Fetch sitemap and scrape StrictlyVC articles via Playwright."""

import logging
import time
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

import config

logger = logging.getLogger(__name__)

SITEMAP_NS = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def fetch_article_urls(days_back: int = config.DEFAULT_DAYS_BACK) -> list[dict]:
    """Fetch sitemap.xml and return article URLs published within `days_back` days.

    Returns list of dicts with keys: url, lastmod (datetime).
    """
    logger.info("Fetching sitemap from %s", config.SITEMAP_URL)
    resp = requests.get(config.SITEMAP_URL, timeout=30)
    resp.raise_for_status()

    root = ElementTree.fromstring(resp.content)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    articles = []
    for url_elem in root.findall("ns:url", SITEMAP_NS):
        loc = url_elem.findtext("ns:loc", namespaces=SITEMAP_NS)
        lastmod_text = url_elem.findtext("ns:lastmod", namespaces=SITEMAP_NS)

        if not loc or "/p/" not in loc:
            continue

        lastmod = None
        if lastmod_text:
            # Handle both "2024-01-15" and "2024-01-15T10:00:00Z" formats
            lastmod_text = lastmod_text.strip()
            try:
                lastmod = datetime.fromisoformat(lastmod_text.replace("Z", "+00:00"))
                if lastmod.tzinfo is None:
                    lastmod = lastmod.replace(tzinfo=timezone.utc)
            except ValueError:
                try:
                    lastmod = datetime.strptime(lastmod_text, "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                except ValueError:
                    logger.warning("Could not parse lastmod '%s' for %s", lastmod_text, loc)

        if lastmod and lastmod < cutoff:
            continue

        articles.append({"url": loc, "lastmod": lastmod})

    # Sort newest first
    articles.sort(key=lambda a: a["lastmod"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    logger.info("Found %d articles within the last %d days", len(articles), days_back)
    return articles


def scrape_articles(urls: list[str]) -> list[dict]:
    """Use Playwright to render each article URL and extract content.

    Returns list of dicts with keys: url, html, text.
    """
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for i, url in enumerate(urls):
            logger.info("Scraping article %d/%d: %s", i + 1, len(urls), url)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=config.PLAYWRIGHT_TIMEOUT)
                page.wait_for_selector(config.CONTENT_SELECTOR, timeout=config.PLAYWRIGHT_TIMEOUT)

                content_el = page.query_selector(config.CONTENT_SELECTOR)
                if content_el:
                    html = content_el.inner_html()
                    text = content_el.inner_text()
                    results.append({"url": url, "html": html, "text": text})
                else:
                    logger.warning("No content found at %s", url)
            except Exception:
                logger.exception("Failed to scrape %s", url)

            if i < len(urls) - 1:
                time.sleep(config.PAGE_LOAD_DELAY)

        browser.close()

    logger.info("Successfully scraped %d/%d articles", len(results), len(urls))
    return results
