"""Single command that reproduces every number in the study.

    python run_analysis.py

Steps: validate the raw price log -> rebuild the website dataset -> primary analysis ->
robustness checks -> tables, figures, results.json -> research report.
All randomness uses the seed in SEED; the wild bootstrap enumerates every sign pattern.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import bastats as bs
import validate

HERE = Path(__file__).parent
ROOT = HERE.parent
TABLES = ROOT / "reports" / "tables"
FIGS = ROOT / "figures"
SEED = 20261013
BOOT_REPS = 9999
# Tax scenarios. Canadian rates are CRA GST/HST rates; US rates are illustrative combined sales-tax levels.
CA_TAX = {"GST only (AB, and before provincial tax elsewhere)": 5.0, "HST Ontario": 13.0, "HST Nova Scotia": 14.0,
          "HST New Brunswick / Newfoundland and Labrador / PEI": 15.0}
US_TAX = {"No sales tax (e.g. Oregon)": 0.0, "4%": 4.0, "7%": 7.0, "8.875%": 8.875, "10.25%": 10.25}


def primary_fx(collected: str) -> tuple[float, str, pd.DataFrame]:
    """Bank of Canada daily rate on the last business day before collection."""
    fx = pd.read_csv(HERE / "fx_rates.csv", dtype={"date": str})
    before = fx[fx["date"] < collected]
    row = before.sort_values("date").iloc[-1]
    return float(row["cad_per_usd"]), row["date"], fx


def estimate_all(df: pd.DataFrame, fx: float) -> dict:
    d = bs.log_diff(df["us"], df["ca"], fx)
    return {"d": d, "cluster": df["brand"].to_numpy()}


def subset_estimate(df: pd.DataFrame, mask, fx: float, label: str) -> dict:
    sub = df[mask]
    d = bs.log_diff(sub["us"], sub["ca"], fx)
    g = sub["brand"].nunique()
    if g >= 2:
        e = bs.cluster_robust_mean(d, sub["brand"].to_numpy()).as_dict()
    else:
        e = bs.paired_iid(d).as_dict()
        e["note"] = "single brand: products treated as independent"
    e["label"] = label
    return e


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(exist_ok=True)

    # 1. validation and website dataset
    pairs, quality = validate.run()
    subprocess.run([sys.executable, str(HERE / "build_dataset.py")], check=True, cwd=HERE)
    collected = quality["collection_dates"][-1]
    fx, fx_date, fx_table = primary_fx(collected)

    df = pairs.copy()
    d = bs.log_diff(df["us"], df["ca"], fx)
    cl = df["brand"].to_numpy()
    df["d"] = d

    # 2. primary estimand: product-weighted mean of d, inference clustered by brand
    primary = bs.cluster_robust_mean(d, cl).as_dict()
    primary["sd"] = float(np.std(d, ddof=1))
    primary["brands"] = int(df["brand"].nunique())
    primary["fx"], primary["fx_date"] = fx, fx_date
    primary["implied_fx"] = float(fx * np.exp(primary["mean_log"]))
    primary["implied_fx_ci"] = [float(fx * np.exp(primary["ci_low"])), float(fx * np.exp(primary["ci_high"]))]
    wild = bs.wild_cluster_bootstrap_p(d, cl)

    # 3. robustness checks (same d, different weighting / inference / sample)
    rob = []
    def add(label, e, kind):
        e = e.as_dict() if isinstance(e, bs.Estimate) else e
        e["label"], e["kind"] = label, kind
        rob.append(e)
    add("Primary: product-weighted mean, brand-clustered CR1", bs.cluster_robust_mean(d, cl), "inference")
    add("Products treated as independent (naive paired t)", bs.paired_iid(d), "inference")
    add("Brand cluster bootstrap, percentile CI", bs.cluster_bootstrap(d, cl, BOOT_REPS, SEED), "inference")
    add("Each brand weighted equally", bs.brand_equal(d, cl), "weighting")
    add("Wilcoxon signed-rank (median)", bs.wilcoxon_signed_rank(d), "inference")
    collapsed = bs.collapse_identical_variants(df)
    add("One row per identical (brand, US, CA) price pair (approximate model level)", bs.cluster_robust_mean(collapsed["d"], collapsed["brand"].to_numpy()), "sample")
    for flag, label in [("uncertain_match", "Excluding uncertain matches"), ("listing_price", "Excluding prices read from category listings"),
                        ("sold_out", "Excluding items shown as sold out")]:
        keep = ~df[flag]
        add(label, bs.cluster_robust_mean(df.loc[keep, "d"], df.loc[keep, "brand"].to_numpy()), "sample")

    subsets = []
    for cat in ["Bag", "Small leather goods", "Watch"]:
        subsets.append(subset_estimate(df, df["category"] == cat, fx, cat))
    for tier in ["Accessible luxury", "Luxury", "Watchmaker"]:
        subsets.append(subset_estimate(df, df["tier"] == tier, fx, tier))

    loo = bs.leave_one_cluster_out(d, cl)
    brands = bs.brand_summary(d, cl).sort_values("mean_log").reset_index(drop=True)
    tier_of = df.groupby("brand")["tier"].first()
    brands["tier"] = brands["brand"].map(tier_of)
    # most influential single products: change in the mean when each one is left out
    infl = pd.DataFrame({"brand": df["brand"], "product": df["product"], "d": d,
                         "mean_without": (d.sum() - d) / (d.size - 1)})
    infl["change_pct_points"] = (np.expm1(infl["mean_without"]) - np.expm1(d.mean())) * 100
    infl = infl.reindex(infl["change_pct_points"].abs().sort_values(ascending=False).index)

    # 4. scenarios: FX and tax shift every d_i by the same constant, so the clustered SE is unchanged
    se = primary["se"]
    tcrit = (primary["ci_high"] - primary["mean_log"]) / se
    def shifted(shift):
        m = primary["mean_log"] + shift
        return {"pct": bs.pct_from_log(m), "ci_low_pct": bs.pct_from_log(m - tcrit * se), "ci_high_pct": bs.pct_from_log(m + tcrit * se)}
    fx_rows = []
    for _, r in fx_table.iterrows():
        fx_rows.append({"date": r["date"], "fx": float(r["cad_per_usd"]), **shifted(np.log(fx / r["cad_per_usd"]))})
    for v in [1.25, 1.30, 1.35, 1.40, 1.42, 1.45, 1.50, 1.55]:
        fx_rows.append({"date": "hypothetical", "fx": v, **shifted(np.log(fx / v))})
    tax_rows = []
    for cn, ct in CA_TAX.items():
        for un, ut in US_TAX.items():
            tax_rows.append({"ca_tax": cn, "ca_rate": ct, "us_tax": un, "us_rate": ut,
                             **shifted(np.log((1 + ct / 100) / (1 + ut / 100)))})
    # Break-even: CA after tax equals US after tax when fx = implied_fx * (1+t_ca)/(1+t_us)
    breakeven = {f"{ct:g}/{ut:g}": float(primary["implied_fx"] * (1 + ct / 100) / (1 + ut / 100))
                 for ct in CA_TAX.values() for ut in US_TAX.values()}

    # 5. regression audit: d on category and log price, brand-clustered
    df["log_us_c"] = np.log(df["us"]) - np.log(df["us"]).mean()
    X1 = np.column_stack([np.ones(len(df)), df["log_us_c"]])
    reg1 = bs.ols_cluster(d, X1, cl, ["intercept", "log US price (centred)"])
    cats = pd.get_dummies(df["category"], drop_first=False).astype(float)
    cats = cats.drop(columns="Bag")
    X2 = np.column_stack([np.ones(len(df)), cats.to_numpy(), df["log_us_c"]])
    reg2 = bs.ols_cluster(d, X2, cl, ["intercept (Bag)"] + [f"{c} vs Bag" for c in cats.columns] + ["log US price (centred)"])
    bdum = pd.get_dummies(df["brand"], drop_first=True).astype(float)
    X3 = np.column_stack([np.ones(len(df)), bdum.to_numpy(), df["log_us_c"]])
    reg3 = bs.ols_cluster(d, X3, cl, ["intercept"] + [f"brand: {b}" for b in bdum.columns] + ["log US price (centred)"])
    slope3 = reg3[reg3["term"] == "log US price (centred)"].iloc[0]
    regressions = [
        {"model": "d ~ log US price", "terms": reg1.to_dict(orient="records"), **reg1.attrs},
        {"model": "d ~ category + log US price", "terms": reg2.to_dict(orient="records"), **reg2.attrs},
        {"model": "d ~ brand fixed effects + log US price (slope only)", "terms": [slope3.to_dict()], **reg3.attrs,
         "note": "Brand dummies outnumber what 15 clusters can support for inference; only the within-brand price slope is reported."},
    ]

    # 6. outputs
    pd.DataFrame(rob).to_csv(TABLES / "robustness.csv", index=False)
    pd.DataFrame(subsets).to_csv(TABLES / "subsets.csv", index=False)
    brands.to_csv(TABLES / "brand_summary.csv", index=False)
    loo.to_csv(TABLES / "leave_one_brand_out.csv", index=False)
    infl.head(10).to_csv(TABLES / "influential_products.csv", index=False)
    pd.DataFrame(fx_rows).to_csv(TABLES / "fx_scenarios.csv", index=False)
    pd.DataFrame(tax_rows).to_csv(TABLES / "tax_scenarios.csv", index=False)
    for i, r in enumerate([reg1, reg2], 1):
        r.to_csv(TABLES / f"regression_{i}.csv", index=False)

    results = {
        "meta": {"generated_by": "pipeline/run_analysis.py", "collected": collected, "seed": SEED, "bootstrap_reps": BOOT_REPS,
                 "fx_source": "Bank of Canada daily average exchange rate (FXUSDCAD), CAD per USD",
                 "estimand": "Mean over matched products of d = ln(P_CA / (P_US x FX)), list prices before sales tax",
                 "python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
                 "scipy": __import__("scipy").__version__},
        "quality": {k: v for k, v in quality.items() if k not in ("row_issues", "raw_ratio_outliers")} |
                   {"row_issues": len(quality["row_issues"]), "raw_ratio_outliers": len(quality["raw_ratio_outliers"])},
        "primary": primary,
        "wild_bootstrap": wild,
        "robustness": rob,
        "subsets": subsets,
        "leave_one_brand_out": {"min_pct": float(loo["pct"].min()), "max_pct": float(loo["pct"].max()),
                                "min_dropped": loo.loc[loo["pct"].idxmin(), "dropped"],
                                "max_dropped": loo.loc[loo["pct"].idxmax(), "dropped"],
                                "rows": loo.to_dict(orient="records")},
        "product_page_sample": product_page_sample(df),
        "influential_products": infl.head(5).to_dict(orient="records"),
        "brands": brands.to_dict(orient="records"),
        "fx_scenarios": fx_rows,
        "tax_scenarios": tax_rows,
        "breakeven_fx": breakeven,
        "regressions": regressions,
        "distribution": {"min_pct": bs.pct_from_log(d.min()), "max_pct": bs.pct_from_log(d.max()),
                         "median_pct": bs.pct_from_log(float(np.median(d))),
                         "share_cheaper_in_canada": float(np.mean(d < 0)), "n_cheaper": int(np.sum(d < 0)),
                         "n_dearer": int(np.sum(d > 0)), "n_equal": int(np.sum(d == 0))},
    }
    (ROOT / "data" / "results.json").write_text(json.dumps(clean(results), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    import figures
    figures.make_all(df, brands, loo, fx_rows, primary, FIGS)
    import make_report
    make_report.render(clean(results))
    print_summary(results)


def product_page_sample(df: pd.DataFrame) -> dict:
    s = df[~df["listing_price"]]
    top = s["brand"].value_counts().head(4)
    return {"n": int(len(s)), "watch": int((s["category"] == "Watch").sum()), "top4": int(top.sum()),
            "top4_brands": top.index.tolist()}


def clean(o):
    """Make numpy / NaN values JSON-safe."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        # 10 significant digits; rounding to decimal places would turn tiny p-values into 0
        return None if not np.isfinite(o) else float(f"{float(o):.10g}")
    return o


