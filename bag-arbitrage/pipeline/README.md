# Cross-Border Luxury Pricing: pipeline

Code behind [shuming-he.github.io/bag-arbitrage](https://shuming-he.github.io/bag-arbitrage/). It compares official list prices for the same products on brands' US and Canadian websites.

## Reproduce everything

```bash
pip install -r requirements.txt
python -m unittest discover tests     # 26 tests (statistics on synthetic data, validation, parser)
python run_analysis.py                # validation -> dataset -> analysis -> tables, figures, results.json, report
```

`run_analysis.py` is deterministic. The bootstrap uses seed 20261013, and the wild bootstrap enumerates every sign pattern, so re-running it reproduces `../data/results.json` byte for byte.

## Files

| File | Role |
|---|---|
| `collected_prices.csv` | Raw price log: one row per product per market, with price, currency, source URL, date and a provenance note |
| `products.csv` | Product list: brand, tier, category, style code, URLs, photo URL |
| `review_flags.csv` | Manual notes on identifiers that need checking |
| `fx_rates.csv` | Bank of Canada daily FXUSDCAD rates, 28 Sep to 9 Oct 2026 |
| `validate.py` | Format checks, matching flags and exclusions; writes `../data/matched_pairs.csv` and `../reports/data_quality.md` |
| `build_dataset.py` | Writes `../data/prices.json` for the web page |
| `bastats.py` | Estimators: paired t, brand-clustered (CR1) mean, brand-equal mean, cluster bootstrap, wild cluster bootstrap-t, Wilcoxon, leave-one-brand-out, clustered OLS |
| `run_analysis.py` | The single command: primary estimate, robustness checks, subsets, scenarios, regressions |
| `figures.py` | SVG figures in `../figures/` |
| `make_report.py` | Renders `../reports/report.md` (and `report.html` with pandoc) from `results.json` |
| `archive_sources.py`, `archived_sources.csv` | Requests Internet Archive copies of every source URL (run by the "Archive source pages" GitHub Action) and lists each snapshot or why none was made |
| `scrape.py`, `parse.py` | Optional scraper for pages with structured price data (`tests/test_parse.py`) |
| `analysis.py` | Earlier SciPy cross-check of the page under i.i.d. assumptions; superseded by `run_analysis.py` |
| `tests/site_consistency.js` | Checks that the page's JavaScript reproduces `results.json` (needs Playwright and a local server) |

## Primary estimand

d_i = ln(P_CA / (P_US × X)) uses list prices before tax. X is the Bank of Canada CAD-per-USD rate for the last business day before collection (2026-10-09, 1.4271). The target is the mean of d over matched products, with standard errors clustered by brand.

All results are in `../data/results.json` and `../reports/report.md`; no result is typed by hand in this README.
