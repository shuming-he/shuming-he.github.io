# Data dictionary

## `pipeline/collected_prices.csv`: raw price log (one row per product per market)

| Column | Type | Description |
|---|---|---|
| `brand_id` | string | Brand key, lower case (e.g. `rolex`) |
| `product` | string | Product name as shown on the brand site |
| `style` | string | Brand style or reference code. Where the brand publishes none (Tory Burch, most Dior listings), a slug of the product name |
| `market` | `us` / `ca` | Which official site the price was read from |
| `price` | number | List price before sales tax, in `currency` |
| `currency` | `USD` / `CAD` | Must be USD on US sites and CAD on Canadian sites; any other value is rejected |
| `url` | URL | Page the price was read from (product page or category listing) |
| `collected` | date | Date the price was read (all rows: 2026-10-13) |
| `note` | string | Provenance: price read from a category listing, matched by exact name, shown as sold out, etc. |

## `pipeline/products.csv`: product list

`brand_id`, `brand` (display name), `tier` (`Accessible luxury`, `Luxury`, `Watchmaker`; assigned by the author by brand), `product`, `category` (`Bag`, `Small leather goods`, `Watch`), `style`, `url_us`, `url_ca` (product or listing pages), `image` (official product photo URL, display only; empty for 12 products).

## `pipeline/review_flags.csv`: manual review notes

`brand_id`, `style`, `flag` (`identifier_check`, `name_match`, `name_change`, `label_inconsistency`), `detail`.

## `pipeline/fx_rates.csv`: exchange rates

`date`, `series` (`FXUSDCAD`), `cad_per_usd` (Bank of Canada daily average rate, Canadian dollars per US dollar), `source`.

## `data/matched_pairs.csv`: analysis table (one row per matched product), written by `validate.py`

| Column | Description |
|---|---|
| `brand_id`, `brand`, `tier`, `category`, `product`, `style` | From `products.csv` |
| `us`, `ca` | US list price (USD) and Canadian list price (CAD), before tax |
| `raw_ratio` | `ca / us`, CAD per USD implied by the two list prices |
| `official_code` | `True` if `style` is a brand code, `False` if it is a name slug |
| `listing_price` | At least one of the two prices was read from a category listing |
| `name_match` | US and CA prices linked by exact product name rather than a shared code |
| `identifier_check` | Listed in `review_flags.csv` as needing an identifier check |
| `uncertain_match` | `name_match` or `identifier_check` |
| `sold_out` | Shown as sold out in at least one market (list price still displayed) |
| `has_image` | An official photo URL is available (display only) |
| `price_pair_group`, `repeat_price_pair` | Group id for identical (brand, US, CA) prices; `True` for the second and later rows of a group |
| `src_us`, `src_ca`, `collected_us`, `collected_ca` | Source URL and date for each price |

## Derived quantities

| Name | Definition |
|---|---|
| `fx` | CAD per USD; primary value: Bank of Canada rate on the last business day before collection (2026-10-09, 1.4271) |
| `d` | `ln(ca / (us × fx))`; negative means cheaper in Canada |
| percentage difference | `exp(d) − 1` |
| implied exchange rate | `fx × exp(mean d)` = geometric mean of `raw_ratio` |
| after-tax scenario | `d + ln((1 + t_CA) / (1 + t_US))` |

## `data/results.json`

Machine-readable output of `run_analysis.py`, read by the website and the report: `meta` (versions, seed, estimand), `quality` (counts from validation), `primary`, `wild_bootstrap`, `robustness`, `subsets`, `leave_one_brand_out`, `influential_products`, `brands`, `fx_scenarios`, `tax_scenarios`, `breakeven_fx`, `regressions`, `distribution`. Percentages are in percent; `mean_log`, `se`, `ci_low`, `ci_high` are on the log scale.

## `data/prices.json`

Website dataset written by `build_dataset.py`: `meta` and `brands[]`, each with `items[]` holding `name`, `category`, `style`, `price.us`, `price.ca`, `url.us`, `url.ca` and optional `image`.
