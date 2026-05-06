# Fashion Studio ETL Pipeline

ETL pipeline untuk mengekstrak data produk fashion dari fashion-studio.dicoding.dev

## Fitur
- Extract: scraping 50 halaman (~1000 produk)
- Transform: cleaning, konversi USD ke IDR, validasi data
- Load: CSV, Google Sheets, PostgreSQL

## Cara Menjalankan
pip install -r requirements.txt
python main.py

## Menjalankan Tests
pytest tests/ --cov=utils --cov-report=term-missing
