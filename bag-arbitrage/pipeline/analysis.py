"""Step 4 (Test): reproduce the website's statistics in Python with SciPy.

Usage:
    python analysis.py
    python analysis.py --fx-cad 1.42 --tax-us 7 --tax-ca 13

The numbers should match the Statistics section of the page for the same settings,
which checks the hand-written JavaScript implementation against SciPy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

DATA = Path(__file__).parent.parent / "data" / "prices.json"


def load(fx_cad: float, tax_us: float, tax_ca: float) -> pd.DataFrame:
    d = json.loads(DATA.read_text(encoding="utf-8"))
    rows = [{"brand": b["name"], "tier": b["tier"], "product": it["name"], **it["price"]}
            for b in d["brands"] for it in b["items"]]
    df = pd.DataFrame(rows)
    df["us_usd"] = df["us"] * (1 + tax_us / 100)
    df["ca_usd"] = df["ca"] / fx_cad * (1 + tax_ca / 100)
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fx-cad", type=float, default=1.42)
    ap.add_argument("--tax-us", type=float, default=7.0)
    ap.add_argument("--tax-ca", type=float, default=13.0)
    a = ap.parse_args()
    df = load(a.fx_cad, a.tax_us, a.tax_ca)

    print(f"{len(df)} products, {df['brand'].nunique()} brands\n")
    log_ca, log_us = np.log(df["ca_usd"]), np.log(df["us_usd"])
    t = stats.ttest_rel(log_ca, log_us)
    diff = log_ca - log_us
    ci = stats.t.interval(0.95, len(diff) - 1, loc=diff.mean(), scale=stats.sem(diff))
    print(f"CA vs US  n={len(diff)}  geometric mean gap {np.expm1(diff.mean()):+.1%}  "
          f"95% CI [{np.expm1(ci[0]):+.1%}, {np.expm1(ci[1]):+.1%}]  t={t.statistic:.2f}  p={t.pvalue:.2g}")

    sticker = df["ca"] / df["us"]
    print(f"Sticker ratio CAD/USD: mean {sticker.mean():.3f}, range {sticker.min():.3f} to {sticker.max():.3f}")

    premium = df["ca_usd"] / df["us_usd"] - 1
    reg = stats.linregress(np.log10(df["us"]), premium)
    print(f"\nOLS  Canada premium ~ log10(US price): slope {reg.slope:+.4f} per x10 "
          f"({reg.slope * np.log10(2):+.1%} per doubling)  r={reg.rvalue:.2f}  R²={reg.rvalue ** 2:.2f}  p={reg.pvalue:.2g}")

    print("\nMean premium by brand")
    by = df.assign(premium=premium).groupby("brand")["premium"].mean()
    print(by.sort_values(ascending=False).map(lambda v: f"{v:+.1%}").to_string())


if __name__ == "__main__":
    main()
