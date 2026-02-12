"""Flask web UI for the StrictlyVC funding scraper & NYC job finder."""

import logging
import threading

import pandas as pd
from flask import Flask, jsonify, render_template

import config
from job_search import search_all_companies
from output import save_combined, save_fundings, save_jobs
from parser import parse_article
from scraper import fetch_article_urls, scrape_articles

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Shared state for the background pipeline run
run_state = {
    "running": False,
    "status": "idle",
    "progress": "",
    "fundings": [],
    "jobs": [],
    "combined": [],
    "summary": {},
}
run_lock = threading.Lock()


def _run_pipeline():
    """Execute the full scraper pipeline in a background thread."""
    global run_state
    try:
        # Step 1: Fetch article URLs
        with run_lock:
            run_state["progress"] = "Fetching article URLs from sitemap..."
        articles = fetch_article_urls(days_back=30)
        if not articles:
            with run_lock:
                run_state.update(status="done", running=False, progress="No articles found.")
            return

        urls = [a["url"] for a in articles[:config.DEFAULT_MAX_ARTICLES]]

        # Step 2: Scrape articles
        with run_lock:
            run_state["progress"] = f"Scraping {len(urls)} article(s) with Playwright..."
        scraped = scrape_articles(urls)
        if not scraped:
            with run_lock:
                run_state.update(status="done", running=False, progress="No articles could be scraped.")
            return

        # Step 3: Parse funding entries
        with run_lock:
            run_state["progress"] = "Parsing funding entries..."
        all_entries = []
        for article in scraped:
            all_entries.extend(parse_article(article))

        parsed_count = sum(1 for e in all_entries if e["parsed"])
        save_fundings(all_entries, fmt="csv")

        # Step 4: Job search
        companies = [e["company"] for e in all_entries if e["parsed"] and e["company"]]
        companies = list(dict.fromkeys(companies))  # deduplicate
        jobs_df = pd.DataFrame()

        if companies:
            for i, company in enumerate(companies):
                with run_lock:
                    run_state["progress"] = (
                        f"Searching jobs for {company} ({i + 1}/{len(companies)})..."
                    )
                # search_all_companies does the delay internally,
                # but we want per-company progress, so we call one at a time
                from job_search import search_company_jobs
                import time

                df = search_company_jobs(company)
                if not df.empty:
                    jobs_df = pd.concat([jobs_df, df], ignore_index=True) if not jobs_df.empty else df
                if i < len(companies) - 1:
                    time.sleep(config.JOB_SEARCH_DELAY)

        # Step 5: Save outputs
        with run_lock:
            run_state["progress"] = "Saving results..."

        if not jobs_df.empty:
            save_jobs(jobs_df, fmt="csv")
            save_combined(all_entries, jobs_df, fmt="csv")

        # Prepare JSON-friendly data for the frontend
        fundings_display = [
            {k: v for k, v in e.items() if k != "raw_text"}
            for e in all_entries if e["parsed"]
        ]

        jobs_display = []
        if not jobs_df.empty:
            cols = ["title", "company", "location", "job_url", "date_posted",
                    "min_amount", "max_amount", "currency", "is_remote", "searched_company"]
            available = [c for c in cols if c in jobs_df.columns]
            jobs_display = jobs_df[available].fillna("").to_dict(orient="records")

        combined_display = []
        if not jobs_df.empty:
            fundings_df = pd.DataFrame(all_entries)
            parsed_df = fundings_df[fundings_df["parsed"] == True][
                ["company", "amount", "round", "section"]
            ].copy()
            if "searched_company" in jobs_df.columns:
                merged = jobs_df.merge(
                    parsed_df, left_on="searched_company", right_on="company",
                    how="inner", suffixes=("", "_funding"),
                )
                display_cols = ["title", "company", "location", "job_url",
                                "amount", "round", "section"]
                available = [c for c in display_cols if c in merged.columns]
                combined_display = merged[available].fillna("").to_dict(orient="records")

        with run_lock:
            run_state.update(
                status="done",
                running=False,
                progress="Complete!",
                fundings=fundings_display,
                jobs=jobs_display,
                combined=combined_display,
                summary={
                    "articles_scraped": len(scraped),
                    "funding_entries": len(all_entries),
                    "parsed": parsed_count,
                    "companies_searched": len(companies),
                    "jobs_found": len(jobs_df),
                },
            )

    except Exception:
        logger.exception("Pipeline failed")
        with run_lock:
            run_state.update(status="error", running=False, progress="Pipeline failed. Check logs.")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/run", methods=["POST"])
def api_run():
    with run_lock:
        if run_state["running"]:
            return jsonify({"error": "Pipeline already running"}), 409
        run_state.update(
            running=True,
            status="running",
            progress="Starting pipeline...",
            fundings=[],
            jobs=[],
            combined=[],
            summary={},
        )

    thread = threading.Thread(target=_run_pipeline, daemon=True)
    thread.start()
    return jsonify({"status": "started"})


@app.route("/api/status")
def api_status():
    with run_lock:
        return jsonify(run_state)


if __name__ == "__main__":
    app.run(debug=False, port=5000)
