# Market Value vs On-Field Performance

Live report: https://shuming-he.github.io/football-value/

**Question.** How much of a footballer's Transfermarkt market value do league statistics explain? Which players are valued well above or below the prediction, and do the Premier League, LaLiga and Bundesliga reward the same statistics?

**Data.** [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) (CC0), downloaded 14 October 2026 by the "Football data" GitHub Action. [`data/raw/PROVENANCE.md`](data/raw/PROVENANCE.md) records the archive hash and the rows kept. I did not scrape Transfermarkt, whose terms do not allow automated collection.

**Method.** OLS of log market value (end of 2025/26) on minutes share, goals, assists and yellow cards per 90, club points per game, league, position, age spline and contract length. Standard errors clustered by club, a wild cluster bootstrap for the league comparison, out-of-sample R² with clubs held out, and robustness checks. All numbers are in [`data/results.json`](data/results.json).

## Reproduce

```bash
cd pipeline
pip install -r requirements.txt
python -m unittest discover tests
python run_analysis.py     # builds data/player_seasons.csv, data/results.json, data/residuals.csv, report/tables/
python make_report.py      # writes ../index.qmd from results.json
quarto render ../index.qmd
```

The "Football report" GitHub Action runs these steps on every change and fails if the recomputed results differ from the committed ones.

## Files

| Path | What it is |
|---|---|
| `pipeline/fetch_data.py` | Downloads the public dataset and keeps big-five league data from July 2023 (run in GitHub Actions) |
| `pipeline/build_dataset.py` | One row per player and league season; lists every exclusion with a reason |
| `pipeline/run_analysis.py` | Models, cross-validation, league comparison, robustness, persistence |
| `pipeline/make_report.py` | Writes the Quarto report text from `results.json` |
| `pipeline/tests/` | Unit tests on synthetic data with known answers |
| `data/raw/` | Filtered source files and provenance |
| `data/player_seasons.csv` | Analysis table for all five leagues and three seasons, with `in_sample` and `exclusion` |
| `data/residuals.csv` | Primary sample with out-of-sample predictions and residuals |
| `data/exclusions.csv` | Counts of excluded players by season, league and reason |
| `report/` | Quarto theme, site bar, tables |
| `vendor/` | Observable Plot 0.6.11, Inputs 0.10.6, d3 7.8.5 and htl 0.3.1, served from the repo instead of a CDN |

## Data dictionary (`player_seasons.csv`)

| Column | Meaning |
|---|---|
| `season` | Season start year (2025 = 2025/26) |
| `league` | Transfermarkt competition code of the league where the player played most minutes |
| `club` | Club where the player played most league minutes that season |
| `minutes`, `apps`, `starts` | League minutes, appearances and starts that season |
| `minutes_share` | Minutes ÷ (league matches per team × 90) |
| `goals_p90`, `assists_p90`, `yellow_p90` | Per 90 league minutes |
| `team_ppg` | Club's league points per game that season |
| `age` | Age on 30 June after the season |
| `contract_years` | Years from 30 June after the season to the contract end date in the source (current dates) |
| `value_end` | Latest market value dated 1 May–30 June after the season, in euros |
| `value_any` | Latest market value on or before 30 June after the season (robustness only) |
| `in_sample`, `exclusion` | Whether the row meets the sample rules, and if not, why |

The analysis is descriptive: residuals show how far a value sits from what the statistics predict, not whether it is wrong.
