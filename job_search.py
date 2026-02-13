"""Search for entry-level tech/sales jobs at funded companies via ATS APIs."""

import logging
import re
import time

import pandas as pd
import requests

import config

logger = logging.getLogger(__name__)


def _matches_keywords(title: str, keywords: list[str]) -> bool:
    """Check if a job title contains any of the given keywords (case-insensitive)."""
    title_lower = f" {title.lower()} "
    return any(kw.lower() in title_lower for kw in keywords)


def _matches_location(location: str) -> bool:
    """Check if a job location matches the target area."""
    loc_lower = location.lower()
    return any(kw in loc_lower for kw in config.LOCATION_KEYWORDS)


def _generate_slugs(company_name: str) -> list[str]:
    """Generate ATS slug variations from a company name.

    E.g. "Gather AI" -> ["gatherai", "gather-ai", "gather"]
    """
    # Clean: lowercase, strip non-alphanumeric (keep spaces)
    cleaned = re.sub(r"[^a-z0-9\s]", "", company_name.lower()).strip()
    words = cleaned.split()

    slugs = []

    # Full name: joined and hyphenated
    if len(words) > 1:
        slugs.append("".join(words))
        slugs.append("-".join(words))

    # Single word or first word only
    if len(words) == 1:
        slugs.append(words[0])

    # Strip common suffixes and try those too
    stripped = [w for w in words if w not in config.SLUG_STRIP_SUFFIXES]
    if stripped and stripped != words:
        if len(stripped) > 1:
            slugs.append("".join(stripped))
            slugs.append("-".join(stripped))
        elif len(stripped) == 1:
            slugs.append(stripped[0])

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for s in slugs:
        if s not in seen:
            seen.add(s)
            unique.append(s)

    return unique


def _try_greenhouse(slug: str) -> list[dict] | None:
    """Try to fetch jobs from Greenhouse API. Returns list of jobs or None."""
    url = config.ATS_APIS["greenhouse"].format(slug=slug)
    try:
        resp = requests.get(url, timeout=config.ATS_REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        jobs = data.get("jobs", [])
        if not jobs:
            return None
        return [
            {
                "title": j.get("title", ""),
                "company": slug,
                "location": j.get("location", {}).get("name", ""),
                "job_url": j.get("absolute_url", ""),
                "ats_platform": "greenhouse",
            }
            for j in jobs
        ]
    except (requests.RequestException, ValueError):
        return None


def _try_lever(slug: str) -> list[dict] | None:
    """Try to fetch jobs from Lever API. Returns list of jobs or None."""
    url = config.ATS_APIS["lever"].format(slug=slug)
    try:
        resp = requests.get(url, timeout=config.ATS_REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not isinstance(data, list) or not data:
            return None
        return [
            {
                "title": j.get("text", ""),
                "company": slug,
                "location": j.get("categories", {}).get("location", ""),
                "job_url": j.get("hostedUrl", ""),
                "ats_platform": "lever",
            }
            for j in data
        ]
    except (requests.RequestException, ValueError):
        return None


def _try_ashby(slug: str) -> list[dict] | None:
    """Try to fetch jobs from Ashby API. Returns list of jobs or None."""
    url = config.ATS_APIS["ashby"].format(slug=slug)
    try:
        resp = requests.get(url, timeout=config.ATS_REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        jobs = data.get("jobs", [])
        if not jobs:
            return None
        return [
            {
                "title": j.get("title", ""),
                "company": slug,
                "location": j.get("location", ""),
                "job_url": j.get("jobUrl", ""),
                "ats_platform": "ashby",
            }
            for j in jobs
        ]
    except (requests.RequestException, ValueError):
        return None


ATS_FETCHERS = [
    ("greenhouse", _try_greenhouse),
    ("lever", _try_lever),
    ("ashby", _try_ashby),
]


def _fetch_company_jobs(company_name: str) -> tuple[list[dict], str]:
    """Try all ATS platforms with slug variations. Returns (jobs, platform) or ([], "")."""
    slugs = _generate_slugs(company_name)

    for slug in slugs:
        for platform_name, fetcher in ATS_FETCHERS:
            jobs = fetcher(slug)
            if jobs:
                logger.info(
                    "%s: found %d jobs on %s (slug: %s)",
                    company_name, len(jobs), platform_name, slug,
                )
                return jobs, platform_name
            time.sleep(0.3)  # small delay between API calls

    logger.info("%s: not found on any ATS platform", company_name)
    return [], ""


def _filter_jobs(jobs: list[dict]) -> list[dict]:
    """Apply role, entry-level, senior, and location filters to job listings."""
    filtered = []
    for job in jobs:
        title = job.get("title", "")
        location = job.get("location", "")

        # Must match a role keyword
        if not _matches_keywords(title, config.ROLE_KEYWORDS):
            continue
        # Must match an entry-level keyword
        if not _matches_keywords(title, config.ENTRY_LEVEL_KEYWORDS):
            continue
        # Must NOT match a senior keyword
        if _matches_keywords(title, config.SENIOR_KEYWORDS):
            continue
        # Must match target location
        if not _matches_location(location):
            continue

        filtered.append(job)

    return filtered


def search_company_jobs(company_name: str) -> pd.DataFrame:
    """Search for entry-level tech/sales jobs at a single company via ATS APIs.

    Returns a filtered DataFrame of matching jobs.
    """
    logger.info("Searching jobs for: %s", company_name)

    all_jobs, platform = _fetch_company_jobs(company_name)
    if not all_jobs:
        return pd.DataFrame()

    filtered = _filter_jobs(all_jobs)

    logger.info(
        "%s (%s): %d total -> %d after filtering",
        company_name, platform, len(all_jobs), len(filtered),
    )

    if not filtered:
        return pd.DataFrame()

    df = pd.DataFrame(filtered)
    df["searched_company"] = company_name
    return df


def search_all_companies(companies: list[str]) -> pd.DataFrame:
    """Search jobs for all funded companies via ATS APIs.

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
