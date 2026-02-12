"""Search for entry-level tech/sales jobs at funded companies via python-jobspy."""

import logging
import time

import pandas as pd
from jobspy import scrape_jobs

import config

logger = logging.getLogger(__name__)


def _matches_keywords(title: str, keywords: list[str]) -> bool:
    """Check if a job title contains any of the given keywords (case-insensitive)."""
    title_lower = f" {title.lower()} "
    return any(kw.lower() in title_lower for kw in keywords)


def search_company_jobs(company_name: str) -> pd.DataFrame:
    """Search for entry-level tech/sales jobs at a single company in NYC.

    Returns a filtered DataFrame of matching jobs.
    """
    logger.info("Searching jobs for: %s", company_name)
    try:
        jobs = scrape_jobs(
            site_name=["indeed", "google"],
            search_term=company_name,
            location=config.JOB_SEARCH_LOCATION,
            distance=config.JOB_SEARCH_DISTANCE_MILES,
            results_wanted=config.JOB_SEARCH_RESULTS_WANTED,
            country_indeed="USA",
        )
    except Exception:
        logger.exception("Job search failed for %s", company_name)
        return pd.DataFrame()

    if jobs.empty:
        logger.info("No jobs found for %s", company_name)
        return jobs

    # Filter: title must match at least one role keyword
    role_mask = jobs["title"].apply(lambda t: _matches_keywords(str(t), config.ROLE_KEYWORDS))
    filtered = jobs[role_mask].copy()

    # Filter: title should match entry-level keywords
    entry_mask = filtered["title"].apply(
        lambda t: _matches_keywords(str(t), config.ENTRY_LEVEL_KEYWORDS)
    )
    filtered = filtered[entry_mask].copy()

    if not filtered.empty:
        filtered["searched_company"] = company_name

    logger.info(
        "%s: %d total results -> %d after filtering",
        company_name,
        len(jobs),
        len(filtered),
    )
    return filtered


def search_all_companies(companies: list[str]) -> pd.DataFrame:
    """Search jobs for all funded companies, with delays between requests.

    Args:
        companies: list of company names to search

    Returns combined DataFrame of all matching jobs.
    """
    all_jobs = []

    for i, company in enumerate(companies):
        df = search_company_jobs(company)
        if not df.empty:
            all_jobs.append(df)

        if i < len(companies) - 1:
            time.sleep(config.JOB_SEARCH_DELAY)

    if all_jobs:
        combined = pd.concat(all_jobs, ignore_index=True)
        logger.info("Total matching jobs across all companies: %d", len(combined))
        return combined

    logger.info("No matching jobs found for any company")
    return pd.DataFrame()
