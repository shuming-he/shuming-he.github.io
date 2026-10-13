# Shuming He · Data Science Portfolio

I am a first-year Mathematics & Statistics student at the University of Toronto, building toward graduate study in data science.
This repository is my portfolio website, live at **https://shuming-he.github.io**. Contact: smhe@outlook.com

## Projects

| # | Project | Live demo | Code | Status |
|---|---|---|---|---|
| P01 | **Bag Arbitrage**: is the same luxury bag or watch cheaper in Canada or the US once currency and tax are accounted for? 31 products from 15 brands with real list prices from official US and Canadian websites, a paired t-test on log price ratios, the implied exchange rate in brand pricing, OLS regression, interactive explorer. | [shuming-he.github.io/bag-arbitrage](https://shuming-he.github.io/bag-arbitrage/) | [`bag-arbitrage/`](bag-arbitrage/) · pipeline in [`bag-arbitrage/pipeline/`](bag-arbitrage/pipeline/) | Live |

## Repository layout

| Path | What it is |
|---|---|
| `index.html` | Portfolio home |
| `assets/` | Shared styles and scripts |
| `bag-arbitrage/index.html` | Bag Arbitrage project page |
| `bag-arbitrage/data/prices.json` | Dataset the page reads |
| `bag-arbitrage/pipeline/` | Python scraper, parser tests, dataset builder and SciPy analysis |

The site is plain HTML, CSS and JavaScript with hand-built SVG charts. There are no frameworks and no build step; GitHub Pages serves the files as they are.

Bag Arbitrage currently displays an illustrative prototype dataset. See [`bag-arbitrage/pipeline/README.md`](bag-arbitrage/pipeline/README.md) for the scraper's status.
