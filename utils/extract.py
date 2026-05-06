import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://fashion-studio.dicoding.dev"


def get_page(url: str, retries: int = 3, delay: float = 1.0):
    """
    Fetch a single page and return a BeautifulSoup object.
    Retries up to `retries` times on failure.
    """
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error on attempt {attempt} for {url}: {e}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error on attempt {attempt} for {url}: {e}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout on attempt {attempt} for {url}: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error on attempt {attempt} for {url}: {e}")
        if attempt < retries:
            time.sleep(delay)
    logger.error(f"All {retries} attempts failed for {url}")
    return None


def parse_product(card) -> dict | None:
    """
    Parse a single collection-card element into a dict.
    HTML structure:
      <div class="collection-card">
        <div class="product-details">
          <h3 class="product-title">...</h3>
          <span class="price">$xx.xx</span>
          <p>Rating: ⭐ 4.5 / 5</p>
          <p>3 Colors</p>
          <p>Size: M</p>
          <p>Gender: Men</p>
        </div>
      </div>
    """
    try:
        # Title
        title_tag = card.find("h3", class_="product-title")
        title = title_tag.get_text(strip=True) if title_tag else None

        # Price
        price_tag = card.find("span", class_="price")
        price = price_tag.get_text(strip=True) if price_tag else None

        # All <p> tags inside product-details
        details = card.find("div", class_="product-details")
        paragraphs = details.find_all("p") if details else card.find_all("p")

        rating = None
        colors = None
        size = None
        gender = None

        for p in paragraphs:
            text = p.get_text(strip=True)
            if text.lower().startswith("rating"):
                rating = re.sub(r"(?i)^rating\s*:?\s*", "", text).strip()
            elif "color" in text.lower():
                colors = text
            elif text.lower().startswith("size"):
                size = text
            elif text.lower().startswith("gender"):
                gender = text

        if not title or not price:
            return None

        return {
            "Title": title,
            "Price": price,
            "Rating": rating,
            "Colors": colors,
            "Size": size,
            "Gender": gender,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error parsing product card: {e}")
        return None


def scrape_page(page_number: int) -> list[dict]:
    """
    Scrape all products from a single page number.
    """
    if page_number < 1:
        raise ValueError(f"Page number must be >= 1, got {page_number}")

    url = BASE_URL if page_number == 1 else f"{BASE_URL}/page{page_number}"

    soup = get_page(url)
    if soup is None:
        logger.warning(f"Could not retrieve page {page_number}")
        return []

    try:
        cards = soup.find_all("div", class_="collection-card")
        if not cards:
            # Fallback: some test stubs / page structures wrap product-details directly
            cards = soup.find_all("div", class_="product-details")
        if not cards:
            logger.warning(f"No product cards found on page {page_number}")
            return []

        products = []
        for card in cards:
            product = parse_product(card)
            if product:
                products.append(product)

        logger.info(f"Page {page_number}: scraped {len(products)} products")
        return products
    except Exception as e:
        logger.error(f"Error processing page {page_number}: {e}")
        return []


def scrape_all_pages(total_pages: int = 50) -> list[dict]:
    """
    Scrape products from all pages (1 to total_pages inclusive).
    Returns a flat list of all product dicts.
    """
    if total_pages < 1:
        raise ValueError(f"total_pages must be >= 1, got {total_pages}")

    all_products = []
    for page in range(1, total_pages + 1):
        try:
            products = scrape_page(page)
            all_products.extend(products)
            time.sleep(0.3)
        except Exception as e:
            logger.error(f"Unexpected error on page {page}: {e}")
            continue

    logger.info(f"Total products scraped: {len(all_products)}")
    return all_products
