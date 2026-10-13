# Shuming He · Data Science Portfolio

I am a first-year Mathematics & Statistics student at the University of Toronto, building toward graduate study in data science.
This repository is my portfolio website, live at **https://shuming-he.github.io**.

## Projects

| # | Project | Live demo | Code | Status |
|---|---|---|---|---|
| P01 | **Bag Arbitrage**: do identical luxury bags and watches cost more in China or Canada than in the US once currency and tax are accounted for? 47 products, 15 brands, paired t-tests on log price ratios, OLS regression, interactive explorer. | [shuming-he.github.io/bag-arbitrage](https://shuming-he.github.io/bag-arbitrage/) | [`bag-arbitrage/`](bag-arbitrage/) · pipeline in [`bag-arbitrage/pipeline/`](bag-arbitrage/pipeline/) | Live (prototype data) |
| P02 | **Clash Royale Analysis** | Coming soon | | In progress |
| P03 | **Course Assignments** | Coming soon | | In progress |

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
