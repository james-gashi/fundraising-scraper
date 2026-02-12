"""CLI entry point for the StrictlyVC funding scraper & NYC job finder."""

import argparse
import logging
import sys

import pandas as pd

import config
from job_search import search_all_companies
from output import save_combined, save_fundings, save_jobs
from parser import parse_article
from scraper import fetch_article_urls, scrape_articles


def main():
    ap = argparse.ArgumentParser(
        description="Scrape StrictlyVC for funded companies and find entry-level NYC jobs."
    )
    ap.add_argument(
        "--max-articles",
        type=int,
        default=config.DEFAULT_MAX_ARTICLES,
        help=f"Maximum articles to scrape (default: {config.DEFAULT_MAX_ARTICLES})",
    )
    ap.add_argument(
        "--days",
        type=int,
        default=config.DEFAULT_DAYS_BACK,
        help=f"Look back N days for articles (default: {config.DEFAULT_DAYS_BACK})",
    )
    ap.add_argument(
        "--skip-jobs",
        action="store_true",
        help="Skip the job search step (only scrape fundings)",
    )
    ap.add_argument(
        "--output-format",
        choices=["csv", "json"],
        default="csv",
        help="Output file format (default: csv)",
    )
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Step 1: Discover articles from sitemap
    logger.info("=== Step 1: Fetching article URLs (last %d days) ===", args.days)
    articles = fetch_article_urls(days_back=args.days)
    if not articles:
        logger.warning("No articles found. Exiting.")
        sys.exit(0)

    urls = [a["url"] for a in articles[: args.max_articles]]
    logger.info("Will scrape %d article(s)", len(urls))

    # Step 2: Scrape article content with Playwright
    logger.info("=== Step 2: Scraping articles with Playwright ===")
    scraped = scrape_articles(urls)
    if not scraped:
        logger.warning("No articles could be scraped. Exiting.")
        sys.exit(0)

    # Step 3: Parse funding entries
    logger.info("=== Step 3: Parsing funding entries ===")
    all_entries = []
    for article in scraped:
        entries = parse_article(article)
        all_entries.extend(entries)

    parsed_count = sum(1 for e in all_entries if e["parsed"])
    logger.info(
        "Total funding entries: %d (%d parsed, %d unparsed)",
        len(all_entries),
        parsed_count,
        len(all_entries) - parsed_count,
    )

    # Save fundings
    fundings_path = save_fundings(all_entries, fmt=args.output_format)
    print(f"\nFunding entries saved to: {fundings_path}")

    if not all_entries:
        logger.warning("No funding entries found. Exiting.")
        sys.exit(0)

    # Step 4: Job search (optional)
    jobs_df = pd.DataFrame()
    if not args.skip_jobs:
        companies = [e["company"] for e in all_entries if e["parsed"] and e["company"]]
        companies = list(dict.fromkeys(companies))  # deduplicate, preserve order

        if companies:
            logger.info("=== Step 4: Searching jobs for %d companies ===", len(companies))
            for c in companies:
                logger.info("  - %s", c)
            jobs_df = search_all_companies(companies)
        else:
            logger.warning("No company names extracted; skipping job search.")
    else:
        logger.info("=== Step 4: Skipping job search (--skip-jobs) ===")

    # Step 5: Save outputs
    logger.info("=== Step 5: Saving results ===")
    if not jobs_df.empty:
        jobs_path = save_jobs(jobs_df, fmt=args.output_format)
        print(f"Job listings saved to: {jobs_path}")

        combined_path = save_combined(all_entries, jobs_df, fmt=args.output_format)
        print(f"Combined output saved to: {combined_path}")
    else:
        if not args.skip_jobs:
            print("No matching jobs found.")

    # Summary
    print(f"\n--- Summary ---")
    print(f"Articles scraped: {len(scraped)}")
    print(f"Funding entries: {len(all_entries)} ({parsed_count} parsed)")
    if not args.skip_jobs:
        print(f"Job listings: {len(jobs_df)}")


if __name__ == "__main__":
    main()
