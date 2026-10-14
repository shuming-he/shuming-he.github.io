"""Write ../index.qmd (the Quarto report) from data/results.json.

Every number in the text comes from results.json; nothing is typed by hand.
Interactive charts are Observable JS cells that read the published CSV/JSON
files in the browser, so rendering needs Quarto only (no Python kernel).
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R = json.loads((ROOT / "data" / "results.json").read_text())
EXCL = pd.read_csv(ROOT / "data" / "exclusions.csv")
REPO = "https://github.com/shuming-he/shuming-he.github.io/tree/main/football-value"


def pct(x, d=0, sign=True):
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    return s.replace("-", "−") + "%"


def num(x, d=2):
    return f"{x:.{d}f}".replace("-", "−")


def pval(p):
    if p is None:
        return "n/a"
    if p < 0.001:
        m, e = f"{p:.1e}".split("e")
        return f"{m} × 10<sup>{int(e)}</sup>".replace("-", "−")
    return f"{p:.3f}"


def eur(x):
    return f"€{x / 1e6:,.1f}m" if x >= 1e6 else f"€{x / 1e3:,.0f}k"


f, s, meta = R["fit"], R["sample"], R["meta"]
coef = {c["term"]: c for c in R["coefficients"]}
lg = {e["league"]: e for e in R["league_effects"]}
eq, wb = R["league_slopes"]["equal_slopes_test"], R["league_slopes"]["equal_slopes_wild_bootstrap"]
per = R["persistence"]
rob = R["robustness"]
slopes = pd.DataFrame(R["league_slopes"]["by_league"])
excl_now = EXCL[(EXCL.season_label == meta["season"]) & EXCL.league.isin(["GB1", "ES1", "L1"])].groupby("exclusion").players.sum()

coef_rows = "\n".join(
    f"| {c['label']} | {c['unit_label']} | {pct(c['pct'], 1)} | {pct(c['pct_low'], 1)} to {pct(c['pct_high'], 1)} | {pval(c['p'])} |"
    for c in R["coefficients"])
rob_rows = "\n".join(
    f"| {r['check']} | {r['n']} | {num(r['r2']) if r['r2'] is not None else '–'} | "
    + " | ".join(num(r.get(t)) if r.get(t) is not None else "absorbed" for t in ["minutes_share", "goals_p90", "assists_p90", "yellow_p90", "team_ppg"])
    + " |" for r in rob)
excl_rows = "\n".join(f"| {k} | {v} |" for k, v in excl_now.items())
slope_rows = []
for term, label in [("goals_p90", "Goals per 90"), ("assists_p90", "Assists per 90"), ("minutes_share", "Minutes share"), ("team_ppg", "Club points per game")]:
    cells = []
    for l in ["GB1", "ES1", "L1"]:
        r = slopes[(slopes.league == l) & (slopes.term == term)].iloc[0]
        cells.append(f"{num(r.coef)} ({num(r.se)})")
    slope_rows.append(f"| {label} | " + " | ".join(cells) + " |")
slope_rows = "\n".join(slope_rows)
age = {a["age"]: a["pct_vs_25"] for a in R["age_curve"]}
n_by = s["by_league"]

qmd = f"""---
title: "Market Value vs On-Field Performance"
subtitle: "How much of a footballer's Transfermarkt value do league statistics explain? Premier League, LaLiga and Bundesliga, {meta['season']}"
author: "Shuming He"
date: "2026-10-14"
format:
  html:
    theme: [darkly, report/theme.scss]
    toc: true
    toc-depth: 2
    toc-location: left
    smooth-scroll: true
    anchor-sections: true
    code-tools: false
    include-before-body: report/nav.html
    link-external-newwindow: true
execute:
  echo: false
lang: en
---

::: {{.lede}}
Across **{s['n']} outfield players** in the {meta['season']} Premier League, LaLiga and Bundesliga, a regression on league statistics, age, position, league and contract length explains **{f['cv_r2']['full'] * 100:.0f}%** of the variation in log market value for clubs it has not seen. League statistics alone explain {f['cv_r2']['field_no_league'] * 100:.0f}%. Adding them to age, position, league and contract raises the out-of-sample R² from {f['cv_r2']['controls_only']:.2f} to {f['cv_r2']['full']:.2f}.
:::

::: {{.keystats}}
[**{s['n']}**<br>players]{{.ks}}
[**{s['clusters']}**<br>clubs]{{.ks}}
[**{f['cv_r2']['full']:.2f}**<br>out-of-sample R²]{{.ks}}
[**{pct(lg['ES1']['pct'])}**<br>LaLiga vs Premier League, same stats]{{.ks}}
:::

## Question

Transfermarkt publishes a market value for every professional footballer. Those values are set by its community and editors, not by a formula, and they are widely quoted in transfer reporting. This project asks three things:

