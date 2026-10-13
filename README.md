# Shuming He · Portfolio

I am a first-year Mathematics & Statistics student at the University of Toronto.
This repository is my portfolio website, live at **https://shuming-he.github.io**. Contact: smhe@outlook.com

## Project: Cross-Border Luxury Pricing (US vs Canada)

**Question.** For identical products sold on a brand's official US and Canadian websites, how do Canadian list prices compare with US list prices converted at the market exchange rate?

**Data.** The data are real, hand-collected official list prices, not illustrative or simulated values.
- On 13 October 2026, prices were read from each brand's own US and Canadian websites for 166 products from 16 brands.
- 165 products from 15 brands have a price in both markets. One Burberry product has no Canadian price and is reported as an exclusion.
- Every price row in [`collected_prices.csv`](bag-arbitrage/pipeline/collected_prices.csv) has its currency, source URL, date and a provenance note.
- In all 126 rows read from a product page, the URL contains the same style code as the row. The other 205 rows were read from category listings, and the note says so.
- Source links show each page as it was on 13 October 2026. Brands often remove or move product pages, so some links may stop working; the analysis uses only the recorded values and does not depend on them. Internet Archive copies, where the archive could make one, are listed with their capture dates in [`archived_sources.csv`](bag-arbitrage/pipeline/archived_sources.csv). A copy captured on another day may show a different price.

**Method.**
- **Estimand.** The mean over matched product listings of d = ln(P_CA / (P_US × X)).
- **Prices.** List prices before tax.
- **Exchange rate.** X is the Bank of Canada rate for 9 October 2026 (1.4271 CAD per USD).
- **Inference.** Clustered by brand, plus a wild cluster bootstrap.
- **Robustness and scenarios.** Robustness checks, regressions and tax/exchange-rate scenarios are reported separately.

**Result.**
- Canadian list prices are on average 10.2% lower than converted US prices before tax (95% CI −12.0% to −8.3%; 15 brand clusters).
- The comparison is descriptive and does not identify why prices differ.
- The full numbers are in [`results.json`](bag-arbitrage/data/results.json) and the [report](https://shuming-he.github.io/bag-arbitrage/reports/report.html).

| | |
|---|---|
| Live page | [shuming-he.github.io/bag-arbitrage](https://shuming-he.github.io/bag-arbitrage/) |
| Report | [reports/report.md](bag-arbitrage/reports/report.md) · [HTML](https://shuming-he.github.io/bag-arbitrage/reports/report.html) |
| Data quality | [reports/data_quality.md](bag-arbitrage/reports/data_quality.md) |
| Audit of an earlier version | [reports/audit.md](bag-arbitrage/reports/audit.md) |
| Pipeline | [bag-arbitrage/pipeline/](bag-arbitrage/pipeline/) |

### Reproduce

```bash
cd bag-arbitrage/pipeline
pip install -r requirements.txt
python -m unittest discover tests
python run_analysis.py
git diff --stat ../data/results.json   # no change means the published results were reproduced exactly
```

`run_analysis.py` validates the raw log, rebuilds the website dataset, and regenerates every estimate, table, figure and the report. The bootstrap is seeded and the wild bootstrap is enumerated, so the output is identical on each run with the pinned versions.

The project page computes its scenario explorer in the browser from `prices.json`. At the default setting, it reproduces the primary estimate in `results.json` exactly; this is checked by [`tests/site_consistency.js`](bag-arbitrage/pipeline/tests/site_consistency.js).

## Repository layout

| Path | What it is |
|---|---|
| `index.html` | Portfolio home |
| `assets/` | Shared styles and scripts |
| `bag-arbitrage/index.html` | Project page |
| `bag-arbitrage/data/` | `prices.json` (page dataset), `matched_pairs.csv` (analysis table), `results.json` (all results) |
| `bag-arbitrage/pipeline/` | Raw data, validation, analysis, tests |
| `bag-arbitrage/reports/` | Report, data quality, data dictionary, audit, claim audit |
| `bag-arbitrage/figures/` | Report figures (SVG) |

The site is plain HTML, CSS and JavaScript. It has no frameworks and no build step.

Product images on the page are loaded from brand websites for identification only. Some brand image servers block loading from other sites, and the page then shows the brand's initials instead.
