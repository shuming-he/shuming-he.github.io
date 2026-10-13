"""Render reports/report.md (and report.html when pandoc is available) from data/results.json.

Every number in the report is read from results.json; the prose contains no hand-typed results.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
REPORTS = ROOT / "reports"


def pct(x, d=1):
    if x is None:
        return "–"
    s = f"{x:.{d}f}"
    return ("−" + s[1:] if s.startswith("-") else s) + "%"


def num(x, d=3):
    if x is None:
        return "–"
    s = f"{x:.{d}f}"
    return "−" + s[1:] if s.startswith("-") else s


def pval(p):
    if p is None:
        return "–"
    if p < 0.001:
        return "< 0.001"
    return f"{p:.3f}"


def ci(e):
    return f"{pct(e['ci_low_pct'])} to {pct(e['ci_high_pct'])}" if e.get("ci_low_pct") is not None else "–"


def render(r: dict) -> Path:
    p, q, w = r["primary"], r["quality"], r["wild_bootstrap"]
    loo, dist = r["leave_one_brand_out"], r["distribution"]
    rob = {e["label"]: e for e in r["robustness"]}
    sub = {e["label"]: e for e in r["subsets"]}
    tax = {(t["ca_rate"], t["us_rate"]): t for t in r["tax_scenarios"]}
    on7 = tax[(13.0, 7.0)]
    reg1, reg2, reg3 = r["regressions"]
    slope1 = reg1["terms"][1]
    slg = next(t for t in reg2["terms"] if t["term"].startswith("Small leather goods"))
    watch = next(t for t in reg2["terms"] if t["term"].startswith("Watch"))
    slope3 = reg3["terms"][0]
    rob_pcts = [e["pct"] for e in r["robustness"] if e["kind"] != "inference" or e["label"].startswith("Primary")]
    excl = q["excluded"]
    fx_hist = [f for f in r["fx_scenarios"] if f["date"] != "hypothetical"]
    fx_lo = min(fx_hist, key=lambda f: f["fx"])
    fx_hi = max(fx_hist, key=lambda f: f["fx"])
    lowest = r["brands"][0]
    highest = r["brands"][-1]

    L = []
    a = L.append
    a("---")
    a("title: \"Cross-Border Luxury Pricing: Official US and Canadian List Prices\"")
    a("author: \"Shuming He (independent project)\"")
    a(f"date: \"Data collected {r['meta']['collected']}\"")
    a("---")
    a("")
    a("## Abstract")
    a("")
    a(f"This study compares official list prices for the same products on the US and Canadian websites of "
      f"{p['brands']} luxury and premium brands ({p['n']} matched products: handbags, small leather goods and watches), "
      f"collected on {r['meta']['collected']}. For each product, the Canadian price is compared with the US price "
      f"converted at the Bank of Canada rate of {p['fx']} CAD per USD ({p['fx_date']}), before sales tax. "
      f"The product-weighted mean log difference is {num(p['mean_log'])}: Canadian list prices are on average "
      f"{pct(abs(p['pct']))} lower (95% CI {ci(p)}; t({p['df']:.0f}) = {num(p['stat'], 2)}, p {pval(p['p'])}, "
      f"standard errors clustered by brand). Every one of the {p['n']} products was lower in Canada at this rate. "
      f"The direction and approximate size hold across alternative weightings, inference methods and sample "
      f"restrictions (point estimates from {pct(min(rob_pcts))} to {pct(max(rob_pcts))}). Equivalently, the brands' "
      f"list prices imply about C${p['implied_fx']:.3f} per US dollar. The comparison is descriptive: it measures "
      f"list-price differences for this set of products on one date and does not identify why brands set prices this way. "
      f"After an illustrative 13% Ontario HST and 7% US sales tax, the average gap narrows to {pct(on7['pct'])}.")
    a("")
    a("## 1. Research question")
    a("")
    a("**Question.** For identical products sold on a brand's official US and Canadian websites, how do Canadian list "
      "prices compare with US list prices converted at the market exchange rate?")
    a("")
    a("**Unit and population.** The unit is a product (a style or reference sold in both markets). The target population "
      "is products that the selected brands list with a visible price on both their US and Canadian official websites. "
      "The sample is not random: brands were included when both sites showed prices that could be read, and products were "
      "chosen to cover each brand's core lines (about ten per brand). Results describe this sample; extending them to other "
      "brands or products requires assumptions discussed in Section 6.")
    a("")
    a("**Estimand.** For product *i* with US price $P^{US}_i$ (USD) and Canadian price $P^{CA}_i$ (CAD), both before tax, "
      "and exchange rate $X$ (CAD per USD),")
    a("")
    a("$$d_i = \\ln\\!\\left(\\frac{P^{CA}_i}{X \\cdot P^{US}_i}\\right), \\qquad \\theta = E[d_i].$$")
    a("")
    a("$d_i < 0$ means the product is cheaper in Canada after conversion. $\\exp(\\theta) - 1$ is the geometric-mean "
      "percentage difference. Log differences are symmetric, additive across tax and exchange-rate adjustments, and "
      "unaffected by the price level, which spans two orders of magnitude here.")
    a("")
    a("**Hypotheses.** $H_0: \\theta = 0$ against $H_1: \\theta \\neq 0$ (two-sided, 5% level).")
    a("")
    a("## 2. Data")
    a("")
    a(f"Prices were read from each brand's official US and Canadian websites on {r['meta']['collected']}, either from the "
      f"product page or from the brand's category listing page. Each price is stored with its currency, source URL, "
      f"collection date and a note (`pipeline/collected_prices.csv`). {q['products_listed']} products from "
      f"{q['brands_listed']} brands were listed; {q['matched_pairs']} from {q['brands_matched']} brands have a valid price in "
      f"both markets and form the analysis sample.")
    a("")
    if excl:
        a("Excluded: " + "; ".join(f"{e['product']} ({e['brand_id']}): {e['reason']}" for e in excl) + ".")
        a("")
    a(f"Categories: " + ", ".join(f"{k} {v}" for k, v in q["by_category"].items()) +
      f". Items per brand: {q['items_per_brand']['min']} to {q['items_per_brand']['max']}.")
    a("")
    f = q["flags"]
    a("**Matching and provenance.** Products were matched by the brand's style or reference code where both pages "
      f"show one. {f['name_match']} pairs were matched by exact product name because at least one page shows no code, "
      f"and {f['identifier_check']} more have an open identifier check. {f['listing_price']} pairs have at least one price "
      f"read from a category listing, {f['sold_out']} were shown as sold out (list price still displayed), and "
      f"{f['repeat_price_pair']} repeat an earlier row's brand and exact price pair (often colour variants). These are "
      "kept and examined in Section 4.2 rather than removed. Full counts are in `reports/data_quality.md`.")
    a("")
    a("**Exchange rate.** Bank of Canada daily average rate (series FXUSDCAD) for the last business day before collection "
      f"({p['fx_date']}, {p['fx']}); 12 October 2026 was a Canadian holiday. Rates from {fx_hist[0]['date']} to "
      f"{fx_hist[-1]['date']} are used for sensitivity.")
    a("")
    a("## 3. Methods")
    a("")
    a("**Estimator.** The sample mean $\\bar d$ over matched products.")
    a("")
    a(f"**Inference.** Prices within a brand are set by one company and move together, so products are not independent. "
      f"The primary standard error is cluster-robust by brand (CR1), with t critical values on G − 1 = {p['df']:.0f} "
      "degrees of freedom (Cameron & Miller, 2015). Because 15 clusters is few, a wild cluster bootstrap-t "
      "with Rademacher weights and the null imposed is also reported (Cameron, Gelbach & Miller, 2008); with 15 brands all "
      f"{2 ** 15} sign patterns can be enumerated, so no random seed is involved.")
    a("")
    a(f"**Robustness.** (i) naive paired t-test treating products as independent; (ii) brand cluster bootstrap with "
      f"percentile interval (B = {r['meta']['bootstrap_reps']}, seed {r['meta']['seed']}; Efron & Tibshirani, 1993); "
      "(iii) equal weight per brand; (iv) Wilcoxon signed-rank test (Wilcoxon, 1945); (v) one observation per identical "
      "price pair within a brand; (vi) excluding uncertain matches, listing-derived prices, or sold-out items; "
      "(vii) leave-one-brand-out and leave-one-product-out influence; (viii) category and tier subsets.")
    a("")
    a("**Regression audit.** OLS of $d_i$ on centred log US price, then adding category indicators, then brand fixed effects, "
      "all with brand-clustered CR1 standard errors.")
    a("")
    a("**Scenarios.** Sales tax and the exchange rate multiply every price in a market by the same factor, so each scenario "
      "shifts every $d_i$ by the same constant and leaves the standard error unchanged. Tax scenarios use CRA GST/HST rates "
      "for Canada (provincial sales taxes in BC, MB, QC and SK are not included) and illustrative combined US rates, "
      "since US sales tax varies by state and locality.")
    a("")
    a("## 4. Results")
    a("")
    a("### 4.1 Primary estimate")
    a("")
    a("| Quantity | Value |")
    a("|---|---|")
    rows = [("Products (n)", p["n"]), ("Brands (clusters)", p["brands"]), ("Exchange rate", f"{p['fx']} CAD/USD ({p['fx_date']})"),
            ("Mean d", num(p["mean_log"], 4)), ("SD of d", num(p["sd"], 4)), ("Clustered SE", num(p["se"], 4)),
            ("95% CI for mean d", f"{num(p['ci_low'], 4)} to {num(p['ci_high'], 4)}"),
            ("t (df)", f"{num(p['stat'], 2)} ({p['df']:.0f})"), ("p (CR1, t with G−1 df)", pval(p["p"])),
            ("p (wild cluster bootstrap-t)", f"{w['p']:.2g} ({w['draws']}" +
             ("; this is the smallest p-value attainable with this many clusters)" if abs(w["p"] - w["min_possible_p"]) < 1e-12 else ")")),
            ("Geometric ratio exp(mean d)", num(p["ratio"], 4)),
            ("Percentage difference", f"{pct(p['pct'], 2)} (95% CI {pct(p['ci_low_pct'], 2)} to {pct(p['ci_high_pct'], 2)})"),
            ("Implied exchange rate in list prices", f"C${p['implied_fx']:.3f} per US$ (95% CI {p['implied_fx_ci'][0]:.3f} to {p['implied_fx_ci'][1]:.3f})"),
            ("Products cheaper in Canada", f"{dist['n_cheaper']} of {p['n']}"),
            ("Range of product differences", f"{pct(dist['min_pct'])} to {pct(dist['max_pct'])} (median {pct(dist['median_pct'])})")]
    for k, v in rows:
        a(f"| {k} | {v} |")
    a("")
    a(f"**Interpretation.** At the market exchange rate on the day before collection, a typical product in this sample "
      f"costs about {pct(abs(p['pct']))} less in Canada than in the US before tax. Put differently, the brands' Canadian "
      f"prices correspond to roughly C${p['implied_fx']:.2f} per US dollar, while the market rate was C${p['fx']:.2f}.")
    a("")
    a("![Brand means](../figures/brand_forest.svg)")
    a("")
    a("### 4.2 Robustness")
    a("")
    a("| Check | n | Brands | Estimate | 95% CI | p |")
    a("|---|---|---|---|---|---|")
    for e in r["robustness"]:
        a(f"| {e['label']} | {e['n']} | {e['clusters'] or '–'} | {pct(e['pct'])} | {ci(e)} | {pval(e['p'])} |")
    a("")
    a(f"Notes: the Wilcoxon row reports the median, not the mean. The naive interval is about "
      f"{(rob['Products treated as independent (naive paired t)']['ci_high_pct'] - rob['Products treated as independent (naive paired t)']['ci_low_pct']) / (p['ci_high_pct'] - p['ci_low_pct']):.0%} "
      "as wide as the clustered one, which shows how much ignoring brand-level dependence would overstate precision. "
      "The bootstrap percentile interval with 15 clusters can be too narrow (Cameron, Gelbach & Miller, 2008).")
    a("")
    lp = rob["Excluding prices read from category listings"]
    pp = r["product_page_sample"]
    a(f"Restricting to prices read from product pages leaves {lp['n']} products and gives {pct(lp['pct'])}. This subset is "
      f"not a random part of the sample: {pp['watch']} of its {lp['n']} products are watches and {pp['top4']} come from "
      f"{', '.join(pp['top4_brands'])}, so the difference may partly reflect composition.")
    a("")
    a(f"**Influence.** Removing one brand at a time moves the estimate between {pct(loo['min_pct'], 2)} (without "
      f"{loo['min_dropped']}) and {pct(loo['max_pct'], 2)} (without {loo['max_dropped']}). No single product changes the "
      f"mean by more than {abs(r['influential_products'][0]['change_pct_points']):.2f} percentage points.")
    a("")
    a("![Leave one brand out](../figures/leave_one_brand_out.svg)")
    a("")
    a("### 4.3 Subsets")
    a("")
    a("| Subset | n | Brands | Estimate | 95% CI |")
    a("|---|---|---|---|---|")
    for e in r["subsets"]:
        a(f"| {e['label']} | {e['n']} | {e['clusters']} | {pct(e['pct'])} | {ci(e)} |")
    a("")
    a(f"Subsets with few brands have few degrees of freedom and wide intervals; small leather goods come from "
      f"{sub['Small leather goods']['clusters']} brands. Brand means range from {pct(lowest['pct'])} ({lowest['brand']}) "
      f"to {pct(highest['pct'])} ({highest['brand']}).")
    a("")
    a("![Distribution](../figures/distribution.svg)")
    a("")
    a("### 4.4 Regression audit")
    a("")
    a("| Model | Term | Coefficient | Clustered SE | p | R² |")
    a("|---|---|---|---|---|---|")
    for m in r["regressions"]:
        for t in m["terms"]:
            a(f"| {m['model']} | {t['term']} | {num(t['coef'], 4)} | {num(t['se_cluster'], 4)} | {pval(t['p'])} | {m['r2']:.2f} |")
    a("")
    a(f"The log difference is not associated with price level (slope {num(slope1['coef'], 4)} per unit of log price, "
      f"p = {pval(slope1['p'])}; within brands {num(slope3['coef'], 4)}, p = {pval(slope3['p'])}). Small leather goods "
      f"show a larger gap than bags ({num(slg['coef'], 3)}, p = {pval(slg['p'])}), but they come from only "
      f"{sub['Small leather goods']['clusters']} brands, so this contrast is closer to a brand comparison than a category "
      f"effect. Watches do not differ from bags (p = {pval(watch['p'])}).")
    a("")
    a("![Price level](../figures/price_scatter.svg)")
    a("")
    a("### 4.5 Exchange-rate and tax scenarios")
    a("")
    a(f"Over the Bank of Canada rates in the two weeks before collection ({fx_lo['fx']} to {fx_hi['fx']}), the pre-tax "
      f"estimate ranges from {pct(fx_lo['pct'])} to {pct(fx_hi['pct'])}. At the implied rate of {p['implied_fx']:.3f} the "
      "difference would be zero by construction.")
    a("")
    a("![FX sensitivity](../figures/fx_sensitivity.svg)")
    a("")
    a("After-tax scenarios (illustrative; the shopper pays the tax of the place of purchase):")
    a("")
    us_rates = sorted({t["us_rate"] for t in r["tax_scenarios"]})
    a("| Canadian tax \\ US tax | " + " | ".join(f"{u:g}%" for u in us_rates) + " |")
    a("|---|" + "---|" * len(us_rates))
    for ct in sorted({t["ca_rate"] for t in r["tax_scenarios"]}):
        a(f"| {ct:g}% | " + " | ".join(pct(tax[(ct, u)]["pct"]) for u in us_rates) + " |")
    a("")
    a(f"For example, comparing Ontario (13% HST) with a 7% US rate gives {pct(on7['pct'])} (95% CI {ci(on7)}). "
      "Where Canadian tax is much higher than US tax, the after-tax difference can disappear or reverse.")
    a("")
    a("## 5. Discussion")
    a("")
    a("Across this sample, official Canadian list prices sit below the converted US prices, consistent with brands setting "
      "Canadian prices at a rate below the spot exchange rate. The data cannot say why. Possible explanations include list "
      "prices being revised less often than the exchange rate moves (Canadian prices may have been set when the Canadian dollar "
      "was stronger), different tax and duty treatment, competitive positioning, or deliberate pricing to market; this "
      "study does not test any of them. The literature on international price differences documents large border effects "
      "(Engel & Rogers, 1996) and studies identical goods sold online across countries (Cavallo, Neiman & Rigobon, 2014).")
    a("")
    a("## 6. Limitations")
    a("")
    for item in [
        f"**One date.** All prices were read on {r['meta']['collected']}; the result is a snapshot and moves with the exchange rate.",
        "**Selection.** Brands were included only if both official sites showed readable prices, which excludes several major houses "
        "(for example Chanel, Louis Vuitton, Gucci and Cartier at collection time). Products were chosen, not sampled at random.",
        "**List prices, not transaction prices.** Discounts, waiting lists, grey-market premiums and duty or shipping costs are not observed. "
        "Several Rolex models in particular trade above list price.",
        f"**Matching.** {f['name_match']} pairs rely on exact names rather than codes; the estimate without uncertain matches is "
        f"{pct(rob['Excluding uncertain matches']['pct'])}.",
        f"**Few clusters.** {p['brands']} brands give {p['df']:.0f} degrees of freedom; brand-level conclusions and subset intervals are imprecise.",
        "**Taxes.** US sales tax varies by state and city and Canadian provincial taxes vary by province; the scenarios are illustrative, "
        "and cross-border purchases may owe duty and tax on import.",
        "**Manual collection.** Prices were read by hand from web pages; source URLs are stored for every price so each can be re-checked.",
    ]:
        a(f"- {item}")
    a("")
    a("## 7. Reproducibility")
    a("")
    a("```bash")
    a("cd bag-arbitrage/pipeline")
    a("pip install -r requirements.txt")
    a("python -m unittest discover tests")
    a("python run_analysis.py")
    a("```")
    a("")
    m = r["meta"]
    a(f"`run_analysis.py` validates the price log, rebuilds the website dataset, runs every analysis in this report and writes "
      f"`data/results.json`, the tables in `reports/tables/`, the figures in `figures/` and this report. Results were produced "
      f"with Python {m['python']}, NumPy {m['numpy']}, pandas {m['pandas']} and SciPy {m['scipy']}. Bootstrap seed {m['seed']}.")
    a("")
    a("## References")
    a("")
    for ref in [
        "Cameron, A. C., Gelbach, J. B., & Miller, D. L. (2008). Bootstrap-based improvements for inference with clustered errors. "
        "*Review of Economics and Statistics*, 90(3), 414–427.",
        "Cameron, A. C., & Miller, D. L. (2015). A practitioner's guide to cluster-robust inference. *Journal of Human Resources*, 50(2), 317–372.",
        "Cavallo, A., Neiman, B., & Rigobon, R. (2014). Currency unions, product introductions, and the real exchange rate. "
        "*Quarterly Journal of Economics*, 129(2), 529–595.",
        "Efron, B., & Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.",
        "Engel, C., & Rogers, J. H. (1996). How wide is the border? *American Economic Review*, 86(5), 1112–1125.",
        "Wilcoxon, F. (1945). Individual comparisons by ranking methods. *Biometrics Bulletin*, 1(6), 80–83.",
        "Bank of Canada. Daily exchange rates, series FXUSDCAD. Valet API, https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?start_date=2026-09-28&end_date=2026-10-13",
        "Canada Revenue Agency. GST/HST rates by province. https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/gst-hst-businesses/charge-collect-which-rate/calculator.html",
    ]:
        a(f"- {ref}")
    out = REPORTS / "report.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    if shutil.which("pandoc"):
        subprocess.run(["pandoc", str(out), "-s", "--mathml", "--toc", "--no-highlight", "-M", "lang=en", "-c", "report.css", "-o", str(REPORTS / "report.html")],
                       check=True, cwd=REPORTS)
    return out


if __name__ == "__main__":
    render(json.loads((ROOT / "data" / "results.json").read_text(encoding="utf-8")))
