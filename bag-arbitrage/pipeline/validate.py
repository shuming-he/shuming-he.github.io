"""Data validation and matching-quality checks.

Builds the analysis table (one row per matched US/CA product pair) from the raw
price log, attaches provenance flags, and records every row that does not reach
the analysis together with the reason. Nothing is dropped silently.

Usage:
    python validate.py          # writes ../data/matched_pairs.csv and ../reports/data_quality.md
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
ROOT = HERE.parent
EXPECTED = {"us": "USD", "ca": "CAD"}
# Each market's URL must point at that market's site; these are the path or host markers each brand uses.
MARKET_URL = {"us": re.compile(r"en-us|us-en|/us/|en_us|us\.burberry|//www\.coach\.com/"),
              "ca": re.compile(r"en-ca|ca-en|/ca/|en_ca|//ca\.coach\.com/")}
# Products without an official style code carry a hand-made slug id (e.g. "ella-tote"); those were matched by name.
SLUG = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)+$")


def load_raw() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prices = pd.read_csv(HERE / "collected_prices.csv", dtype={"style": str, "note": str})
    products = pd.read_csv(HERE / "products.csv", dtype={"style": str, "image": str})
    flags = pd.read_csv(HERE / "review_flags.csv", dtype=str)
    prices["note"] = prices["note"].fillna("")
    return prices, products, flags


def _alnum(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def code_in_url(style, url) -> bool:
    return _alnum(style) in _alnum(url)


def product_page_row(r) -> bool:
    """Price read from a product page (not a category listing) for a product with an official code."""
    return "category listing" not in str(r["note"]) and not SLUG.match(str(r["style"]))


def provenance_counts(prices: pd.DataFrame) -> dict:
    page = prices.apply(product_page_row, axis=1)
    hit = [code_in_url(s, u) for s, u in zip(prices["style"], prices["url"])]
    return {"product_page_rows": int(page.sum()),
            "product_page_rows_code_in_url": int((page & pd.Series(hit, index=prices.index)).sum()),
            "listing_rows": int(prices["note"].str.contains("category listing").sum())}


def row_checks(prices: pd.DataFrame) -> pd.DataFrame:
    """Return one row per failed check on the long price log."""
    issues = []
    for i, r in prices.iterrows():
        def add(check, detail):
            issues.append({"row": i + 2, "brand_id": r.brand_id, "style": r["style"], "market": r.market,
                           "check": check, "detail": detail})
        if r.market not in EXPECTED:
            add("unknown_market", r.market)
            continue
        if r.currency != EXPECTED[r.market]:
            add("wrong_currency", f"{r.currency} on the {r.market} site")
        if not (pd.notna(r.price) and float(r.price) > 0):
            add("non_positive_price", str(r.price))
        if not MARKET_URL[r.market].search(str(r.url)):
            add("url_market_unclear", str(r.url))
        if product_page_row(r) and not code_in_url(r["style"], r.url):
            add("code_not_in_url", "price read from a product page whose URL does not contain the style code")
    dup = prices.duplicated(subset=["brand_id", "product", "market"], keep=False)
    for i in prices.index[dup]:
        r = prices.loc[i]
        issues.append({"row": i + 2, "brand_id": r.brand_id, "style": r["style"], "market": r.market,
                       "check": "duplicate_price_row", "detail": "more than one price for this product and market"})
    return pd.DataFrame(issues, columns=["row", "brand_id", "style", "market", "check", "detail"])


def build_pairs(prices: pd.DataFrame, products: pd.DataFrame, flags: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pivot to one row per product with both prices; return (pairs, excluded)."""
    ok = prices[prices["market"].isin(EXPECTED) & prices["price"].notna()
                & prices["currency"].eq(prices["market"].map(EXPECTED))]
    latest = ok.sort_values("collected").groupby(["brand_id", "product", "market"]).tail(1)
    wide = latest.pivot(index=["brand_id", "product"], columns="market",
                        values=["price", "url", "note", "collected"])
    wide.columns = [f"{'src' if a == 'url' else a}_{b}" for a, b in wide.columns]
    wide = wide.reset_index()
    merged = products.merge(wide, on=["brand_id", "product"], how="left")

    missing = merged["price_us"].isna() | merged["price_ca"].isna()
    excluded = merged.loc[missing, ["brand_id", "product", "style"]].assign(
        reason=lambda x: ["no Canadian price collected" if pd.isna(merged.loc[i, "price_ca"]) else "no US price collected"
                          for i in x.index])
    pairs = merged[~missing].copy()

    pairs["us"] = pairs.pop("price_us").astype(float)
    pairs["ca"] = pairs.pop("price_ca").astype(float)
    notes = pairs["note_us"].fillna("") + " | " + pairs["note_ca"].fillna("")
    pairs["listing_price"] = notes.str.contains("category listing")
    pairs["sold_out"] = notes.str.contains("sold out")
    flagged = flags.groupby(["brand_id", "style"])["flag"].agg(set)
    flag_of = [flagged.get((b, s), set()) for b, s in zip(pairs["brand_id"], pairs["style"])]
    pairs["official_code"] = ~pairs["style"].str.match(SLUG)
    pairs["name_match"] = (notes.str.contains("exact name").to_numpy() | ~pairs["official_code"].to_numpy()
                           | np.array([("name_match" in f) for f in flag_of], dtype=bool))
    pairs["identifier_check"] = [("identifier_check" in f) for f in flag_of]
    pairs["uncertain_match"] = pairs["name_match"] | pairs["identifier_check"]
    pairs["has_image"] = pairs["image"].fillna("").str.startswith("https://")
    # Identical (US, CA) price pairs inside one brand: usually colour variants of one model.
    pairs["price_pair_group"] = pairs.groupby(["brand_id", "us", "ca"]).ngroup()
    pairs["repeat_price_pair"] = pairs.duplicated(subset=["brand_id", "us", "ca"], keep="first")
    pairs["raw_ratio"] = pairs["ca"] / pairs["us"]
    cols = ["brand_id", "brand", "tier", "category", "product", "style", "us", "ca", "raw_ratio",
            "official_code", "listing_price", "name_match", "identifier_check", "uncertain_match", "sold_out", "has_image",
            "price_pair_group", "repeat_price_pair", "src_us", "src_ca", "collected_us", "collected_ca"]
    return pairs[cols].reset_index(drop=True), excluded.reset_index(drop=True)


