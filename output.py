"""Save funding and job results to CSV/JSON files."""

import json
import logging
import os
from datetime import datetime

import pandas as pd

import config

logger = logging.getLogger(__name__)


def _ensure_data_dir():
    os.makedirs(config.DATA_DIR, exist_ok=True)


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def save_fundings(entries: list[dict], fmt: str = "csv") -> str:
    """Save funding entries to a file. Returns the output path."""
    _ensure_data_dir()
    ts = _timestamp()

    if fmt == "json":
        path = os.path.join(config.DATA_DIR, f"fundings_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, default=str)
    else:
        path = os.path.join(config.DATA_DIR, f"fundings_{ts}.csv")
        df = pd.DataFrame(entries)
        df.to_csv(path, index=False)

    logger.info("Saved %d funding entries to %s", len(entries), path)
    return path


def save_jobs(jobs_df: pd.DataFrame, fmt: str = "csv") -> str:
    """Save job results to a file. Returns the output path."""
    _ensure_data_dir()
    ts = _timestamp()

    if fmt == "json":
        path = os.path.join(config.DATA_DIR, f"jobs_{ts}.json")
        jobs_df.to_json(path, orient="records", indent=2)
    else:
        path = os.path.join(config.DATA_DIR, f"jobs_{ts}.csv")
        jobs_df.to_csv(path, index=False)

    logger.info("Saved %d job listings to %s", len(jobs_df), path)
    return path


def save_combined(entries: list[dict], jobs_df: pd.DataFrame, fmt: str = "csv") -> str:
    """Join funding data with job results and save. Returns the output path."""
    _ensure_data_dir()
    ts = _timestamp()

    fundings_df = pd.DataFrame(entries)

    if jobs_df.empty or fundings_df.empty:
        combined = fundings_df if jobs_df.empty else jobs_df
    else:
        # Only join parsed fundings that have a company name
        parsed = fundings_df[fundings_df["parsed"] == True][  # noqa: E712
            ["company", "amount", "round", "location", "description", "section", "source_url"]
        ].copy()

        if "searched_company" in jobs_df.columns:
            combined = jobs_df.merge(
                parsed,
                left_on="searched_company",
                right_on="company",
                how="left",
                suffixes=("", "_funding"),
            )
        else:
            combined = fundings_df

    if fmt == "json":
        path = os.path.join(config.DATA_DIR, f"combined_{ts}.json")
        combined.to_json(path, orient="records", indent=2, default_handler=str)
    else:
        path = os.path.join(config.DATA_DIR, f"combined_{ts}.csv")
        combined.to_csv(path, index=False)

    logger.info("Saved combined output (%d rows) to %s", len(combined), path)
    return path
