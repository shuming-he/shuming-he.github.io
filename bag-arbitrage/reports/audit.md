# Audit of the Bag Arbitrage project (13 October 2026)

Scope: the published page `bag-arbitrage/index.html`, the dataset `data/prices.json`, and the pipeline in `pipeline/`, as of commit `6bbc27b` (the version live on GitHub Pages when the audit started). Severity scale: **Critical** (a reported result is wrong or misleading), **High** (inference or reproducibility is materially weakened), **Medium** (a reader could be misled or a check is missing), **Low** (presentation or housekeeping).

Each finding lists the evidence, why it matters, the correction made, and how the correction was verified. Numbers quoted for the corrected analysis come from `data/results.json`, produced by `pipeline/run_analysis.py`.

## Summary

| # | Finding | Severity | Status |
|---|---|---|---|
| A1 | 12 observations had been removed because they lacked a product photo | Critical | Fixed |
| A2 | Headline result was an after-tax scenario, not the observed price comparison | Critical | Fixed |
| A3 | Abstract stated a causal explanation the data cannot support | Critical | Fixed |
| A4 | Inference treated 153 products as independent, ignoring brand clustering | High | Fixed |
| A5 | Exchange rate labelled as the 2 October market rate was rounded and not dated to collection | High | Fixed |
| A6 | Matching quality and price provenance were not reported or tested | High | Fixed |
| A7 | No single reproducible command; README results were typed by hand | High | Fixed |
| A8 | No tests for the statistical code; dependencies not pinned | Medium | Fixed |
| A9 | Colour variants with identical prices counted as separate observations without a sensitivity check | Medium | Fixed (sensitivity analysis) |
| A10 | Three Dior items carried hand-made ids although both product pages show the same official code | Medium | Fixed |
| A11 | Price-tier regression used i.i.d. errors and a scenario-dependent outcome | Medium | Fixed |
| A12 | The research question says handbags but the data include watches and small leather goods | Medium | Documented; category subsets added |
| A13 | US sales-tax rates presented without a source | Medium | Labelled illustrative |
| A14 | One Breitling reference has a canonical-link mismatch on the source page | Low | Flagged, kept |
| A15 | Product images are hot-linked from brand servers; loading was not verified from this environment | Low | Documented |
| A16 | One listed product (Burberry) has no Canadian price | Low | Reported as an exclusion |
| A17 | Root README still called the data an "illustrative prototype dataset" and gave 153 products | Critical | Fixed (follow-up) |
| A18 | `results.json` rounded tiny p-values to 0 | Medium | Fixed (follow-up) |
| A19 | Unit of analysis (listing vs model) and its weighting consequence not stated | Medium | Fixed (follow-up) |

## Findings

### A1. Observations removed for lacking a photo — Critical
- **Evidence.** Commit `6bbc27b` replaced 12 Coach and Dior products that had no official photo with other products. The removed rows are recoverable from commit `d4ea863` (`git show d4ea863:bag-arbitrage/pipeline/collected_prices.csv`).
- **Why it matters.** Removing valid price observations for a display reason is a silent sample change. Photo availability could be related to the product line and so to price.
- **Correction.** The 24 price rows and 12 product rows were restored. The sample is now 165 products. Photos affect display order only. The analysis has no photo filter, and `has_image` is recorded as a column.
- **Verification.** `reports/data_quality.md` shows 165 matched pairs, of which 12 have no photo. `run_analysis.py` uses every matched pair.

### A2. Headline was a tax scenario — Critical
- **Evidence.** The abstract and the "Canada vs US" stat box reported the after-tax comparison at 7% US tax and 13% HST (`index.html`, `renderAbstract` and `renderStats`).
- **Why it matters.** Taxes are assumptions about a hypothetical buyer, not observed data. They shift every product by the same constant, ln(1.13/1.07) ≈ 0.055. That roughly halves the reported gap, so the headline depended on chosen inputs.
- **Correction.** The primary estimand is now the pre-tax list-price comparison at a dated Bank of Canada rate. Tax settings appear only in a section labelled as a scenario.
- **Verification.** The primary estimate (−10.2%, 95% CI −12.0% to −8.3%) and the Ontario/7% scenario (−5.1%) are both read from `results.json`.

