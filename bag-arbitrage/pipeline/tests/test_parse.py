"""Run with: python -m unittest discover tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from parse import extract_price, parse_price_text  # noqa: E402

JSONLD_PAGE = """<html><head><script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"Tabby Shoulder Bag 26",
 "offers":{"@type":"Offer","price":"4600.00","priceCurrency":"CNY"}}
</script></head><body></body></html>"""

GRAPH_PAGE = """<script type="application/ld+json">
{"@graph":[{"@type":"BreadcrumbList"},{"@type":"Product","offers":[{"@type":"Offer","price":650,"priceCurrency":"CAD"}]}]}
</script>"""

META_PAGE = """<meta property="product:price:amount" content="1,295.00">
<meta property="product:price:currency" content="CAD">"""

BROKEN_PAGE = """<script type="application/ld+json">{not json</script><span itemprop="price" content="495"></span>"""


class ParseText(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(parse_price_text("¥12,800"), 12800)
        self.assertEqual(parse_price_text("C$1,295.00"), 1295.0)
        self.assertEqual(parse_price_text("1.295,00 €"), 1295.0)
        self.assertEqual(parse_price_text("$495"), 495)
        self.assertEqual(parse_price_text("12,80"), 12.8)
        self.assertIsNone(parse_price_text("Sold out"))


class Extract(unittest.TestCase):
    def test_jsonld(self):
        p = extract_price(JSONLD_PAGE)
        self.assertEqual((p.amount, p.currency, p.source), (4600.0, "CNY", "json-ld"))

    def test_graph_and_offer_list(self):
        p = extract_price(GRAPH_PAGE)
        self.assertEqual((p.amount, p.currency), (650.0, "CAD"))

    def test_meta_fallback(self):
        p = extract_price(META_PAGE)
        self.assertEqual((p.amount, p.currency, p.source), (1295.0, "CAD", "meta"))

    def test_broken_jsonld_falls_back(self):
        p = extract_price(BROKEN_PAGE)
        self.assertEqual(p.amount, 495.0)

    def test_no_price(self):
        self.assertIsNone(extract_price("<html><body>Hello</body></html>"))


if __name__ == "__main__":
    unittest.main()
