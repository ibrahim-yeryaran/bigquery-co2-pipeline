"""
load_to_bigquery.py
-------------------
The "EL" part of ELT: downloads the OWID CO₂ CSV and loads it into the
BigQuery table `<project>.co2_raw.owid_co2`. Transformations (T) are done
in BigQuery SQL.

Authentication:
  A) gcloud auth application-default login   (no key file, recommended)
  B) GOOGLE_APPLICATION_CREDENTIALS=<service-account.json>

Run:
    python extract_load/load_to_bigquery.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()  # load .env from the project root into environment variables

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("load_bq")

# ── Settings ──────────────────────────────────────────────────────────────────
CSV_URL = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LOCAL_CSV = DATA_DIR / "owid-co2-data.csv"

PROJECT = os.getenv("GCP_PROJECT_ID")
RAW_DATASET = os.getenv("BQ_RAW_DATASET", "co2_raw")
LOCATION = os.getenv("BQ_LOCATION", "US")
TABLE = "owid_co2"


def download_csv() -> Path:
    """Download the CSV (skips download if it already exists)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if LOCAL_CSV.exists():
        log.info("CSV already present: %s", LOCAL_CSV)
        return LOCAL_CSV

    log.info("Downloading CSV: %s", CSV_URL)
    resp = requests.get(CSV_URL, timeout=60)
    resp.raise_for_status()
    LOCAL_CSV.write_bytes(resp.content)
    log.info("Downloaded → %s (%.1f MB)", LOCAL_CSV, len(resp.content) / 1e6)
    return LOCAL_CSV


def ensure_dataset(client: bigquery.Client) -> None:
    """Create the raw dataset if it doesn't exist (idempotent)."""
    dataset_id = f"{PROJECT}.{RAW_DATASET}"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = LOCATION
    client.create_dataset(dataset, exists_ok=True)
    log.info("Dataset ready: %s (%s)", dataset_id, LOCATION)


def load_csv(client: bigquery.Client, csv_path: Path) -> None:
    """Load the CSV into the BigQuery table. WRITE_TRUNCATE → idempotent."""
    table_id = f"{PROJECT}.{RAW_DATASET}.{TABLE}"
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,                 # skip the header row
        autodetect=True,                     # infer the schema from the CSV
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        allow_quoted_newlines=True,
    )

    log.info("Loading → %s", table_id)
    with csv_path.open("rb") as fh:
        job = client.load_table_from_file(fh, table_id, job_config=job_config)
    job.result()  # wait for the job to finish

    table = client.get_table(table_id)
    log.info("✅ Loaded → %s rows, %s columns", f"{table.num_rows:,}", len(table.schema))


def run() -> None:
    if not PROJECT:
        log.error("GCP_PROJECT_ID is not set. Fill in your .env (see .env.example).")
        sys.exit(1)

    csv_path = download_csv()
    client = bigquery.Client(project=PROJECT, location=LOCATION)
    ensure_dataset(client)
    load_csv(client, csv_path)
    log.info("Raw load complete.")


if __name__ == "__main__":
    run()
