"""Steps 2-3 (Clean + Match): turn price rows into the JSON file the website reads.

Usage:
    python build_dataset.py                       # collected_prices.csv (prices read from official sites)
    python build_dataset.py raw/prices_X.csv      # a scrape.py run instead

Keeps the latest price per product and market, drops products that are missing
either market, and writes ../data/prices.json.
Currency conversion and tax are applied in the browser so readers can change them.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
OUT = HERE.parent / "data" / "prices.json"
EXPECTED = {"us": "USD", "ca": "CAD"}
WATCH_NOTE = ("These are official list prices. Popular Rolex models often have waitlists and sell above list "
              "on the secondary market, which this comparison does not include.")


def load(path: Path) -> pd.DataFrame:
    """Read either the hand-collected log or a scrape.py output into one shape."""
    df = pd.read_csv(path)
    if "collected" in df.columns:  # collected_prices.csv
        df = df.rename(columns={"collected": "scraped_at"}).assign(status="ok")
    return df


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "collected_prices.csv"
    raw = load(src)
    products = pd.read_csv(HERE / "products.csv")

    ok = raw[(raw["status"] == "ok") & raw["price"].notna() & raw["market"].isin(EXPECTED)].copy()
    # a price in the wrong currency means the site redirected us to another region
    wrong = ok["currency"].ne(ok["market"].map(EXPECTED))
    if wrong.any():
        print(f"Dropping {wrong.sum()} rows with an unexpected currency")
    ok = ok[~wrong]

    latest = ok.sort_values("scraped_at").groupby(["brand_id", "product", "market"]).tail(1)
    wide = latest.pivot_table(index=["brand_id", "product"], columns="market", values="price", aggfunc="last").reset_index()
    urls = latest.pivot_table(index=["brand_id", "product"], columns="market", values="url", aggfunc="last")
    urls.columns = [f"src_{c}" for c in urls.columns]
    complete = (wide.dropna(subset=list(EXPECTED))
                .merge(urls.reset_index(), on=["brand_id", "product"])
                .merge(products.reindex(columns=["brand_id", "brand", "tier", "product", "category", "style", "image"]), on=["brand_id", "product"]))
    print(f"{len(complete)} of {len(products)} products have prices in both markets")

    # Brands missing any product photo go last; within a brand, items with a photo come first.
    tier_order = {"Accessible luxury": 0, "Luxury": 1, "Watchmaker": 2}
    has_img = complete["image"].fillna("").str.startswith("https://")
    complete = complete.assign(_noimg=~has_img, _brand_noimg=has_img.groupby(complete["brand_id"]).transform("mean") < 1)
    complete = complete.sort_values(["_brand_noimg", "tier", "brand", "_noimg", "us"],
                                    key=lambda c: c.map(tier_order) if c.name == "tier" else c)
    brands = []
    for (bid, name, tier), g in complete.groupby(["brand_id", "brand", "tier"], sort=False):
        brands.append({"id": bid, "name": name, "tier": tier, "items": [
            {"name": r["product"], "category": r["category"], "style": str(r["style"]),
             "price": {"us": round(float(r["us"]), 2), "ca": round(float(r["ca"]), 2)},
             "url": {"us": r["src_us"], "ca": r["src_ca"]},
             **({"image": r["image"]} if isinstance(r["image"], str) and r["image"].startswith("https://") else {})}
            for _, r in g.iterrows()]})

    out = {
        "meta": {
            "dataset": "official-list-prices",
            "description": "Official list prices read from each brand's US and Canadian websites.",
            "collected": str(latest["scraped_at"].max())[:10],
            "currency": {"us": "USD before sales tax", "ca": "CAD before sales tax"},
            "watch_note": WATCH_NOTE,
        },
        "brands": brands,
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(HERE.parent.parent)}")


if __name__ == "__main__":
    main()
