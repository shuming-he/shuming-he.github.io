"""Tests for bastats and validate on small synthetic data with known answers."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bastats as bs  # noqa: E402
import validate  # noqa: E402


class PriceMaths(unittest.TestCase):
    def test_log_diff_known_value(self):
        # US $100 at 1.40 CAD/USD is C$140; a C$126 price is 10% lower: ln(0.9)
        d = bs.log_diff([100], [126], fx=1.40)
        self.assertAlmostEqual(d[0], np.log(0.9))
        self.assertAlmostEqual(bs.pct_from_log(d[0]), -10.0)

    def test_fx_direction(self):
        # a stronger US dollar (more CAD per USD) makes Canada look cheaper
        self.assertLess(bs.log_diff([100], [130], 1.45)[0], bs.log_diff([100], [130], 1.35)[0])

    def test_tax_is_a_constant_shift(self):
        us, ca = np.array([100, 2000, 50]), np.array([130, 2500, 70])
        shift = bs.log_diff(us, ca, 1.4, 7, 13) - bs.log_diff(us, ca, 1.4)
        np.testing.assert_allclose(shift, np.log(1.13 / 1.07))

    def test_rejects_bad_prices(self):
        for us, ca in [([100], [0]), ([-1], [10]), ([np.nan], [10]), ([1, 2], [1])]:
            with self.assertRaises(ValueError):
                bs.log_diff(us, ca, 1.4)
        with self.assertRaises(ValueError):
            bs.usd_to_cad([1], 0)
        with self.assertRaises(ValueError):
            bs.with_tax([1], -5)


class Estimators(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        self.cluster = np.repeat(list("ABCDEFGH"), [3, 5, 4, 6, 2, 5, 3, 4])
        brand_effect = dict(zip("ABCDEFGH", rng.normal(-0.1, 0.03, 8)))
        self.d = np.array([brand_effect[c] for c in self.cluster]) + rng.normal(0, 0.02, self.cluster.size)

    def test_paired_iid_matches_scipy(self):
        e = bs.paired_iid(self.d)
        ref = stats.ttest_1samp(self.d, 0)
        self.assertAlmostEqual(e.stat, ref.statistic)
        self.assertAlmostEqual(e.p, ref.pvalue)
        self.assertEqual(e.df, self.d.size - 1)

    def test_cluster_se_matches_manual_cr1(self):
        e = bs.cluster_robust_mean(self.d, self.cluster)
        n, G = self.d.size, 8
        u = pd.Series(self.d - self.d.mean()).groupby(self.cluster).sum()
        se = np.sqrt(G / (G - 1) * (u ** 2).sum()) / n
        self.assertAlmostEqual(e.se, se)
        self.assertEqual(e.df, G - 1)
        self.assertEqual(e.clusters, G)

    def test_cluster_mean_equals_ols_cluster_intercept(self):
        e = bs.cluster_robust_mean(self.d, self.cluster)
        r = bs.ols_cluster(self.d, np.ones((self.d.size, 1)), self.cluster, ["c"])
        self.assertAlmostEqual(r["coef"][0], e.mean_log)
        # OLS version adds the (n-1)/(n-k) factor, which is 1 when k = 1
        self.assertAlmostEqual(r["se_cluster"][0], e.se)

    def test_one_obs_per_cluster_reduces_to_hc1(self):
        d = np.array([0.1, -0.2, 0.05, 0.3, -0.1])
        e = bs.cluster_robust_mean(d, np.arange(5))
        n = d.size
        self.assertAlmostEqual(e.se, np.sqrt(n / (n - 1) * np.sum((d - d.mean()) ** 2)) / n)

    def test_clustering_widens_ci_when_brands_differ(self):
        self.assertGreater(bs.cluster_robust_mean(self.d, self.cluster).se, bs.paired_iid(self.d).se)

    def test_brand_equal_is_mean_of_brand_means(self):
        e = bs.brand_equal(self.d, self.cluster)
        self.assertAlmostEqual(e.mean_log, pd.Series(self.d).groupby(self.cluster).mean().mean())
        self.assertEqual(e.clusters, 8)

    def test_bootstrap_reproducible_and_contains_mean(self):
        a = bs.cluster_bootstrap(self.d, self.cluster, reps=999, seed=1)
        b = bs.cluster_bootstrap(self.d, self.cluster, reps=999, seed=1)
        self.assertEqual((a.ci_low, a.ci_high), (b.ci_low, b.ci_high))
        self.assertLess(a.ci_low, self.d.mean())
        self.assertGreater(a.ci_high, self.d.mean())

    def test_wild_bootstrap_enumeration(self):
        w = bs.wild_cluster_bootstrap_p(self.d, self.cluster)
        self.assertIn("256", w["draws"])
        # every brand mean is negative, so only the identity and full flip are as extreme
        self.assertAlmostEqual(w["p"], 2 / 256)
        # a null effect gives a large p-value
        centred = self.d - self.d.mean()
        self.assertGreater(bs.wild_cluster_bootstrap_p(centred, self.cluster)["p"], 0.5)

    def test_leave_one_out(self):
        loo = bs.leave_one_cluster_out(self.d, self.cluster)
        self.assertEqual(len(loo), 8)
        keep = self.cluster != "A"
        self.assertAlmostEqual(loo.set_index("dropped").loc["A", "mean_log"], self.d[keep].mean())

    def test_ols_recovers_slope(self):
        rng = np.random.default_rng(3)
        x = rng.normal(size=200)
        cl = np.repeat(np.arange(20), 10)
        y = 0.5 - 0.2 * x + rng.normal(0, 0.01, 200)
        r = bs.ols_cluster(y, np.column_stack([np.ones(200), x]), cl, ["c", "x"])
        self.assertAlmostEqual(r["coef"][1], -0.2, places=2)
        self.assertEqual(r.attrs["clusters"], 20)

    def test_collapse_identical_variants(self):
        df = pd.DataFrame({"brand_id": ["a", "a", "a", "b"], "us": [1, 1, 2, 1], "ca": [2, 2, 3, 2]})
        self.assertEqual(len(bs.collapse_identical_variants(df)), 3)


class Validation(unittest.TestCase):
    def frames(self):
        products = pd.DataFrame({
            "brand_id": ["x", "x", "y"], "brand": ["X", "X", "Y"], "tier": ["Luxury"] * 3,
            "product": ["P1", "P2", "P3"], "category": ["Bag"] * 3, "style": ["AB1", "ab-slug", "C3"],
            "url_us": [""] * 3, "url_ca": [""] * 3, "image": ["https://i", None, None]})
        prices = pd.DataFrame({
            "brand_id": ["x", "x", "x", "x", "y"], "product": ["P1", "P1", "P2", "P2", "P3"],
            "style": ["AB1", "AB1", "ab-slug", "ab-slug", "C3"], "market": ["us", "ca", "us", "ca", "us"],
            "price": [100, 130, 50, 65, 10], "currency": ["USD", "CAD", "USD", "CAD", "USD"],
            "url": ["https://b.com/en-us/1", "https://b.com/en-ca/1", "https://b.com/en-us/2", "https://b.com/en-ca/2",
                    "https://b.com/en-us/3"],
            "collected": ["2026-10-13"] * 5, "note": ["", "price read from category listing", "", "", ""]})
        flags = pd.DataFrame(columns=["brand_id", "style", "flag", "detail"])
        return prices, products, flags

    def test_unmatched_product_is_reported_not_dropped_silently(self):
        pairs, excluded = validate.build_pairs(*self.frames())
        self.assertEqual(len(pairs), 2)
        self.assertEqual(excluded["product"].tolist(), ["P3"])
        self.assertIn("Canadian", excluded["reason"][0])

    def test_flags(self):
        pairs, _ = validate.build_pairs(*self.frames())
        p = pairs.set_index("product")
        self.assertTrue(p.loc["P1", "listing_price"])
        self.assertFalse(p.loc["P1", "name_match"])
        self.assertTrue(p.loc["P2", "name_match"])          # slug id means no official code
        self.assertFalse(p.loc["P2", "has_image"])

    def test_wrong_currency_is_flagged_and_excluded(self):
        prices, products, flags = self.frames()
        prices.loc[1, "currency"] = "USD"                   # Canadian page redirected to the US store
        issues = validate.row_checks(prices)
        self.assertIn("wrong_currency", issues["check"].tolist())
        pairs, excluded = validate.build_pairs(prices, products, flags)
        self.assertNotIn("P1", pairs["product"].tolist())
        self.assertIn("P1", excluded["product"].tolist())

    def test_duplicate_rows_flagged(self):
        prices, _, _ = self.frames()
        prices = pd.concat([prices, prices.iloc[[0]]], ignore_index=True)
        self.assertIn("duplicate_price_row", validate.row_checks(prices)["check"].tolist())


if __name__ == "__main__":
    unittest.main()
