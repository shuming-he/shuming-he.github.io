"""Steps 2-3 (Clean + Match): turn raw scrape rows into the JSON file the website reads.

Usage:
    python build_dataset.py                       # newest file in raw/
    python build_dataset.py raw/prices_X.csv      # a specific scrape

Keeps the latest successful price per product and market, drops products that are
missing any of the three markets, and writes ../data/prices.json.
Currency conversion and tax are applied in the browser so readers can change them.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
OUT = HERE.parent / "data" / "prices.json"
EXPECTED = {"us": "USD", "ca": "CAD", "cn": "CNY"}
WATCH_NOTE = ("These are authorized dealer list prices. Popular Rolex, AP and Patek models often have waitlists "
              "and sell above list on the secondary market, which this comparison does not include.")


def main() -> None:
    raw_path = Path(sys.argv[1]) if len(sys.argv) > 1 else max((HERE / "raw").glob("prices_*.csv"))
    raw = pd.read_csv(raw_path)
    products = pd.read_csv(HERE / "products.csv")

    ok = raw[(raw["status"] == "ok") & raw["price"].notna()].copy()
    # a price in the wrong currency means the site redirected us to another region
    wrong = ok["currency"].ne(ok["market"].map(EXPECTED))
    if wrong.any():
        print(f"Dropping {wrong.sum()} rows with an unexpected currency")
    ok = ok[~wrong]

    latest = ok.sort_values("scraped_at").groupby(["brand_id", "product", "market"]).tail(1)
    wide = latest.pivot_table(index=["brand_id", "product"], columns="market", values="price", aggfunc="last").reset_index()
    complete = wide.dropna(subset=list(EXPECTED)).merge(products, on=["brand_id", "product"], how="inner")
    print(f"{len(complete)} of {len(products)} products have prices in all three markets")

    brands = []
    for (bid, name, tier), g in complete.groupby(["brand_id", "brand", "tier"], sort=False):
        brands.append({"id": bid, "name": name, "tier": tier, "items": [
            {"name": r["product"], "category": r["category"],
             "price": {"us": round(float(r["us"]), 2), "ca": round(float(r["ca"]), 2), "cn": round(float(r["cn"]), 2)}}
            for _, r in g.iterrows()]})

    out = {
        "meta": {
            "dataset": "scraped",
            "description": f"Official list prices scraped by pipeline/scrape.py ({raw_path.name}).",
            "collected": str(latest["scraped_at"].max())[:10],
            "currency": {"us": "USD before sales tax", "ca": "CAD before sales tax", "cn": "CNY, 13% VAT included"},
            "watch_note": WATCH_NOTE,
        },
        "brands": brands,
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(HERE.parent.parent)}")


if __name__ == "__main__":
    main()
