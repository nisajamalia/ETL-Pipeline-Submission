import pandas as pd
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

EXCHANGE_RATE = 16000  


def to_dataframe(products: list[dict]) -> pd.DataFrame:
    """Convert a list of product dicts to a pandas DataFrame."""
    if not products:
        raise ValueError("Product list is empty. Nothing to convert.")
    try:
        df = pd.DataFrame(products)
        logger.info(f"DataFrame created with {len(df)} rows and {len(df.columns)} columns.")
        return df
    except Exception as e:
        logger.error(f"Failed to create DataFrame: {e}")
        raise


def clean_price(price_str) -> float | None:
    """Parse '$29.99' → 29.99 (float USD). Returns None on failure."""
    try:
        if pd.isna(price_str):
            return None
        cleaned = re.sub(r"[^\d.]", "", str(price_str))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def clean_rating(rating_str) -> float | None:
    """
    Parse rating strings like:
      'Rating: ⭐ 4.5 / 5'  → 4.5
      '4.8 / 5'             → 4.8
      'Invalid Rating / 5'  → None
    Returns None for invalid/out-of-range ratings.
    """
    try:
        if pd.isna(rating_str):
            return None
        text = str(rating_str)
        # Strip 'Rating:' prefix and emoji characters
        text = re.sub(r"(?i)rating\s*:?\s*", "", text)
        text = re.sub(r"[^\d./-]", " ", text).strip()
        # Take the part before '/'
        if "/" in text:
            text = text.split("/")[0].strip()
        text = text.strip()
        if not text:
            return None
        value = float(text)
        if value < 0 or value > 5:
            return None
        return value
    except (ValueError, TypeError):
        return None


def clean_colors(colors_str) -> int | None:
    """Extract numeric count from '3 Colors' → 3. Returns None on failure."""
    try:
        if pd.isna(colors_str):
            return None
        match = re.search(r"\d+", str(colors_str))
        return int(match.group()) if match else None
    except Exception:
        return None


def clean_size(size_str) -> str | None:
    """Strip 'Size:' prefix → 'M'. Returns None if null."""
    try:
        if pd.isna(size_str):
            return None
        return re.sub(r"(?i)^size\s*:?\s*", "", str(size_str)).strip()
    except Exception:
        return None


def clean_gender(gender_str) -> str | None:
    """Strip 'Gender:' prefix → 'Men'. Returns None if null."""
    try:
        if pd.isna(gender_str):
            return None
        return re.sub(r"(?i)^gender\s*:?\s*", "", str(gender_str)).strip()
    except Exception:
        return None


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all transformation steps:
    1. Remove invalid titles (Unknown Product, empty)
    2. Clean and parse each column
    3. Drop rows with nulls in key columns
    4. Convert Price USD → IDR
    5. Enforce correct data types
    6. Remove duplicates
    7. Reset index
    """
    if df.empty:
        raise ValueError("Input DataFrame is empty. Cannot transform.")

    try:
        logger.info(f"Starting transformation. Initial row count: {len(df)}")

        # 1. Remove invalid titles
        df = df[df["Title"].notna()]
        df = df[~df["Title"].str.strip().str.lower().isin(["unknown product", ""])]
        logger.info(f"After removing invalid titles: {len(df)} rows")

        # 2. Clean columns
        df = df.copy()
        df["Price"] = df["Price"].apply(clean_price)
        df["Rating"] = df["Rating"].apply(clean_rating)
        df["Colors"] = df["Colors"].apply(clean_colors)
        df["Size"] = df["Size"].apply(clean_size)
        df["Gender"] = df["Gender"].apply(clean_gender)

        # 3. Drop nulls in key columns
        key_cols = ["Title", "Price", "Rating", "Colors", "Size", "Gender"]
        df = df.dropna(subset=key_cols)
        logger.info(f"After dropping nulls in key columns: {len(df)} rows")

        # 4. Convert Price USD → IDR
        df["Price"] = (df["Price"] * EXCHANGE_RATE).round(2)

        # 5. Enforce data types
        df["Price"] = df["Price"].astype(float)
        df["Rating"] = df["Rating"].astype(float)
        df["Colors"] = df["Colors"].astype(int)
        df["Size"] = df["Size"].astype(str)
        df["Gender"] = df["Gender"].astype(str)
        df["Title"] = df["Title"].astype(str)

        # 6. Remove duplicates
        df = df.drop_duplicates()
        logger.info(f"After removing duplicates: {len(df)} rows")

        # 7. Reset index
        df = df.reset_index(drop=True)
        logger.info(f"Transformation complete. Final row count: {len(df)}")
        return df

    except Exception as e:
        logger.error(f"Transformation failed: {e}")
        raise
