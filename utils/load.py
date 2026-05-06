import pandas as pd
import logging
import os

try:
    from sqlalchemy import create_engine
except ImportError:
    create_engine = None  # type: ignore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# 1. CSV

def load_to_csv(df: pd.DataFrame, filepath: str = "products.csv") -> None:
    """
    Save the DataFrame to a CSV file.
    Raises ValueError if the DataFrame is empty.
    Raises IOError if the file cannot be written.
    """
    if df is None or df.empty:
        raise ValueError("DataFrame is empty. Nothing to save to CSV.")
    try:
        df.to_csv(filepath, index=False)
        logger.info(f"Data saved to CSV: {filepath} ({len(df)} rows)")
    except OSError as e:
        logger.error(f"Failed to write CSV file '{filepath}': {e}")
        raise IOError(f"Could not write to '{filepath}': {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error saving CSV: {e}")
        raise



# 2. Google Sheets


def load_to_google_sheets(
    df: pd.DataFrame,
    spreadsheet_id: str,
    sheet_name: str = "Sheet1",
    credentials_path: str = "google-sheets-api.json",
) -> None:
    """
    Upload the DataFrame to a Google Sheets spreadsheet.

    Parameters
    ----------
    df               : cleaned DataFrame to upload
    spreadsheet_id   : the ID portion of the Google Sheets URL
    sheet_name       : target worksheet name (default 'Sheet1')
    credentials_path : path to the service-account JSON key file
    """
    if df is None or df.empty:
        raise ValueError("DataFrame is empty. Nothing to upload to Google Sheets.")

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Service account file not found: '{credentials_path}'")

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as e:
        logger.error("gspread or google-auth not installed. Run: pip install gspread google-auth")
        raise ImportError("Missing dependency for Google Sheets upload.") from e

    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
        client = gspread.authorize(creds)

        spreadsheet = client.open_by_key(spreadsheet_id)

        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            worksheet.clear()
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=len(df) + 1, cols=len(df.columns))

        data = [df.columns.tolist()] + df.astype(str).values.tolist()
        worksheet.update(data)

        logger.info(
            f"Data uploaded to Google Sheets (id={spreadsheet_id}, "
            f"sheet='{sheet_name}'): {len(df)} rows"
        )
    except gspread.exceptions.APIError as e:
        logger.error(f"Google Sheets API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error uploading to Google Sheets: {e}")
        raise


# 3. PostgreSQL

def load_to_postgresql(
    df: pd.DataFrame,
    table_name: str = "products",
    db_url: str | None = None,
    if_exists: str = "replace",
) -> None:
    """
    Write the DataFrame to a PostgreSQL table using SQLAlchemy.

    Parameters
    ----------
    df         : cleaned DataFrame to save
    table_name : target table name (default 'products')
    db_url     : SQLAlchemy connection string, e.g.
                 'postgresql+psycopg2://user:pass@host:5432/dbname'
                 Falls back to the DB_URL environment variable if None.
    if_exists  : 'replace' (default) | 'append' | 'fail'
    """
    if df is None or df.empty:
        raise ValueError("DataFrame is empty. Nothing to save to PostgreSQL.")

    resolved_url = db_url or os.environ.get("DB_URL")
    if not resolved_url:
        raise ValueError(
            "No database URL provided. Pass db_url= or set the DB_URL environment variable."
        )

    if create_engine is None:
        logger.error("sqlalchemy not installed. Run: pip install sqlalchemy psycopg2-binary")
        raise ImportError("Missing dependency for PostgreSQL upload.")

    try:
        engine = create_engine(resolved_url)
        df.to_sql(table_name, engine, if_exists=if_exists, index=False)
        logger.info(
            f"Data saved to PostgreSQL table '{table_name}' "
            f"(if_exists='{if_exists}'): {len(df)} rows"
        )
    except Exception as e:
        logger.error(f"Failed to save data to PostgreSQL: {e}")
        raise
