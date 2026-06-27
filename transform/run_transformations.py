"""
run_transformations.py
----------------------
Runs the .sql files in the transform/ folder in name order (01_, 02_, ...)
against BigQuery. The ${PROJECT} / ${RAW} / ${ANALYTICS} placeholders in each
file are filled in from .env values.

Run:
    python transform/run_transformations.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from string import Template

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("transform")

PROJECT = os.getenv("GCP_PROJECT_ID")
RAW_DATASET = os.getenv("BQ_RAW_DATASET", "co2_raw")
ANALYTICS_DATASET = os.getenv("BQ_ANALYTICS_DATASET", "co2_analytics")
LOCATION = os.getenv("BQ_LOCATION", "US")

SQL_DIR = Path(__file__).resolve().parent


def ensure_analytics_dataset(client: bigquery.Client) -> None:
    """Create the analytics dataset if it doesn't exist (idempotent)."""
    dataset = bigquery.Dataset(f"{PROJECT}.{ANALYTICS_DATASET}")
    dataset.location = LOCATION
    client.create_dataset(dataset, exists_ok=True)
    log.info("Analytics dataset ready: %s.%s", PROJECT, ANALYTICS_DATASET)


def run() -> None:
    if not PROJECT:
        log.error("GCP_PROJECT_ID is not set. Fill in your .env (see .env.example).")
        sys.exit(1)

    client = bigquery.Client(project=PROJECT, location=LOCATION)
    ensure_analytics_dataset(client)

    sql_files = sorted(SQL_DIR.glob("*.sql"))
    if not sql_files:
        log.warning("No .sql files found in transform/.")
        return

    for sql_file in sql_files:
        raw_sql = sql_file.read_text(encoding="utf-8")
        sql = Template(raw_sql).safe_substitute(
            PROJECT=PROJECT,
            RAW=RAW_DATASET,
            ANALYTICS=ANALYTICS_DATASET,
        )
        log.info("Running → %s", sql_file.name)
        job = client.query(sql)
        job.result()  # wait for completion
        log.info("  ✅ %s done (%s bytes processed)", sql_file.name, f"{job.total_bytes_processed or 0:,}")

    log.info("All transformations complete.")


if __name__ == "__main__":
    run()
