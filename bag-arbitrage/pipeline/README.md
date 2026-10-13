# Bag Arbitrage pipeline

Python code behind [shuming-he.github.io/bag-arbitrage](https://shuming-he.github.io/bag-arbitrage/).
It collects official list prices for the same products in the US, Canada and China and writes the JSON file the page reads.

```
products.csv ──scrape.py──▶ raw/prices_<time>.csv ──build_dataset.py──▶ ../data/prices.json ──▶ web page
                                                                              │
                                                                       analysis.py (SciPy check)
```

| Step | File | What it does |
|---|---|---|
| Scrape | `scrape.py` | Fetches each product URL in `products.csv`, respects `robots.txt`, waits between requests, and logs every attempt with a status. |
| Parse | `parse.py` | Reads the price from schema.org JSON-LD, falling back to price meta tags. Handles `¥12,800`, `C$1,295.00` and decimal commas. |
| Clean + match | `build_dataset.py` | Keeps the latest successful price per product and market, drops wrong-currency redirects and incomplete products, writes `../data/prices.json`. |
| Test | `analysis.py` | Paired t-tests on log price ratios and an OLS regression with `scipy.stats`, to cross-check the JavaScript on the page. |

## Run it

```bash
pip install -r requirements.txt
python -m unittest discover tests      # parser tests
python scrape.py                       # needs product URLs in products.csv
python build_dataset.py
python analysis.py --fx-cny 7.10 --fx-cad 1.38 --tax-us 7 --tax-ca 13
```

## Status

- The page currently shows a **prototype sample** (`"dataset": "prototype-sample"` in `prices.json`), not scraped prices.
- `products.csv` lists the 47 products but the `url_us`, `url_ca` and `url_cn` columns are still empty, so `scrape.py` has not collected real prices yet.
- Some brand sites render prices with JavaScript or block automated requests. Those pages will show `no-price-found` or `http-403` in the raw log and need a headless browser.
- `analysis.py` reproduces the page's statistics on the current dataset (China vs US +5.0%, t = 4.12; Canada vs US +2.5%, t = 6.21; r = −0.59 at the default settings).