### A3. Causal claim — Critical
- **Evidence.** The abstract said: "The reason is that brands price Canada at about C$… per US dollar."
- **Why it matters.** The implied rate is an algebraic restatement of the same price ratios, not an explanation. Nothing in the design identifies why prices differ.
- **Correction.** The sentence was removed. The page and report describe the implied rate as an equivalent way to express the gap. The Discussion lists possible explanations explicitly as untested.
- **Verification.** The claim audit (`reports/claim_audit.md`) found no remaining causal wording.

### A4. Products treated as independent — High
- **Evidence.** `pairedTest`, `fxStats` and `ols` used n − 1 or n − 2 degrees of freedom with the i.i.d. standard error.
- **Why it matters.** One company sets all of a brand's prices, so they are correlated. With 15 brands, the naive 95% interval is about 31% as wide as the brand-clustered interval. A naive p-value of 5 × 10⁻⁷⁴ overstates the evidence.
- **Correction.**
  - Primary inference now uses a CR1 brand-clustered SE with t(G − 1) critical values.
  - Two cluster bootstraps are reported: a wild cluster bootstrap-t (all 2¹⁵ sign patterns) and a pairs cluster bootstrap.
  - The naive test is kept only as a labelled comparison.
  - The page computes the same clustered interval live.
- **Verification.**
  - Unit tests compare the CR1 SE with a hand computation and with the OLS-intercept route. They also check the reduction to HC1 with one observation per cluster.
  - A Node script checks that the page's JavaScript reproduces `results.json`.

### A5. Exchange-rate date and value — High
- **Evidence.** The page default was 1.42, described as "the market rate on 2 October 2026". The Bank of Canada FXUSDCAD rate that day was 1.4246, and prices were collected on 13 October.
- **Why it matters.** The rate enters every observation. Using 1.42 instead of the 9 October rate (1.4271) moves the pre-tax estimate by about 0.45 percentage points, and the source was not given.
- **Correction.** `pipeline/fx_rates.csv` stores the Bank of Canada daily rates from 28 September to 9 October 2026, with their source. The primary rate is the last business day before collection: 9 October, 1.4271. 12 October was Thanksgiving. Sensitivity is reported over all stored dates and a hypothetical range.
- **Verification.** `primary_fx()` selects the date from the file, and `results.json` records `fx_date`.

### A6. Matching quality not reported — High
- **Evidence.**
  - Notes in `collected_prices.csv` show that 104 pairs use a price read from a category listing and 11 were shown as sold out.
  - Tory Burch and most Dior listings publish no style code, so those products were matched by name.
  - None of this was summarised or tested.
- **Why it matters.** Mismatched products would add noise or bias that readers could not assess.
- **Correction.** `validate.py` adds flags (`name_match`, `identifier_check`, `listing_price`, `sold_out`, `repeat_price_pair`). It runs format checks on every row and writes `reports/data_quality.md`. Every flag gets a sensitivity analysis, and no row is dropped because of a flag.
- **Verification.** The format checks report 0 failures. Excluding uncertain matches gives −10.1%. Using product-page prices only gives −8.9%. Both are in `reports/tables/robustness.csv`.

### A7. No single reproducible command — High
- **Evidence.** Results came from the JavaScript on the page and a separate `analysis.py`. README figures (−4.4%, t = −13.58) were typed by hand and were already stale.
- **Correction.** `python run_analysis.py` runs validation, the dataset build, all analyses, tables, figures, `results.json` and the report. The report is rendered from `results.json`, with no hand-typed results.
- **Verification.**
  - The command was run end to end in this environment.
  - Running it twice gives identical `results.json`: the bootstrap is seeded and the wild bootstrap is enumerated.

### A8. Tests and dependencies — Medium
- **Evidence.** The only tests covered price-text parsing, and `requirements.txt` used `>=` ranges.
- **Correction.** `tests/test_stats.py` adds 19 tests on synthetic data with known answers: price maths, tax shift, input validation, each estimator, bootstrap reproducibility, leave-one-out, OLS recovery and validation logic. `requirements.txt` now pins the exact versions used.
- **Verification.** `python -m unittest discover tests` ran 25 tests, all passing.

### A9. Identical-price variants — Medium
- **Evidence.**
  - 17 rows repeat an earlier row's brand and exact (US, CA) price pair, for example colourways of one Coach card case.
  - Some are different models at the same price point, such as the two Omega models at US$7,400 / C$9,700.