1. How much of a player's market value can be explained by what he does on the pitch in league matches?
2. Which players are valued well above or below what those statistics predict?
3. Do the Premier League, LaLiga and Bundesliga reward the same statistics in the same way?

The analysis is descriptive. A player whose value is above the prediction is not shown to be "overvalued": his value may reflect things the statistics here do not measure, such as defensive work, passing, injuries, earlier seasons, international reputation or commercial appeal.

## Data

- **Source.** [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets), a public dataset built from Transfermarkt pages and released under CC0. It was downloaded on 14 October 2026; [PROVENANCE.md]({REPO}/data/raw/PROVENANCE.md) records the file's SHA-256 hash and the rows kept.
- **Why not scrape?** Transfermarkt's terms do not allow automated collection. FBref, the usual source for detailed match statistics, stopped publishing Opta's advanced data in 2026, so passing and defensive statistics were not available from it either.
- **Unit.** One outfield player in one league season. Statistics come from that season's league matches only. A player who changed club within the league is counted once, at the club where he played most minutes.
- **Outcome.** The latest market value Transfermarkt published between 1 May and 30 June 2026, after the season ended. The values range from {eur(s['value_min_eur'])} to {eur(s['value_max_eur'])}, with median {eur(s['value_median_eur'])}. The model uses the log of value, because values span three orders of magnitude.
- **Sample.** At least {meta['min_minutes']} league minutes, goalkeepers excluded. That leaves {n_by['Premier League']} Premier League, {n_by['LaLiga']} LaLiga and {n_by['Bundesliga']} Bundesliga players from {s['clusters']} clubs.

Players who appeared in the three leagues but are not in the sample:

| Reason | Players |
|---|---|
{excl_rows}

## Method

The primary model is an ordinary least squares regression of log market value on:

- **League statistics:** share of the season's league minutes played, goals per 90 minutes, assists per 90 minutes, yellow cards per 90 minutes, and the club's points per game.
- **Other factors:** league, position group (seven groups), age (a natural cubic spline with 4 degrees of freedom), years left on the contract and a flag for a missing contract date.

Players at the same club share a coach, a team style and a market profile, so their errors are correlated. Standard errors are therefore **clustered by club** ({s['clusters']} clusters, *t* with {s['clusters'] - 1} degrees of freedom). For the main league comparison I also report a wild cluster bootstrap with {wb['reps']} draws, which is more reliable when a test uses many restrictions relative to the number of clusters.

To answer "how much is explained" without rewarding overfitting, R² is also computed **out of sample**. Clubs are split into 10 folds, and each club's players are predicted by a model that never saw that club.

## How much do statistics explain?

| Model | In-sample R² | Out-of-sample R² |
|---|---|---|
| League statistics only | – | {f['cv_r2']['field_no_league']:.2f} |
| League statistics + league | {f['r2_field_only']:.2f} | {f['cv_r2']['field_only']:.2f} |
| Age, position, league, contract only | {f['r2_controls_only']:.2f} | {f['cv_r2']['controls_only']:.2f} |
| All of the above | {f['r2']:.2f} | {f['cv_r2']['full']:.2f} |

The league statistics are jointly significant (*F*({f['field_block_test']['df_num']}, {f['field_block_test']['df_den']:.0f}) = {f['field_block_test']['F']:.1f}, *p* = {pval(f['field_block_test']['p'])}). Splitting the out-of-sample R² of the full model fairly between the two groups of variables (a two-group Shapley decomposition) gives league statistics **{f['shapley_field_share'] * 100:.0f}%** of the explained variation and the other factors the rest. After the model, the typical prediction error is a factor of about {2.718281828 ** f['residual_sd']:.2f} in either direction (residual SD {f['residual_sd']:.2f} in logs).

### What each statistic is associated with

Effects are percentage differences in market value for the stated increase, holding the other variables fixed, with 95% confidence intervals from club-clustered standard errors.

| Variable | Increase | Effect on value | 95% CI | *p* |
|---|---|---|---|---|
{coef_rows}

Age matters a great deal. For an otherwise typical player, the model's value at 21 is {pct(age[21])} relative to 25, at 30 it is {pct(age[30])}, and at 33 it is {pct(age[33])}.

```{{ojs}}
results = FileAttachment("data/results.json").json()
Plot.plot({{
  marginLeft: 210, height: 230, x: {{label: "Effect on market value (%) with 95% CI", grid: true}}, y: {{label: null}},
  marks: [
    Plot.ruleX([0], {{stroke: "#555"}}),
    Plot.ruleY(results.coefficients.filter(d => d.term !== "no_contract"), {{y: d => `${{d.label}} (${{d.unit_label}})`, x1: "pct_low", x2: "pct_high", stroke: "#8c7cf2", strokeWidth: 2}}),
    Plot.dot(results.coefficients.filter(d => d.term !== "no_contract"), {{y: d => `${{d.label}} (${{d.unit_label}})`, x: "pct", fill: "#d9d4ff", r: 5, tip: true}})
  ]
}})
```

