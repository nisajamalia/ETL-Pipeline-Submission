import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from utils.extract import get_page, parse_product, scrape_page, scrape_all_pages



def make_card_html(
    title="Cool T-Shirt",
    price="$29.99",
    rating="4.5 / 5",
    colors="3 Colors",
    size="Size: M",
    gender="Gender: Men",
):
    """Build a minimal product-card HTML snippet."""
    return f"""
    <div class="product-details">
        <h3 class="product-title">{title}</h3>
        <span class="price">{price}</span>
        <p>Rating: {rating}</p>
        <p>{colors}</p>
        <p>{size}</p>
        <p>{gender}</p>
    </div>
    """


def make_soup(cards_html: str) -> BeautifulSoup:
    return BeautifulSoup(f"<html><body>{cards_html}</body></html>", "html.parser")


# ─── get_page ───────────────────────────────────────────────────────────────

class TestGetPage:
    @patch("utils.extract.requests.get")
    def test_returns_soup_on_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body><p>Hello</p></body></html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_page("https://fashion-studio.dicoding.dev")
        assert result is not None
        assert result.find("p").get_text() == "Hello"

    @patch("utils.extract.requests.get")
    def test_returns_none_after_all_retries_fail(self, mock_get):
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.ConnectionError("down")

        result = get_page("https://fashion-studio.dicoding.dev", retries=2, delay=0)
        assert result is None

    @patch("utils.extract.requests.get")
    def test_retries_on_timeout(self, mock_get):
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.Timeout("timed out")

        result = get_page("https://example.com", retries=3, delay=0)
        assert result is None
        assert mock_get.call_count == 3

    @patch("utils.extract.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        import requests as req_lib
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req_lib.exceptions.HTTPError("404")
        mock_get.return_value = mock_resp

        result = get_page("https://example.com", retries=1, delay=0)
        assert result is None

    @patch("utils.extract.requests.get")
    def test_retries_succeed_on_second_attempt(self, mock_get):
        import requests as req_lib
        good_resp = MagicMock()
        good_resp.text = "<html><body></body></html>"
        good_resp.raise_for_status = MagicMock()
        mock_get.side_effect = [req_lib.exceptions.ConnectionError("err"), good_resp]

        result = get_page("https://example.com", retries=3, delay=0)
        assert result is not None
        assert mock_get.call_count == 2



class TestParseProduct:
    def _card(self, **kwargs):
        soup = make_soup(make_card_html(**kwargs))
        return soup.find("div", class_="product-details")

    def test_parses_full_valid_card(self):
        card = self._card()
        result = parse_product(card)
        assert result is not None
        assert result["Title"] == "Cool T-Shirt"
        assert result["Price"] == "$29.99"
        assert result["Rating"] == "4.5 / 5"
        assert result["Colors"] == "3 Colors"
        assert result["Size"] == "Size: M"
        assert result["Gender"] == "Gender: Men"
        assert "timestamp" in result

    def test_returns_none_when_title_missing(self):
        html = """
        <div class="product-details">
            <span class="price">$10.00</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        card = soup.find("div", class_="product-details")
        assert parse_product(card) is None

    def test_returns_none_when_price_missing(self):
        html = """
        <div class="product-details">
            <h3 class="product-title">Jacket</h3>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        card = soup.find("div", class_="product-details")
        assert parse_product(card) is None

    def test_timestamp_is_string(self):
        card = self._card()
        result = parse_product(card)
        assert isinstance(result["timestamp"], str)

    def test_optional_fields_are_none_when_absent(self):
        html = """
        <div class="product-details">
            <h3 class="product-title">Shirt</h3>
            <span class="price">$15.00</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        card = soup.find("div", class_="product-details")
        result = parse_product(card)
        assert result is not None
        assert result["Rating"] is None
        assert result["Colors"] is None


# ─── scrape_page ─────────────────────────────────────────────────────────────

class TestScrapePage:
    @patch("utils.extract.get_page")
    def test_returns_products_for_page_1(self, mock_get_page):
        html = make_card_html() * 2
        mock_get_page.return_value = make_soup(html)

        result = scrape_page(1)
        assert len(result) == 2

    @patch("utils.extract.get_page")
    def test_returns_empty_list_when_no_cards(self, mock_get_page):
        mock_get_page.return_value = make_soup("<div></div>")
        result = scrape_page(1)
        assert result == []

    @patch("utils.extract.get_page")
    def test_returns_empty_list_when_page_fetch_fails(self, mock_get_page):
        mock_get_page.return_value = None
        result = scrape_page(3)
        assert result == []

    def test_raises_on_invalid_page_number(self):
        with pytest.raises(ValueError):
            scrape_page(0)

    @patch("utils.extract.get_page")
    def test_uses_correct_url_for_page_1(self, mock_get_page):
        mock_get_page.return_value = make_soup("")
        scrape_page(1)
        called_url = mock_get_page.call_args[0][0]
        assert "page" not in called_url

    @patch("utils.extract.get_page")
    def test_uses_page_url_for_page_gt_1(self, mock_get_page):
        mock_get_page.return_value = make_soup("")
        scrape_page(5)
        called_url = mock_get_page.call_args[0][0]
        assert "page5" in called_url



class TestScrapeAllPages:
    @patch("utils.extract.scrape_page")
    def test_aggregates_products_across_pages(self, mock_scrape):
        mock_scrape.return_value = [{"Title": "X", "Price": "$1.00"}]
        result = scrape_all_pages(total_pages=3)
        assert len(result) == 3
        assert mock_scrape.call_count == 3

    @patch("utils.extract.scrape_page")
    def test_returns_empty_when_all_pages_empty(self, mock_scrape):
        mock_scrape.return_value = []
        result = scrape_all_pages(total_pages=5)
        assert result == []

    def test_raises_on_invalid_total_pages(self):
        with pytest.raises(ValueError):
            scrape_all_pages(total_pages=0)

    @patch("utils.extract.scrape_page")
    def test_continues_on_page_exception(self, mock_scrape):
        mock_scrape.side_effect = [
            Exception("boom"),
            [{"Title": "OK", "Price": "$5.00"}],
            [{"Title": "OK2", "Price": "$6.00"}],
        ]
        result = scrape_all_pages(total_pages=3)
        assert len(result) == 2

    @patch("utils.extract.scrape_page")
    def test_scrapes_correct_number_of_pages(self, mock_scrape):
        mock_scrape.return_value = []
        scrape_all_pages(total_pages=10)
        assert mock_scrape.call_count == 10
