"""Static figures for the report (SVG, matplotlib). Colours match the website."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

US, CA, INK, MUTED = "#1a9dbb", "#8c7cf2", "#1d1d1f", "#6e6e73"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "svg.fonttype": "none", "svg.hashsalt": "bag-arbitrage"})


def _pct(x):
    return np.expm1(x) * 100


def brand_forest(brands: pd.DataFrame, primary: dict, out: Path) -> None:
    b = brands.sort_values("mean_log")
    fig, ax = plt.subplots(figsize=(7, 5.2))
    y = np.arange(len(b))
    lo = b["ci_low_pct"].astype(float)
    hi = b["ci_high_pct"].astype(float)
    ax.hlines(y, lo, hi, color=MUTED, lw=1.2)
    ax.plot(b["pct"], y, "o", color=CA, ms=6)
    ax.axvline(0, color=INK, lw=.8)
    ax.axvspan(primary["ci_low_pct"], primary["ci_high_pct"], color=US, alpha=.15, lw=0)
    ax.axvline(primary["pct"], color=US, lw=1.2, ls="--")
    ax.set_yticks(y, [f"{r.brand} (n={r.n})" for r in b.itertuples()])
    ax.set_xlabel("Canadian list price vs US list price converted to CAD (%)")
    ax.set_title("Brand means with within-brand 95% intervals\n(dashed line and band: pooled estimate, brand-clustered 95% CI)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out, metadata={"Date": None})
    plt.close(fig)


def distribution(df: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 3.2))
    order = df.groupby("category")["d"].median().sort_values().index
    for i, cat in enumerate(order):
        x = _pct(df.loc[df["category"] == cat, "d"].to_numpy())
        jitter = (np.random.default_rng(i).random(x.size) - .5) * .35
        ax.plot(x, i + jitter, "o", ms=4, alpha=.7, color=[US, CA, MUTED][i % 3])
    ax.set_yticks(range(len(order)), [f"{c} (n={(df['category'] == c).sum()})" for c in order])
    ax.axvline(0, color=INK, lw=.8)
    ax.set_xlabel("Product-level difference (%), before tax")
    ax.set_title("Distribution of product-level price differences by category", fontsize=10)
    fig.tight_layout()
    fig.savefig(out, metadata={"Date": None})
    plt.close(fig)


def price_scatter(df: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for cat, c in zip(["Bag", "Small leather goods", "Watch"], [CA, MUTED, US]):
        s = df[df["category"] == cat]
        ax.scatter(s["us"], _pct(s["d"]), s=14, color=c, alpha=.75, label=cat)
    ax.set_xscale("log")
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xlabel("US list price (USD, log scale)")
    ax.set_ylabel("Difference (%)")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Price difference against price level", fontsize=10)
    fig.tight_layout()
    fig.savefig(out, metadata={"Date": None})
    plt.close(fig)


def loo_plot(loo: pd.DataFrame, primary: dict, out: Path) -> None:
    l = loo.sort_values("pct")
    fig, ax = plt.subplots(figsize=(7, 4.6))
    ax.plot(l["pct"], range(len(l)), "o", color=US)
    ax.axvline(primary["pct"], color=CA, ls="--", lw=1)
    ax.set_yticks(range(len(l)), [f"without {b}" for b in l["dropped"]])
    ax.set_xlabel("Pooled difference (%) after removing one brand")
    ax.set_title("Leave-one-brand-out influence (dashed: all brands)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out, metadata={"Date": None})
    plt.close(fig)


def fx_plot(fx_rows: list, primary: dict, out: Path) -> None:
    h = pd.DataFrame([r for r in fx_rows if r["date"] == "hypothetical"] + [r for r in fx_rows if r["date"] != "hypothetical"])
    h = h.drop_duplicates("fx").sort_values("fx")
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.fill_between(h["fx"], h["ci_low_pct"], h["ci_high_pct"], color=US, alpha=.18, lw=0)
    ax.plot(h["fx"], h["pct"], color=US)
    ax.axhline(0, color=INK, lw=.8)
    ax.axvline(primary["fx"], color=CA, ls="--", lw=1)
    ax.axvline(primary["implied_fx"], color=MUTED, ls=":", lw=1)
    ax.annotate(f"BoC {primary['fx_date']}: {primary['fx']}", (primary["fx"], ax.get_ylim()[1]), fontsize=8,
                ha="right", va="top", color=CA)
    ax.annotate(f"implied {primary['implied_fx']:.3f}", (primary["implied_fx"], ax.get_ylim()[0]), fontsize=8,
                ha="left", va="bottom", color=MUTED)
    ax.set_xlabel("Exchange rate (CAD per USD)")
    ax.set_ylabel("Difference (%)")
    ax.set_title("Sensitivity of the pre-tax difference to the exchange rate (band: 95% CI)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out, metadata={"Date": None})
    plt.close(fig)


def make_all(df, brands, loo, fx_rows, primary, outdir: Path) -> None:
    brand_forest(brands, primary, outdir / "brand_forest.svg")
    distribution(df, outdir / "distribution.svg")
    price_scatter(df, outdir / "price_scatter.svg")
    loo_plot(loo, primary, outdir / "leave_one_brand_out.svg")
    fx_plot(fx_rows, primary, outdir / "fx_sensitivity.svg")