def print_summary(r: dict) -> None:
    p = r["primary"]
    print(f"\nn = {p['n']} products, {p['brands']} brands; FX {p['fx']} ({p['fx_date']})")
    print(f"Primary: mean d = {p['mean_log']:.4f} (SE {p['se']:.4f}), {p['pct']:.2f}% "
          f"[{p['ci_low_pct']:.2f}%, {p['ci_high_pct']:.2f}%], t({p['df']:.0f}) = {p['stat']:.2f}, p = {p['p']:.2g}")
    print(f"Wild cluster bootstrap p = {r['wild_bootstrap']['p']:.3g} ({r['wild_bootstrap']['draws']})")
    for e in r["robustness"]:
        ci = "" if e["ci_low_pct"] is None else f" [{e['ci_low_pct']:.2f}, {e['ci_high_pct']:.2f}]"
        print(f"  {e['label']:<55} n={e['n']:<4} {e['pct']:7.2f}%{ci}  p={e['p'] if e['p'] is None else format(e['p'], '.2g')}")
    for e in r["subsets"]:
        print(f"  subset {e['label']:<25} n={e['n']:<4} G={e['clusters']} {e['pct']:7.2f}% [{e['ci_low_pct']:.2f}, {e['ci_high_pct']:.2f}]")


if __name__ == "__main__":
    main()
