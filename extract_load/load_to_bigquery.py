"""
load_to_bigquery.py
-------------------
ELT'in "EL" kısmı: OWID CO₂ CSV'sini indirir ve BigQuery'deki
`<proje>.co2_raw.owid_co2` tablosuna yükler. Dönüşümler (T) BigQuery
SQL'inde yapılır.

Kimlik doğrulama:
  A) gcloud auth application-default login   (anahtar dosyası yok, önerilen)
  B) GOOGLE_APPLICATION_CREDENTIALS=<service-account.json>

Çalıştırma:
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

load_dotenv()  # proje kökündeki .env'i ortam değişkenlerine yükler

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("load_bq")

# ── Ayarlar ───────────────────────────────────────────────────────────────────
CSV_URL = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LOCAL_CSV = DATA_DIR / "owid-co2-data.csv"

PROJECT = os.getenv("GCP_PROJECT_ID")
RAW_DATASET = os.getenv("BQ_RAW_DATASET", "co2_raw")
LOCATION = os.getenv("BQ_LOCATION", "US")
TABLE = "owid_co2"


def download_csv() -> Path:
    """CSV'yi indirir (zaten varsa yeniden indirmez)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if LOCAL_CSV.exists():
        log.info("CSV zaten mevcut: %s", LOCAL_CSV)
        return LOCAL_CSV

    log.info("CSV indiriliyor: %s", CSV_URL)
    resp = requests.get(CSV_URL, timeout=60)
    resp.raise_for_status()
    LOCAL_CSV.write_bytes(resp.content)
    log.info("İndirildi → %s (%.1f MB)", LOCAL_CSV, len(resp.content) / 1e6)
    return LOCAL_CSV


def ensure_dataset(client: bigquery.Client) -> None:
    """Raw dataset'i yoksa oluşturur (idempotent)."""
    dataset_id = f"{PROJECT}.{RAW_DATASET}"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = LOCATION
    client.create_dataset(dataset, exists_ok=True)
    log.info("Dataset hazır: %s (%s)", dataset_id, LOCATION)


def load_csv(client: bigquery.Client, csv_path: Path) -> None:
    """CSV'yi BigQuery tablosuna yükler. WRITE_TRUNCATE → idempotent."""
    table_id = f"{PROJECT}.{RAW_DATASET}.{TABLE}"
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,                 # header satırını atla
        autodetect=True,                     # şemayı CSV'den çıkar
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        allow_quoted_newlines=True,
    )

    log.info("Yükleniyor → %s", table_id)
    with csv_path.open("rb") as fh:
        job = client.load_table_from_file(fh, table_id, job_config=job_config)
    job.result()  # işin bitmesini bekle

    table = client.get_table(table_id)
    log.info("✅ Yüklendi → %s satır, %s kolon", f"{table.num_rows:,}", len(table.schema))


def run() -> None:
    if not PROJECT:
        log.error("GCP_PROJECT_ID tanımlı değil. .env dosyanı doldur (bkz. .env.example).")
        sys.exit(1)

    csv_path = download_csv()
    client = bigquery.Client(project=PROJECT, location=LOCATION)
    ensure_dataset(client)
    load_csv(client, csv_path)
    log.info("Ham yükleme tamamlandı.")


if __name__ == "__main__":
    run()
