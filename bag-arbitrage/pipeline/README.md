# Bag Arbitrage pipeline

Python code behind [shuming-he.github.io/bag-arbitrage](https://shuming-he.github.io/bag-arbitrage/).
It collects official list prices for the same products in the US and Canada and writes the JSON file the page reads.

```
collected_prices.csv ─┐
                      ├─build_dataset.py──▶ ../data/prices.json ──▶ web page
products.csv ─scrape.py─▶ raw/prices_<time>.csv ─┘         │
                                                    analysis.py (SciPy check)
```

| Step | File | What it does |
|---|---|---|
| Collect | `collected_prices.csv` | One row per product per market: list price, currency, style number, source URL and date, read from each brand's official site. A note marks prices read from a category listing or items shown as sold out. |
| Scrape | `scrape.py` | Fetches each URL in `products.csv`, respects `robots.txt`, waits between requests, and logs every attempt with a status. Works for pages that publish structured price data. |
| Parse | `parse.py` | Reads the price from schema.org JSON-LD, falling back to price meta tags. Handles `$5,100`, `C$1,295.00` and decimal commas. |
| Clean + match | `build_dataset.py` | Keeps the latest price per product and market, drops wrong-currency redirects and products missing either market, writes `../data/prices.json` with source URLs. |
| Test | `analysis.py` | Paired t-test on log price ratios, the implied CAD/USD rate, and an OLS regression with `scipy.stats`, to cross-check the JavaScript on the page. |

## Run it

```bash
pip install -r requirements.txt
python -m unittest discover tests      # parser tests
python build_dataset.py                # from collected_prices.csv
python analysis.py --fx-cad 1.42 --tax-us 7 --tax-ca 13
```

## Status (13 October 2026)

- 153 products from 15 brands (about 10 per brand) have official prices in both markets.
- Results at the defaults (USD/CAD 1.42, 7% US tax, 13% HST): Canada vs US −4.5% (95% CI −5.1% to −3.9%), t = −13.70, p < 0.001. Brands price Canada at about C$1.28 per US$1. The gap is not related to price tier (r = 0.03, p = 0.7).
- Some prices were read from category listing pages; the `note` column says which. Six Coach items were matched across markets by product name because Coach's Canadian product pages hide prices.