## Do the leagues value players differently?

**In level, yes, strongly.** For the same statistics, age, position and contract, a LaLiga player's value is {pct(lg['ES1']['pct'])} (95% CI {pct(100 * (2.718281828 ** lg['ES1']['ci_low'] - 1))} to {pct(100 * (2.718281828 ** lg['ES1']['ci_high'] - 1))}) and a Bundesliga player's {pct(lg['L1']['pct'])} (95% CI {pct(100 * (2.718281828 ** lg['L1']['ci_low'] - 1))} to {pct(100 * (2.718281828 ** lg['L1']['ci_high'] - 1))}) compared with a Premier League player. Part of this is the Premier League's revenue, and part may be differences in opposition strength that per-90 numbers do not adjust for.

**In what is rewarded, there is moderate evidence of differences.** Letting all five statistics have their own slope in each league and testing that the slopes are equal gives *F*({eq['df_num']}, {eq['df_den']:.0f}) = {eq['F']:.2f}, *p* = {pval(eq['p'])} with clustered standard errors, and *p* = {pval(wb['p'])} with the wild cluster bootstrap. The bootstrap p-value is much weaker, so the evidence is real but not strong. Separate regressions by league (coefficients on log value, clustered SE in brackets):

| Statistic | Premier League | LaLiga | Bundesliga |
|---|---|---|---|
{slope_rows}

In the Premier League, value rises less steeply with club results, minutes, goals and assists than in the other two leagues. That pattern is consistent with Premier League values being high even at weaker clubs, but this analysis does not test the reason. Each league regression has only 18–20 clubs, so these individual slopes are imprecise.

```{{ojs}}
Plot.plot({{
  marginLeft: 150, height: 300, x: {{label: "Coefficient on log value (95% CI)", grid: true}}, y: {{label: null}},
  fy: {{label: null}}, color: {{legend: true, domain: ["Premier League", "LaLiga", "Bundesliga"], range: ["#1a9dbb", "#e8b04a", "#e35f3d"]}},
  marks: [
    Plot.ruleX([0], {{stroke: "#555"}}),
    Plot.ruleY(results.league_slopes.by_league.filter(d => d.term !== "yellow_p90"), {{fy: "label", y: "league_name", x1: "ci_low", x2: "ci_high", stroke: "league_name", strokeWidth: 2}}),
    Plot.dot(results.league_slopes.by_league.filter(d => d.term !== "yellow_p90"), {{fy: "label", y: "league_name", x: "coef", fill: "league_name", r: 4.5, tip: true}})
  ]
}})
```

## Above and below what the statistics predict

Each player's prediction comes from the out-of-sample model, so his own club was not used to fit it. The ratio is actual value ÷ predicted value: 2.0 means valued at twice the prediction, 0.5 at half.

