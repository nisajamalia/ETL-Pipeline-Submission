import logging
import os

from utils.extract import scrape_all_pages
from utils.transform import to_dataframe, transform
from utils.load import load_to_csv, load_to_google_sheets, load_to_postgresql

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_pipeline(
    total_pages: int = 50,
    csv_path: str = "products.csv",
    google_sheets_id: str | None = None,
    google_sheets_credentials: str = "google-sheets-api.json",
    postgres_url: str | None = None,
) -> None:
    """
    Run the complete ETL pipeline:
      1. Extract  – scrape fashion-studio.dicoding.dev
      2. Transform – clean and normalise data
      3. Load      – save to CSV (always), Google Sheets, and/or PostgreSQL
    """
    # ── EXTRACT ──────────────────────────────────────────────────────────────
    logger.info("=== EXTRACT STAGE ===")
    raw_products = scrape_all_pages(total_pages=total_pages)
    if not raw_products:
        logger.error("No products were scraped. Aborting pipeline.")
        return
    logger.info(f"Extracted {len(raw_products)} raw records.")

    # ── TRANSFORM ────────────────────────────────────────────────────────────
    logger.info("=== TRANSFORM STAGE ===")
    df_raw = to_dataframe(raw_products)
    df_clean = transform(df_raw)
    logger.info(f"Transformation complete. {len(df_clean)} clean records ready.")

    # ── LOAD ─────────────────────────────────────────────────────────────────
    logger.info("=== LOAD STAGE ===")

    # 1. Always save to CSV
    load_to_csv(df_clean, filepath=csv_path)

    # 2. Optionally save to Google Sheets
    if google_sheets_id:
        try:
            load_to_google_sheets(
                df_clean,
                spreadsheet_id=google_sheets_id,
                credentials_path=google_sheets_credentials,
            )
        except Exception as e:
            logger.warning(f"Google Sheets upload failed (skipping): {e}")

    # 3. Optionally save to PostgreSQL
    resolved_pg_url = postgres_url or os.environ.get("DB_URL")
    if resolved_pg_url:
        try:
            load_to_postgresql(df_clean, db_url=resolved_pg_url)
        except Exception as e:
            logger.warning(f"PostgreSQL upload failed (skipping): {e}")

    logger.info("=== ETL PIPELINE COMPLETE ===")


if __name__ == "__main__":
    # ── Configuration ─────────────────────────────────────────────────────
    # Fill in your Google Sheets spreadsheet ID and/or Postgres URL as needed.
    GOOGLE_SHEETS_ID = os.environ.get("GOOGLE_SHEETS_ID", None)
    POSTGRES_URL = os.environ.get("DB_URL", None)

    run_pipeline(
        total_pages=50,
        csv_path="products.csv",
        google_sheets_id=GOOGLE_SHEETS_ID,
        google_sheets_credentials="google-sheets-api.json",
        postgres_url=POSTGRES_URL,
    )
