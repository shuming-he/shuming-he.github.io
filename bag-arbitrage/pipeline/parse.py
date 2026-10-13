"""Extract a product's list price from a saved or downloaded product page.

Brand sites differ in layout, but most publish schema.org Product data so search
engines can show prices. We read that first and fall back to common meta tags.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Iterable, Optional

from bs4 import BeautifulSoup

CURRENCY_SYMBOLS = {"C$": "CAD", "CA$": "CAD", "US$": "USD", "$": "USD", "¥": "CNY", "￥": "CNY", "RMB": "CNY"}


@dataclass
class Price:
    amount: float
    currency: Optional[str]
    source: str  # which part of the page the price came from


def parse_price_text(text: str) -> Optional[float]:
    """Turn strings like '¥12,800', 'C$1,295.00' or '1.295,00 €' into a float."""
    if text is None:
        return None
    s = str(text).strip()
    s = re.sub(r"[^\d.,]", "", s)
    if not s:
        return None
    if "," in s and "." in s:
        # whichever separator comes last is the decimal point
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        # '12,800' is thousands; '12,80' is a decimal comma
        head, _, tail = s.rpartition(",")
        s = s.replace(",", "") if len(tail) == 3 else head.replace(",", "") + "." + tail
    try:
        return float(s)
    except ValueError:
        return None


def guess_currency(text: str) -> Optional[str]:
    for sym, code in sorted(CURRENCY_SYMBOLS.items(), key=lambda kv: -len(kv[0])):
        if sym in text:
            return code
    return None


def _walk_jsonld(node) -> Iterable[dict]:
    if isinstance(node, list):
        for x in node:
            yield from _walk_jsonld(x)
    elif isinstance(node, dict):
        yield node
        for key in ("@graph", "offers", "itemListElement"):
            if key in node:
                yield from _walk_jsonld(node[key])


def _from_jsonld(soup: BeautifulSoup) -> Optional[Price]:
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for node in _walk_jsonld(data):
            types = node.get("@type", [])
            types = types if isinstance(types, list) else [types]
            if not ({"Offer", "AggregateOffer"} & set(types)):
                continue
            raw = node.get("price", node.get("lowPrice"))
            amount = parse_price_text(raw) if isinstance(raw, str) else (float(raw) if raw is not None else None)
            if amount:
                return Price(amount, node.get("priceCurrency"), "json-ld")
    return None


def _from_meta(soup: BeautifulSoup) -> Optional[Price]:
    pairs = [
        ({"property": "product:price:amount"}, {"property": "product:price:currency"}),
        ({"property": "og:price:amount"}, {"property": "og:price:currency"}),
        ({"itemprop": "price"}, {"itemprop": "priceCurrency"}),
    ]
    for amount_attrs, cur_attrs in pairs:
        tag = soup.find(attrs=amount_attrs)
        if not tag:
            continue
        amount = parse_price_text(tag.get("content") or tag.get_text())
        if amount:
            cur = soup.find(attrs=cur_attrs)
            return Price(amount, cur.get("content") if cur else None, "meta")
    return None


def extract_price(html: str) -> Optional[Price]:
    """Return the first price found in structured data, or None."""
    soup = BeautifulSoup(html, "html.parser")
    return _from_jsonld(soup) or _from_meta(soup)
