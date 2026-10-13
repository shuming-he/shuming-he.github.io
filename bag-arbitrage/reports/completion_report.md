# Completion report: research-grade upgrade of Bag Arbitrage

Date: 13 October 2026.

**Status: done locally, not published.** Nothing has been committed, pushed or deployed. The live site still shows commit `6bbc27b`. Publishing waits for the author's approval.

## A. Audit
`reports/audit.md` lists 16 findings: 3 critical, 4 high, 6 medium and 3 low. Each has evidence, the correction made and how the correction was verified. The critical findings were:
- 12 observations had been removed for lacking a photo. They are now restored.
- The headline was an after-tax scenario.
- The abstract made a causal claim.

## B. Research question, population, estimand
These are in report Section 1 and in the page's "Research question" section.
- **Estimand.** Mean of d = ln(P_CA / (X·P_US)), using pre-tax list prices.
- **Exchange rate.** X is the Bank of Canada rate for 2026-10-09, which is 1.4271.
- **Inference.** Brand-clustered.

## C. Data dictionary and data quality
- `reports/data_dictionary.md` describes every file and field.
- `reports/data_quality.md` is generated from the data and gives:
  - 331 price rows, 166 products and 165 matched pairs.
  - One exclusion: a Burberry product with no Canadian price.
  - 0 format failures.
  - Flag counts: 30 name matches, 104 listing-page prices, 11 sold out, and 17 repeated price pairs.

## D. Primary result
Produced by `run_analysis.py` and stored in `data/results.json`.

| Statistic | Value |
|---|---|
| Sample | n = 165 products, 15 brands |
| Mean d | −0.1071 (clustered SE 0.0096; SD 0.0419) |
| 95% CI for mean d | −0.1277 to −0.0865 |
| t | −11.17 (df = 14) |
| p | < 0.001 |
| Wild cluster bootstrap p | 6.1 × 10⁻⁵, the minimum attainable with 15 clusters |
| Geometric ratio | 0.898 |
| Percentage difference | −10.2% (95% CI −12.0% to −8.3%) |
| Implied exchange rate | C$1.282 per US$ |

**Plain language.** Before tax, at the market exchange rate, these products' Canadian list prices were about 10% lower than their US list prices.

## E. Robustness
- **Point estimates** stay between −10.2% and −8.9%:
  - brand-equal weighting: −10.0%
  - collapsing repeated price pairs: −10.0%
  - excluding uncertain matches: −10.1%
  - product-page prices only: −8.9% (watch-heavy subsample)
  - excluding sold-out items: −9.9%
- **Leave one brand out:** −10.4% to −9.6%.
- **Wilcoxon median:** −9.1%.
- **Naive i.i.d. interval:** about 31% as wide as the clustered interval. It is shown only as a comparison.
- **Exchange-rate scenarios:** over the two weeks of Bank of Canada rates, the estimate runs from −9.5% to −10.2%.
- **Tax scenarios:** shown as a grid. The gap reverses only when Canadian tax is far above US tax, for example ON 13% against 0% US.

## F. Regression audit
All standard errors are brand-clustered.

| Model | Coefficient | Clustered p |
|---|---|---|
| d on log US price | slope 0.004 | 0.52 |
| Same, with brand fixed effects (within-brand slope) | −0.004 | 0.34 |
| d on category and log price: small leather goods vs bags | −0.038 | 0.006 |

The small-leather-goods contrast comes from only 3 brands.

## G. Reproducible pipeline
`python run_analysis.py` produces:
- `data/results.json`
- `data/matched_pairs.csv`
- `data/prices.json`
- tables in `reports/tables/*.csv`
- figures in `figures/*.svg`
- `reports/report.md` and `report.html`

Dependencies are pinned in `requirements.txt`. Running the command twice gave byte-identical `results.json` and figures. I checked this.

## H. Tests
- **Unit tests.** `python -m unittest discover tests` ran 26 tests and all passed: 20 new tests (statistics on synthetic data, validation, output) plus 6 existing parser tests.
- **Page check.** `tests/site_consistency.js` showed that the page's JavaScript reproduces the primary estimate from `results.json` exactly (mean, SE, t, p, CI and implied rate) on desktop (1366 px) and mobile (375 px). It found no console errors and no horizontal overflow.

## I. Website
The project page was rebuilt in this order:
1. Hero, titled "Cross-Border Luxury Pricing", with links to Key findings, Code and Report.
2. Research question.
3. Key findings, read from `results.json`.
4. Statistical evidence, with robustness and subset tables.
5. Interactive scenario explorer, labelled as not the primary result. Its defaults reproduce the primary estimate.
6. Methods.
7. Reproducibility.
8. Limitations, L1 to L7 plus future work.
9. Author, described as an independent project.

The animations you asked for earlier are kept, and they still respect reduced-motion settings. Brands with any product lacking a photo (Coach, Dior) now appear last. On the home page, the project card now uses the new title and the new counts.

## J. Report
- `reports/report.md` and `report.html` are generated entirely from `results.json`.
- **References:**
  - Engel & Rogers (1996), Cameron, Gelbach & Miller (2008), Cameron & Miller (2015) and Cavallo, Neiman & Rigobon (2014) were checked online.
  - Efron & Tibshirani (1993) and Wilcoxon (1945) are standard references but were not re-checked in this session. Check them before citing.

## K. Claim audit and accessibility
- **Claim audit.** `reports/claim_audit.md` gives the source for each claim. No causal claims remain.
- **Accessibility.** axe-core (WCAG 2 A/AA) found 0 violations on the home page, the project page and the report. This was after I raised the muted text colour to meet 4.5:1 contrast, made the code block focusable, and added `lang` to the report.

## L. CV description and remaining limitations
- **CV description.** Short and long versions are in `reports/project_summary.md`.
- **Remaining limitations:**
  - It is a one-day snapshot.
  - The brands and products were chosen, not sampled.
  - The data are list prices, not what buyers actually pay.
  - There are only 15 clusters.
  - 30 matches rely on product names.
  - US tax rates are illustrative.
  - Product images are hot-linked from brand sites and were not checked from this environment.
- The project does not guarantee admission anywhere.
- If AI tools helped with code or writing, disclose this as each program requires.

## Not done or not verified
- Not committed, pushed or deployed. This needs the author's approval.
- Image loading on the live site was not checked, because brand image hosts are blocked from this environment.
- No PDF of the report was produced. The HTML version is available instead.

## Follow-up after the author's review (13 October 2026)
- Root README rewritten: it had still described the data as an illustrative prototype with 153 products (audit A17).
- `results.json` no longer rounds tiny p-values to 0 (A18), and a test now covers this.
- Unit of analysis defined as a product listing, with the model-level comparison explained (A19).
- The report explains what the agreement between inference methods does and does not show.
- `validate.py` checks that every product-page price URL contains its style code: 124 of 124 do.