Two cautions before reading the list. First, a typical player is already a factor of {2.718281828 ** f['residual_sd']:.2f} away from the prediction, so only large ratios stand out. Second, a large gap often points to something the model leaves out: age at the extremes (one season says little about a 38-year-old's value), defensive and passing work these statistics do not record, or a club whose results were unusual that season.

```{{ojs}}
players = FileAttachment("data/residuals.csv").csv({{typed: true}})
viewof league = Inputs.select(["All leagues", "Premier League", "LaLiga", "Bundesliga"], {{label: "League"}})
viewof position = Inputs.select(["All positions", "Centre-back", "Full-back", "Defensive mid", "Central mid", "Attacking mid", "Winger", "Forward"], {{label: "Position"}})
viewof minValue = Inputs.select(new Map([["Any value", 0], ["€5m or more", 5e6], ["€20m or more", 2e7], ["€50m or more", 5e7]]), {{label: "Market value"}})
viewof q = Inputs.search(players, {{placeholder: "Search players or clubs", columns: ["name", "club"]}})
filtered = q.filter(d => (league === "All leagues" || d.league === league) && (position === "All positions" || d.position_group === position) && d.value_end >= minValue)
```

```{{ojs}}
Plot.plot({{
  height: 420, grid: true,
  x: {{type: "log", label: "Predicted value (€, out of sample) →"}}, y: {{type: "log", label: "↑ Actual value (€)"}},
  color: {{legend: true, domain: ["Premier League", "LaLiga", "Bundesliga"], range: ["#1a9dbb", "#e8b04a", "#e35f3d"]}},
  marks: [
    Plot.line([[1e4, 1e4], [4e8, 4e8]], {{stroke: "#777", strokeDasharray: "4 4"}}),
    Plot.dot(filtered, {{x: "predicted_value", y: "value_end", fill: "league", r: 3, fillOpacity: 0.75,
      channels: {{Player: "name", Club: "club", Age: d => d.age.toFixed(1), Ratio: d => Math.exp(d.residual).toFixed(2)}},
      tip: {{format: {{x: d => "€" + (d / 1e6).toFixed(1) + "m", y: d => "€" + (d / 1e6).toFixed(1) + "m"}}}}}})
  ]
}})
```

```{{ojs}}
Inputs.table(filtered.map(d => ({{...d, ratio: Math.exp(d.residual)}})), {{
  columns: ["name", "club", "league", "position_group", "age", "minutes", "goals", "assists", "value_end", "predicted_value", "ratio"],
  header: {{name: "Player", club: "Club", league: "League", position_group: "Position", age: "Age", minutes: "Minutes", goals: "Goals", assists: "Assists",
           value_end: "Value", predicted_value: "Predicted", ratio: "Ratio"}},
  format: {{age: d => d.toFixed(1), value_end: d => "€" + (d / 1e6).toFixed(1) + "m", predicted_value: d => "€" + (d / 1e6).toFixed(1) + "m", ratio: d => d.toFixed(2)}},
  sort: "ratio", reverse: true, rows: 15
}})
```

### Do these gaps last?

Using the same model in earlier seasons (without contract length, because the source only has current contract dates), the gap in one season is correlated with the same player's gap the next season: *r* = {per[0]['corr']:.2f} from {per[0]['from']} to {per[0]['to']} (n = {per[0]['n']}) and *r* = {per[1]['corr']:.2f} from {per[1]['from']} to {per[1]['to']} (n = {per[1]['n']}). So much of the gap is a stable feature of the player that these statistics do not capture, not a one-season accident.

Players valued above their prediction also tended to see their value grow more slowly the next year: each 1.0 of log gap went with {num(per[0]['change_on_resid'])} (SE {num(per[0]['change_on_resid_se'])}) and {num(per[1]['change_on_resid'])} (SE {num(per[1]['change_on_resid_se'])}) in the next year's log change, controlling for age. This is consistent with partial correction, but regression toward the mean would produce the same pattern even if values contained no error at all, so it is not evidence that the market was wrong.

## Robustness

Each row re-estimates the primary model with one change. Columns show the coefficients on log value; the clustered *p*-values are in [the table file]({REPO}/report/tables/robustness.csv).

| Check | n | R² | Minutes share | Goals /90 | Assists /90 | Yellows /90 | Club pts/game |
|---|---|---|---|---|---|---|---|
{rob_rows}

The signs and rough sizes hold in every version: minutes, goals, assists and club results are all positively associated with value, and yellow cards are never significantly different from zero. "Totals instead of per-90 rates" uses season totals, so its goal, assist and card coefficients are on a different scale and are omitted here. In the club fixed-effects version, club points per game is absorbed because it is the same for every player at a club.

## Limitations

- **Missing statistics.** Without passing, defensive or expected-goals data, the model cannot see much of what defenders and midfielders do. Their residuals mostly measure that gap.
- **Market value is an estimate.** Transfermarkt values are community judgements. Research has found them to be informative about actual transfer fees (Herm, Callsen-Bracker and Kreis 2014; Müller, Simons and Weinmann 2017), but they are not prices.
- **One season, current positions.** Position and contract dates in the source are the latest ones, not necessarily those during the season.
- **Association, not cause.** Better players play more and score more, and also join better clubs. The coefficients describe how values line up with statistics, not what would happen to a value if a player scored more.
- **Selection.** Players with fewer than {meta['min_minutes']} minutes are excluded, so the results describe regular players.

## Reproduce

All code, data and this report are in the [repository]({REPO}). From `football-value/pipeline/`:

```bash
pip install -r requirements.txt
python -m unittest discover tests
python run_analysis.py      # dataset, models, results.json, tables
python make_report.py       # writes ../index.qmd
quarto render ../index.qmd
```

The GitHub Action that publishes this page runs the tests and the analysis, and fails if the recomputed `results.json` differs from the committed one.

## References

- Cameron, A. C., Gelbach, J. B. and Miller, D. L. (2008). Bootstrap-based improvements for inference with clustered errors. *Review of Economics and Statistics*, 90(3), 414–427.
- Herm, S., Callsen-Bracker, H.-M. and Kreis, H. (2014). When the crowd evaluates soccer players' market values: Accuracy and evaluation attributes of an online community. *Sport Management Review*, 17(4), 484–492.
- Müller, O., Simons, A. and Weinmann, M. (2017). Beyond crowd judgments: Data-driven estimation of market value in association football. *European Journal of Operational Research*, 263(2), 611–624.
"""

(ROOT / "index.qmd").write_text(qmd)
print("wrote", ROOT / "index.qmd")
