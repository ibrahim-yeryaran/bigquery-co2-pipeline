"""
run_transformations.py
----------------------
transform/ klasöründeki .sql dosyalarını ad sırasına göre (01_, 02_, ...)
BigQuery'de çalıştırır. Her dosyadaki ${PROJECT} / ${RAW} / ${ANALYTICS}
yer tutucuları .env değerleriyle doldurulur.

Çalıştırma:
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
    """Analytics dataset'i yoksa oluşturur (idempotent)."""
    dataset = bigquery.Dataset(f"{PROJECT}.{ANALYTICS_DATASET}")
    dataset.location = LOCATION
    client.create_dataset(dataset, exists_ok=True)
    log.info("Analytics dataset hazır: %s.%s", PROJECT, ANALYTICS_DATASET)


def run() -> None:
    if not PROJECT:
        log.error("GCP_PROJECT_ID tanımlı değil. .env dosyanı doldur (bkz. .env.example).")
        sys.exit(1)

    client = bigquery.Client(project=PROJECT, location=LOCATION)
    ensure_analytics_dataset(client)

    sql_files = sorted(SQL_DIR.glob("*.sql"))
    if not sql_files:
        log.warning("transform/ içinde .sql dosyası yok.")
        return

    for sql_file in sql_files:
        raw_sql = sql_file.read_text(encoding="utf-8")
        sql = Template(raw_sql).safe_substitute(
            PROJECT=PROJECT,
            RAW=RAW_DATASET,
            ANALYTICS=ANALYTICS_DATASET,
        )
        log.info("Çalıştırılıyor → %s", sql_file.name)
        job = client.query(sql)
        job.result()  # bitmesini bekle
        log.info("  ✅ %s tamam (%s işlenen byte)", sql_file.name, f"{job.total_bytes_processed or 0:,}")

    log.info("Tüm dönüşümler tamamlandı.")


if __name__ == "__main__":
    run()