- **Correction.** A sensitivity analysis keeps one row per (brand, US, CA) pair: n = 148, −10.0%. Clustering by brand already limits the effect on inference.

### A10. Dior identifiers — Medium
- **Evidence.** Three Dior products had slug ids such as `book-tote-medium-blue-oblique`, although both source URLs contain the same official code (for example `M1324CZBB_M928`).
- **Correction.** The style column now holds the official codes, so these pairs count as code-matched.

### A11. Price-tier regression — Medium
- **Evidence.** `ols()` regressed the after-tax percentage gap on log10 US price and took the p-value from Pearson r with n − 2 df.
- **Correction.** The report regresses d (pre-tax log difference) on centred log price, then adds category and brand fixed effects, all with brand-clustered SEs.
- **Verification.** The slope is 0.004 (p = 0.52), and within brands it is −0.004 (p = 0.34). The page's scatter is labelled as descriptive.

### A12. Scope of the question — Medium
- **Evidence.** Of the 165 matched products, 87 are bags, 60 are watches and 18 are small leather goods.
- **Correction.** The question is stated for "luxury goods sold on official brand sites", with bag, watch and small-leather-goods subsets reported.

### A13. US tax rates — Medium
- **Evidence.** The slider hint used NYC 8.875% and Oregon 0% without citation.
- **Correction.** US rates are labelled illustrative. Canadian rates are CRA GST/HST rates, with a note that provincial sales taxes are not included.

### A14. Breitling identifier — Low
- **Evidence.** The RB0137241G1R1 page's canonical link ends in G1P1.
- **Correction.** Flagged in `review_flags.csv` and kept. It is excluded in the uncertain-match sensitivity analysis.

### A15. Hot-linked images — Low
- **Evidence.** Images load from brand CDNs. This environment's proxy blocks those hosts, so loading could not be verified here.
- **Correction.** The page uses `referrerpolicy="no-referrer"` and falls back to initials, and image credit is given. Image display is not part of the analysis.

### A16. Burberry — Low
- **Evidence.** One product has a US price but no Canadian price (Burberry's Canadian site showed no price).
- **Correction.** Listed as an exclusion in `reports/data_quality.md`. Burberry does not appear in the brand count.

### A17. Root README contradicted the page — Critical
- **Evidence.** The repository's top-level `README.md` said "Bag Arbitrage currently displays an illustrative prototype dataset" and described 153 products, a paired t-test and OLS. That text dated from before real prices were collected; the page and report describe 165 real, sourced prices. The author found this on review after the first publish.
- **Why it matters.** A reviewer cannot tell which description is true, which undermines the credibility of every number.
- **Correction.** The README now states that the data are hand-collected official list prices, gives the counts, the provenance check and the reproduce command, and matches the page and report.
- **Verification.** A search of all text files for "prototype" and the old counts finds only this audit's historical references.

### A18. p-values rounded to zero — Medium
- **Evidence.** `clean()` in `run_analysis.py` rounded floats to 10 decimal places, so the naive t-test p (5.4 × 10⁻⁷⁴) and the Wilcoxon p (7.9 × 10⁻²⁹) were written to `results.json` as `0.0`.
- **Correction.** Values are now kept to 10 significant digits. The page and report show p < 0.001, or scientific notation for the wild bootstrap p.
- **Verification.** A new unit test checks that a p-value of 5.4 × 10⁻⁷⁴ survives `clean()`; 26 tests pass.

### A19. Unit of analysis — Medium
- **Evidence.** For fashion brands a style code identifies a colourway, so colours of one model are separate rows; 17 rows repeat a brand and exact price pair.
- **Correction.** The report and page define the unit as a product listing and explain the weighting consequence. The model-level approximation (n = 148) is reported next to it, together with its own limitation: it also merges different models at the same price point.

## What was checked and found correct
- In all 124 price rows read from a product page, the URL contains the same style code as the CSV row (`validate.py`, `code_not_in_url` check).
- The page's statistics are computed in the browser from `prices.json`, not hard-coded. With products treated as independent, they matched SciPy before the changes.
- Every price has a source URL, a currency and a collection date. No wrong-currency rows were found.
- The raw CAD/USD ratio lies between 1.163 and 1.421, and no pair is outside 1.5 × IQR.