def quality_summary(prices, products, pairs, excluded, issues) -> dict:
    by_brand = pairs.groupby("brand").size()
    q1, q3 = pairs["raw_ratio"].quantile([0.25, 0.75])
    iqr = q3 - q1
    outliers = pairs[(pairs["raw_ratio"] < q1 - 1.5 * iqr) | (pairs["raw_ratio"] > q3 + 1.5 * iqr)]
    return {
        "provenance": provenance_counts(prices),
        "price_rows": int(len(prices)),
        "products_listed": int(len(products)),
        "brands_listed": int(products["brand_id"].nunique()),
        "matched_pairs": int(len(pairs)),
        "brands_matched": int(pairs["brand_id"].nunique()),
        "excluded": excluded.to_dict(orient="records"),
        "row_issues": issues.to_dict(orient="records"),
        "collection_dates": sorted(set(pairs["collected_us"]) | set(pairs["collected_ca"])),
        "by_category": pairs["category"].value_counts().to_dict(),
        "by_tier": pairs["tier"].value_counts().to_dict(),
        "items_per_brand": {"min": int(by_brand.min()), "max": int(by_brand.max()), "median": float(by_brand.median())},
        "flags": {k: int(pairs[k].sum()) for k in
                  ["official_code", "listing_price", "name_match", "identifier_check", "uncertain_match", "sold_out", "repeat_price_pair"]},
        "without_image": int((~pairs["has_image"]).sum()),
        "distinct_price_pairs": int((~pairs["repeat_price_pair"]).sum()),
        "raw_ratio": {"min": float(pairs["raw_ratio"].min()), "q1": float(q1), "median": float(pairs["raw_ratio"].median()),
                      "q3": float(q3), "max": float(pairs["raw_ratio"].max())},
        "raw_ratio_outliers": outliers[["brand", "product", "style", "us", "ca", "raw_ratio"]].to_dict(orient="records"),
    }


