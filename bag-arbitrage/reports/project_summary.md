# Project descriptions

## For an academic CV (projects section)

**Cross-Border Luxury Pricing: US vs Canada** — independent project, 2026
- Built a dataset of official list prices for 165 matched products (handbags, small leather goods, watches) from 15 brands' US and Canadian websites, with source URLs, provenance flags and a validation report.
- Estimated the mean log price difference at a dated Bank of Canada exchange rate with brand-clustered (CR1) inference and a wild cluster bootstrap. Found Canadian list prices 10.2% lower before tax (95% CI −12.0% to −8.3%).
- Ran robustness checks (brand-equal weights, colour-variant collapsing, match-quality and provenance exclusions, leave-one-brand-out, category subsets, clustered regressions) and exchange-rate and tax scenarios.
- Wrote a reproducible Python pipeline (pandas, SciPy, matplotlib; pinned versions, 25 unit tests). One command regenerates every number, figure and the report. Published an interactive site whose in-browser statistics are tested against the pipeline output.

## Short version (one line)

Cross-Border Luxury Pricing (independent, 2026): reproducible analysis of 165 matched US/Canada list prices, with cluster-robust inference and robustness checks; Python, SciPy, JavaScript.

## Statement-of-purpose sentence (adapt as needed)

In an independent project, I compared official US and Canadian list prices for 165 matched luxury products. The project taught me how much clustered data change inference: treating products as independent made the confidence interval about a third as wide as a brand-clustered analysis supports.

Note: describe your own role accurately. If AI tools assisted with code or writing, follow each program's policy on disclosure.
