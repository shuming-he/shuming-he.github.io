# Claim audit

Every factual or statistical claim on the project page and in the report, with where it comes from. Wording check: the page and report make no claim about why prices differ (searched for 'because', 'the reason', 'due to', 'cause'; the only hits are about timing as a limitation and are worded as possibilities). Results are described as descriptive differences in list prices for this sample.

| Claim | Evidence | Status |
|---|---|---|
| 165 matched products from 15 brands | results.json `primary.n`, `primary.brands`; data_quality.md | Verified (computed) |
| Collected 13 October 2026 | `collected` column of collected_prices.csv (all 331 rows) | Verified (data) |
| Canadian list prices -10.2% vs US before tax, 95% CI -12.0% to -8.3% | results.json `primary`; page JS reproduces it (tests/site_consistency.js) | Verified (computed) |
| t(14) = -11.17, p < 0.001, brand-clustered | results.json `primary` | Verified (computed) |
| Wild cluster bootstrap p = 6.1e-05, smallest attainable with 15 brands | results.json `wild_bootstrap` (`p` equals `min_possible_p`) | Verified (computed) |
| All 165 products lower in Canada at 1.4271 | results.json `distribution` | Verified (computed) |
| Estimates range -10.2% to -8.9% across robustness checks | results.json `robustness` (excluding rows that only change inference, which share the primary mean) | Verified (computed) |
| Implied rate C$1.282 per US$ | results.json `primary.implied_fx` | Verified (computed); an algebraic restatement, not an explanation |
| No association with price level | results.json `regressions[0]` slope p = 0.52; within-brand p = 0.34 | Verified (computed); 'no evidence of association', not proof of none |
| After-tax (13% HST, 7% US) gap -5.1% | results.json `tax_scenarios` | Verified (computed); labelled as a scenario |
| Bank of Canada rate 1.4271 on 9 October 2026 | fx_rates.csv, from Bank of Canada Valet API FXUSDCAD (fetched during this work) | Verified (source) |
| CRA GST/HST rates 5/13/14/15% | CRA GST/HST rate page, checked during this work | Verified (source) |
| US sales-tax levels | Not sourced | Labelled illustrative |
| Hudson's Bay closed; Saks Canada disallows crawlers; Farfetch/NAP show retailer prices; Chrono24 mostly resale | Checked during data collection on 13 October 2026 (Hudson's Bay site redirected; Saks robots.txt) | Verified at collection time |
| Brands excluded because no online prices or blocked access | Collection notes (team memory and Limitations L2) | Observed at collection time; may change |
| References (Engel & Rogers 1996; Cameron, Gelbach & Miller 2008; Cameron & Miller 2015; Cavallo, Neiman & Rigobon 2014) | Bibliographic details checked online during this work | Verified |
| References (Efron & Tibshirani 1993; Wilcoxon 1945) | Standard references; details not re-checked online in this session | Should be checked before submission |
| Author: first-year Mathematics & Statistics student, University of Toronto | Stated by the author | Author-provided |
| Independent project | Stated by the author; no supervisor, course or institution is claimed | Author-provided |

Removed in this revision: the abstract sentence 'The reason is that brands price Canada at about C$… per US dollar' (causal), the after-tax headline, the label '1.42 … was the market rate on 2 October 2026' (rounded; the Bank of Canada rate was 1.4246), and hand-typed README results.
