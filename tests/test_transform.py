import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pandas as pd

from utils.transform import (
    to_dataframe,
    clean_price,
    clean_rating,
    clean_colors,
    clean_size,
    clean_gender,
    transform,
    EXCHANGE_RATE,
)


# ─── Helpers ────────────────────────────────────────────────────────────────

def sample_products(n: int = 3) -> list[dict]:
    base = {
        "Title": "Awesome Jacket",
        "Price": "$29.99",
        "Rating": "4.5 / 5",
        "Colors": "3 Colors",
        "Size": "Size: M",
        "Gender": "Gender: Men",
        "timestamp": "2025-01-01T00:00:00",
    }
    return [{**base, "Title": f"Product {i}"} for i in range(n)]


def sample_df(n: int = 3) -> pd.DataFrame:
    return pd.DataFrame(sample_products(n))


# ─── to_dataframe ────────────────────────────────────────────────────────────

class TestToDataframe:
    def test_converts_list_to_dataframe(self):
        products = sample_products(5)
        df = to_dataframe(products)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5

    def test_raises_on_empty_list(self):
        with pytest.raises(ValueError):
            to_dataframe([])

    def test_columns_match_keys(self):
        products = sample_products(2)
        df = to_dataframe(products)
        for key in products[0]:
            assert key in df.columns


# ─── clean_price ────────────────────────────────────────────────────────────

class TestCleanPrice:
    def test_strips_dollar_sign(self):
        assert clean_price("$29.99") == pytest.approx(29.99)

    def test_handles_plain_float_string(self):
        assert clean_price("15.00") == pytest.approx(15.00)

    def test_returns_none_for_nan(self):
        assert clean_price(float("nan")) is None

    def test_returns_none_for_non_numeric(self):
        assert clean_price("N/A") is None

    def test_handles_comma_in_price(self):
        assert clean_price("$1,000.00") == pytest.approx(1000.00)

    def test_returns_none_for_none(self):
        assert clean_price(None) is None


# ─── clean_rating ────────────────────────────────────────────────────────────

class TestCleanRating:
    def test_parses_slash_format(self):
        assert clean_rating("4.8 / 5") == pytest.approx(4.8)

    def test_parses_plain_float(self):
        assert clean_rating("3.5") == pytest.approx(3.5)

    def test_returns_none_for_invalid_rating_string(self):
        assert clean_rating("Invalid Rating") is None

    def test_returns_none_for_nan(self):
        assert clean_rating(float("nan")) is None

    def test_returns_none_for_out_of_range(self):
        assert clean_rating("6.0") is None
        assert clean_rating("-1.0") is None

    def test_returns_none_for_none(self):
        assert clean_rating(None) is None

    def test_zero_is_valid(self):
        assert clean_rating("0.0") == pytest.approx(0.0)

    def test_five_is_valid(self):
        assert clean_rating("5.0") == pytest.approx(5.0)


# ─── clean_colors ────────────────────────────────────────────────────────────

class TestCleanColors:
    def test_extracts_number_from_string(self):
        assert clean_colors("3 Colors") == 3

    def test_handles_single_digit(self):
        assert clean_colors("1 Color") == 1

    def test_returns_none_for_no_digits(self):
        assert clean_colors("No Colors") is None

    def test_returns_none_for_nan(self):
        assert clean_colors(float("nan")) is None

    def test_returns_none_for_none(self):
        assert clean_colors(None) is None

    def test_handles_number_only_string(self):
        assert clean_colors("5") == 5


# ─── clean_size ──────────────────────────────────────────────────────────────

class TestCleanSize:
    def test_strips_size_prefix(self):
        assert clean_size("Size: M") == "M"

    def test_strips_size_prefix_no_space(self):
        assert clean_size("Size:XL") == "XL"

    def test_returns_none_for_nan(self):
        assert clean_size(float("nan")) is None

    def test_returns_none_for_none(self):
        assert clean_size(None) is None

    def test_handles_multi_word_size(self):
        assert clean_size("Size: One Size") == "One Size"


# ─── clean_gender ────────────────────────────────────────────────────────────

class TestCleanGender:
    def test_strips_gender_prefix(self):
        assert clean_gender("Gender: Men") == "Men"

    def test_strips_gender_prefix_no_space(self):
        assert clean_gender("Gender:Women") == "Women"

    def test_returns_none_for_nan(self):
        assert clean_gender(float("nan")) is None

    def test_returns_none_for_none(self):
        assert clean_gender(None) is None

    def test_unisex_gender(self):
        assert clean_gender("Gender: Unisex") == "Unisex"


# ─── transform ───────────────────────────────────────────────────────────────

class TestTransform:
    def test_raises_on_empty_dataframe(self):
        with pytest.raises(ValueError):
            transform(pd.DataFrame())

    def test_price_converted_to_idr(self):
        df = sample_df(2)
        result = transform(df)
        for price in result["Price"]:
            assert price == pytest.approx(29.99 * EXCHANGE_RATE)

    def test_removes_unknown_product_titles(self):
        products = sample_products(2)
        products.append({
            "Title": "Unknown Product",
            "Price": "$10.00",
            "Rating": "4.0 / 5",
            "Colors": "2 Colors",
            "Size": "Size: S",
            "Gender": "Gender: Women",
            "timestamp": "2025-01-01T00:00:00",
        })
        df = transform(pd.DataFrame(products))
        assert "Unknown Product" not in df["Title"].values

    def test_removes_null_rows(self):
        products = sample_products(3)
        products.append({
            "Title": None,
            "Price": None,
            "Rating": None,
            "Colors": None,
            "Size": None,
            "Gender": None,
            "timestamp": "2025-01-01T00:00:00",
        })
        df = transform(pd.DataFrame(products))
        assert df["Title"].isna().sum() == 0

    def test_removes_duplicates(self):
        products = sample_products(2)
        products = products + products  
        df = transform(pd.DataFrame(products))
        assert len(df) == 2

    def test_rating_column_is_float(self):
        df = transform(sample_df())
        assert df["Rating"].dtype == float

    def test_colors_column_is_int(self):
        df = transform(sample_df())
        assert df["Colors"].dtype == int

    def test_size_column_has_no_prefix(self):
        df = transform(sample_df())
        assert not df["Size"].str.contains("Size:").any()

    def test_gender_column_has_no_prefix(self):
        df = transform(sample_df())
        assert not df["Gender"].str.contains("Gender:").any()

    def test_result_has_no_nulls_in_key_columns(self):
        df = transform(sample_df())
        for col in ["Title", "Price", "Rating", "Colors", "Size", "Gender"]:
            assert df[col].isna().sum() == 0

    def test_invalid_rating_rows_dropped(self):
        products = sample_products(2)
        products.append({
            "Title": "Bad Rating Product",
            "Price": "$15.00",
            "Rating": "Invalid Rating",
            "Colors": "2 Colors",
            "Size": "Size: L",
            "Gender": "Gender: Men",
            "timestamp": "2025-01-01T00:00:00",
        })
        df = transform(pd.DataFrame(products))
        assert "Bad Rating Product" not in df["Title"].values

    def test_timestamp_column_preserved(self):
        df = transform(sample_df())
        assert "timestamp" in df.columns

    def test_index_is_reset(self):
        df = transform(sample_df(5))
        assert list(df.index) == list(range(len(df)))
