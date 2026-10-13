"""Step 1 (Scrape): download each product page listed in products.csv and record its price.

Usage:
    python scrape.py                     # all products with a URL
    python scrape.py --brand coach       # one brand
    python scrape.py --delay 5           # seconds between requests (default 3)

Output: raw/prices_<YYYYMMDD-HHMM>.csv, one row per product per market.
Rows are kept even when a fetch fails, with the reason in `status`, so coverage is auditable.
"""
from __future__ import annotations

import argparse
import csv
import time
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

from parse import extract_price

HERE = Path(__file__).parent
MARKETS = {"us": "USD", "ca": "CAD", "cn": "CNY"}
USER_AGENT = "BagArbitrageResearchBot/0.1 (student data science project; https://shuming-he.github.io/bag-arbitrage/)"

_robots: dict[str, urllib.robotparser.RobotFileParser] = {}


def allowed(url: str) -> bool:
    """Respect robots.txt for every host we visit."""
    root = "{0.scheme}://{0.netloc}".format(urlparse(url))
    if root not in _robots:
        rp = urllib.robotparser.RobotFileParser(root + "/robots.txt")
        try:
            rp.read()
        except Exception:
            rp = None
        _robots[root] = rp
    rp = _robots[root]
    return True if rp is None else rp.can_fetch(USER_AGENT, url)


def fetch(session: requests.Session, url: str) -> tuple[str, str | None]:
    if not allowed(url):
        return "blocked-by-robots", None
    try:
        r = session.get(url, timeout=20)
    except requests.RequestException as e:
        return f"error:{type(e).__name__}", None
    if r.status_code != 200:
        return f"http-{r.status_code}", None
    return "ok", r.text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", help="only scrape this brand_id")
    ap.add_argument("--delay", type=float, default=3.0)
    args = ap.parse_args()

    products = list(csv.DictReader(open(HERE / "products.csv", newline="", encoding="utf-8")))
    if args.brand:
        products = [p for p in products if p["brand_id"] == args.brand]

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8"})

    out_dir = HERE / "raw"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    out_path = out_dir / f"prices_{stamp}.csv"
    fields = ["scraped_at", "brand_id", "product", "market", "url", "status", "price", "currency", "source"]

    n_ok = n_try = 0
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for p in products:
            for m, default_cur in MARKETS.items():
                url = (p.get(f"url_{m}") or "").strip()
                if not url:
                    continue
                n_try += 1
                status, html = fetch(session, url)
                price = extract_price(html) if html else None
                if html and not price:
                    status = "no-price-found"
                n_ok += price is not None
                w.writerow({
                    "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "brand_id": p["brand_id"], "product": p["product"], "market": m, "url": url,
                    "status": status, "price": price.amount if price else "",
                    "currency": (price.currency or default_cur) if price else "", "source": price.source if price else "",
                })
                print(f"[{status:>16}] {p['brand_id']:<16} {m}  {p['product']}")
                time.sleep(args.delay)

    print(f"\n{n_ok}/{n_try} prices captured -> {out_path.relative_to(HERE)}")
    if n_try == 0:
        print("No URLs in products.csv yet. Add official product page URLs to url_us / url_ca / url_cn.")


if __name__ == "__main__":
    main()