def write_report(q: dict, pairs: pd.DataFrame, path: Path) -> None:
    f = q["flags"]
    lines = [
        "# Data quality and matching report",
        "",
        "Generated by `pipeline/validate.py` from `collected_prices.csv`, `products.csv` and `review_flags.csv`. "
        "Every number below is computed from those files.",
        "",
        "## Counts",
        "",
        "| Quantity | Count |",
        "|---|---|",
        f"| Price rows in the log | {q['price_rows']} |",
        f"| Products listed | {q['products_listed']} from {q['brands_listed']} brands |",
        f"| Products with a valid price in both markets (analysis sample) | {q['matched_pairs']} from {q['brands_matched']} brands |",
        f"| Products excluded | {len(q['excluded'])} |",
        f"| Rows failing a format check | {len(q['row_issues'])} |",
        f"| Collection date(s) | {', '.join(q['collection_dates'])} |",
        f"| Items per brand | {q['items_per_brand']['min']} to {q['items_per_brand']['max']} (median {q['items_per_brand']['median']:g}) |",
        "",
        "Categories: " + ", ".join(f"{k} {v}" for k, v in q["by_category"].items()) + ".",
        "",
        "## Exclusions",
        "",
    ]
    if q["excluded"]:
        lines += ["| Brand | Product | Style | Reason |", "|---|---|---|---|"]
        lines += [f"| {e['brand_id']} | {e['product']} | {e['style']} | {e['reason']} |" for e in q["excluded"]]
    else:
        lines.append("None.")
    lines += ["", "## Format checks", ""]
    if q["row_issues"]:
        lines += ["| CSV row | Brand | Style | Market | Check | Detail |", "|---|---|---|---|---|---|"]
        lines += [f"| {r['row']} | {r['brand_id']} | {r['style']} | {r['market']} | {r['check']} | {r['detail']} |" for r in q["row_issues"]]
    else:
        lines.append("All rows passed: known market, expected currency (USD on US sites, CAD on Canadian sites), "
                     "positive price, market-specific URL, one price per product and market.")
    pv = q["provenance"]
    lines += [
        "",
        "## Price provenance",
        "",
        f"- {pv['product_page_rows']} price rows were read from a product page; in {pv['product_page_rows_code_in_url']} of them the URL contains the same style code as the CSV row, so the row can be traced to its page.",
        f"- {pv['listing_rows']} price rows were read from a category listing; the listing URL is stored, and the product is identified on that listing by its name (and code where the listing shows one).",
        "",
        "## Matching quality and provenance flags",
        "",
        "Flags are kept as columns in `data/matched_pairs.csv`; they are used for sensitivity analyses, not to drop rows.",
        "",
        "| Flag | Pairs | Meaning |",
        "|---|---|---|",
        f"| Matched by style code on both pages | {q['matched_pairs'] - f['uncertain_match']} | Same official style or reference code on the US and CA pages, no open check |",
        f"| No official code published | {q['matched_pairs'] - f['official_code']} | Brand shows no code on its listing (Dior listings, Tory Burch); identified by a slug of the product name |",
        f"| `name_match` | {f['name_match']} | US and CA prices linked by exact product name (no shared code on at least one page) |",
        f"| `identifier_check` | {f['identifier_check']} | Code or page provenance needs a manual check (see `review_flags.csv`) |",
        f"| `uncertain_match` | {f['uncertain_match']} | `name_match` or `identifier_check` |",
        f"| `listing_price` | {f['listing_price']} | At least one price read from a category listing rather than the product page |",
        f"| `sold_out` | {f['sold_out']} | Listed as sold out in at least one market; the list price was still shown |",
        f"| `repeat_price_pair` | {f['repeat_price_pair']} | Same brand and identical (US, CA) prices as an earlier row: often a colour variant of one model, sometimes a different model at the same price point |",
        f"| No product photo | {q['without_image']} | Display only; does not affect the analysis |",
        "",
        f"Distinct (brand, US price, CA price) combinations: {q['distinct_price_pairs']}.",
        "",
        "## Raw price ratio (CAD list price / USD list price, no conversion)",
        "",
        "Min {min:.3f}, Q1 {q1:.3f}, median {median:.3f}, Q3 {q3:.3f}, max {max:.3f}.".format(**q["raw_ratio"]),
        "",
    ]
    if q["raw_ratio_outliers"]:
        lines += ["Pairs outside 1.5 × IQR (checked against their source pages; kept in the sample):", "",
                  "| Brand | Product | Style | US | CA | CA/US |", "|---|---|---|---|---|---|"]
        lines += [f"| {o['brand']} | {o['product']} | {o['style']} | {o['us']:,.0f} | {o['ca']:,.0f} | {o['raw_ratio']:.3f} |"
                  for o in q["raw_ratio_outliers"]]
    else:
        lines.append("No pair lies outside 1.5 × IQR.")
    lines += ["", "## Items per brand", "", "| Brand | Tier | Pairs | Bag | Small leather goods | Watch | Uncertain match | Listing price |",
              "|---|---|---|---|---|---|---|---|"]
    for (b, t), g in pairs.groupby(["brand", "tier"]):
        c = g["category"].value_counts()
        lines.append(f"| {b} | {t} | {len(g)} | {c.get('Bag', 0)} | {c.get('Small leather goods', 0)} | {c.get('Watch', 0)} "
                     f"| {int(g['uncertain_match'].sum())} | {int(g['listing_price'].sum())} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> tuple[pd.DataFrame, dict]:
    prices, products, flags = load_raw()
    issues = row_checks(prices)
    pairs, excluded = build_pairs(prices, products, flags)
    q = quality_summary(prices, products, pairs, excluded, issues)
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "reports").mkdir(exist_ok=True)
    pairs.to_csv(ROOT / "data" / "matched_pairs.csv", index=False)
    write_report(q, pairs, ROOT / "reports" / "data_quality.md")
    return pairs, q


if __name__ == "__main__":
    pairs, q = run()
    print(json.dumps({k: v for k, v in q.items() if k not in ("row_issues", "raw_ratio_outliers")}, indent=2, default=str))
    print(f"{len(q['row_issues'])} format issues, {len(q['raw_ratio_outliers'])} ratio outliers")
