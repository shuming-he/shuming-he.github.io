"""The single command: dataset -> models -> robustness -> results.json, tables and chart data.

Primary sample: outfield players with at least 900 league minutes in the
2025/26 Premier League, LaLiga and Bundesliga, valued at the end of that season.
Outcome: log of the Transfermarkt market value. Standard errors are clustered by
club, with t(G-1) reference distributions.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

import build_dataset

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TABLES = ROOT / "report" / "tables"
LEAGUES = ["GB1", "ES1", "L1"]
LEAGUE_NAMES = {"GB1": "Premier League", "ES1": "LaLiga", "L1": "Bundesliga", "IT1": "Serie A", "FR1": "Ligue 1"}
PRIMARY_SEASON = 2025
SEED = 20261014

FIELD = ["minutes_share", "goals_p90", "assists_p90", "yellow_p90", "team_ppg"]
# effects are reported for these increments, which are about one standard deviation or less
UNITS = {"minutes_share": (0.10, "+10 percentage points"), "goals_p90": (0.10, "+0.10"), "assists_p90": (0.10, "+0.10"),
         "yellow_p90": (0.10, "+0.10"), "team_ppg": (0.50, "+0.5 points"), "contract_years": (1.0, "+1 year")}
FIELD_LABELS = {
    "minutes_share": "Share of league minutes played",
    "goals_p90": "Goals per 90 minutes",
    "assists_p90": "Assists per 90 minutes",
    "yellow_p90": "Yellow cards per 90 minutes",
    "team_ppg": "Club points per game",
    "contract_years": "Contract years remaining",
    "no_contract": "Contract end date missing or passed",
}
AGE = "cr(age, df=4, constraints='center')"
CONTROLS = f"C(league, Treatment('GB1')) + C(position_group, Treatment('Centre-back')) + {AGE}"
CONTRACT = "contract_years + no_contract"
FULL = f"log_value ~ {' + '.join(FIELD)} + {CONTROLS} + {CONTRACT}"
CONTROLS_ONLY = f"log_value ~ {CONTROLS} + {CONTRACT}"
FIELD_ONLY = f"log_value ~ {' + '.join(FIELD)} + C(league, Treatment('GB1'))"


def prepare(df):
    df = df.copy()
    df["no_contract"] = (~df.contract_known.astype(bool)).astype(int)
    df.loc[df.no_contract == 1, "contract_years"] = 0.0
    return df


def sample(df, season=PRIMARY_SEASON, leagues=LEAGUES, min_minutes=900, value="value_end"):
    s = df[(df.season == season) & df.league.isin(leagues) & (df.minutes >= min_minutes)
           & (df.position != "Goalkeeper") & df.position_group.notna() & df.age.notna() & df[value].notna()].copy()
    s["log_value"] = np.log(s[value])
    return s.reset_index(drop=True)


def fit(formula, d, cluster="club_id"):
    return smf.ols(formula, d).fit(cov_type="cluster", cov_kwds={"groups": d[cluster]}, use_t=True)


def coef_table(m, names):
    rows = []
    for n in names:
        if n not in m.params:
            continue
        b, se, p = m.params[n], m.bse[n], m.pvalues[n]
        lo, hi = m.conf_int().loc[n]
        u, ulabel = UNITS.get(n, (1.0, "+1"))
        rows.append({"term": n, "label": FIELD_LABELS.get(n, n), "coef": b, "se": se, "t": m.tvalues[n], "p": p,
                     "ci_low": lo, "ci_high": hi, "unit": u, "unit_label": ulabel,
                     "pct": 100 * (np.exp(b * u) - 1), "pct_low": 100 * (np.exp(lo * u) - 1), "pct_high": 100 * (np.exp(hi * u) - 1)})
    return rows


def cv_r2(formula, d, folds=10, seed=SEED):
    """Out-of-sample R^2 with whole clubs held out together, plus out-of-fold predictions."""
    rng = np.random.default_rng(seed)
    clubs = d.club_id.unique()
    fold_of = dict(zip(rng.permutation(clubs), np.arange(len(clubs)) % folds))
    f = d.club_id.map(fold_of)
    pred = pd.Series(np.nan, index=d.index)
    for k in range(folds):
        train, test = d[f != k], d[f == k]
        m = smf.ols(formula, train).fit()
        pred[test.index] = m.predict(test)
    resid = d.log_value - pred
    return 1 - (resid ** 2).sum() / ((d.log_value - d.log_value.mean()) ** 2).sum(), pred


def age_curve(m, d):
    """Predicted log value by age for a typical player, relative to age 25."""
    ages = np.arange(18, 37)
    ref = d.iloc[[0]].copy()
    for c in FIELD + ["contract_years"]:
        ref[c] = d[c].median()
    ref["no_contract"], ref["league"], ref["position_group"] = 0, "GB1", "Central mid"
    grid = pd.concat([ref.assign(age=a) for a in ages])
    pred = m.predict(grid).to_numpy()
    base = pred[list(ages).index(25)]
    return [{"age": int(a), "pct_vs_25": 100 * (np.exp(p - base) - 1)} for a, p in zip(ages, pred)]


def wald(m, terms):
    r = m.wald_test(" , ".join(f"{t} = 0" for t in terms), scalar=True, use_f=True)
    return {"F": float(r.statistic), "df_num": int(r.df_num), "df_den": float(r.df_denom), "p": float(r.pvalue)}


def league_slopes(d):
    """Separate on-field slopes by league; test that they are equal."""
    inter = " + ".join(f"{v}:C(league, Treatment('GB1'))" for v in FIELD)
    m = fit(f"{FULL} + {inter}", d)
    terms = [t for t in m.params.index if ":" in t]
    by_league = []
    for lg in LEAGUES:
        sub = d[d.league == lg]
        ml = fit(f"log_value ~ {' + '.join(FIELD)} + C(position_group, Treatment('Centre-back')) + {AGE} + {CONTRACT}", sub)
        for row in coef_table(ml, FIELD):
            row.update(league=lg, league_name=LEAGUE_NAMES[lg], n=int(ml.nobs), clusters=int(sub.club_id.nunique()), r2=ml.rsquared)
            by_league.append(row)
    return {"equal_slopes_test": wald(m, terms), "equal_slopes_wild_bootstrap": wild_wald(d, FULL, f"{FULL} + {inter}"),
            "by_league": by_league}


def wild_wald(d, restricted, unrestricted, reps=1999, seed=SEED):
    """Restricted wild cluster bootstrap (Rademacher weights by club) for a joint test."""
    mr = smf.ols(restricted, d).fit()
    mu = fit(unrestricted, d)
    terms = [t for t in mu.params.index if t not in mr.params.index]
    observed = wald(mu, terms)["F"]
    rng = np.random.default_rng(seed)
    clubs = d.club_id.unique()
    pos = d.club_id.map({c: i for i, c in enumerate(clubs)}).to_numpy()
    exceed = 0
    for _ in range(reps):
        w = rng.choice([-1.0, 1.0], size=len(clubs))[pos]
        boot = d.assign(log_value=mr.fittedvalues + mr.resid * w)
        exceed += wald(fit(unrestricted, boot), terms)["F"] >= observed
    return {"F": observed, "reps": reps, "p": (exceed + 1) / (reps + 1)}


def robustness(df):
    out = []

    def add(label, d, formula=FULL, note=""):
        m = fit(formula, d)
        row = {"check": label, "n": int(m.nobs), "clusters": int(d.club_id.nunique()), "r2": m.rsquared, "note": note}
        for t in FIELD:
            if t in m.params:
                row[t] = m.params[t]
                row[t + "_p"] = m.pvalues[t]
        row["field_block"] = wald(m, [t for t in FIELD if t in m.params])
        out.append(row)

    base = sample(df)
    add("Primary", base)
    add("At least 450 minutes", sample(df, min_minutes=450))
    add("At least 1800 minutes", sample(df, min_minutes=1800))
    add("Latest value on or before 30 June, any date", sample(df, value="value_any"), note="adds players whose last valuation was earlier in the season")
    add("Without contract length", base, FULL.replace(f" + {CONTRACT}", ""))
    add("Quadratic in age instead of a spline", base, FULL.replace(AGE, "age + I(age**2)"))
    add("Club fixed effects", base, FULL.replace("team_ppg + ", "").replace("C(league, Treatment('GB1')) + ", "") + " + C(club_id)",
        note="compares players within the same club; club points per game is absorbed")
    add("Totals instead of per-90 rates", base, FULL.replace("goals_p90", "goals").replace("assists_p90", "assists").replace("yellow_p90", "yellow"),
        note="goals, assists and yellow cards as season totals")
    add("Five leagues (adds Serie A, Ligue 1)", sample(df, leagues=LEAGUES + ["IT1", "FR1"]),
        FULL.replace("C(league, Treatment('GB1'))", "C(league, Treatment('GB1'))"))
    for s, lbl in [(2024, "2024/25 season"), (2023, "2023/24 season")]:
        add(f"{lbl}, without contract length", sample(df, season=s), FULL.replace(f" + {CONTRACT}", ""),
            note="contract dates in the source are current ones, so they are left out for past seasons")
    # median regression: no clustered SE, coefficients only
    q = smf.quantreg(FULL, base).fit(q=0.5)
    out.append({"check": "Median (quantile) regression", "n": int(q.nobs), "clusters": int(base.club_id.nunique()), "r2": None,
                "note": "coefficients only; p-values are not clustered", **{t: q.params[t] for t in FIELD},
                **{t + "_p": q.pvalues[t] for t in FIELD}, "field_block": None})
    return out


def persistence(df):
    """Do players valued above their stats one season stay there, and does their value change differently next year?"""
    formula = FULL.replace(f" + {CONTRACT}", "")
    rows = []
    for s in [2023, 2024]:
        a = sample(df, season=s)
        b = sample(df, season=s + 1)
        ra = a.assign(resid=fit(formula, a).resid)[["player_id", "resid", "log_value", "age"]]
        rb = b.assign(resid_next=fit(formula, b).resid)[["player_id", "resid_next", "log_value"]].rename(columns={"log_value": "log_value_next"})
        m = ra.merge(rb, on="player_id")
        m["change"] = m.log_value_next - m.log_value
        r, p = stats.pearsonr(m.resid, m.resid_next)
        reg = smf.ols(f"change ~ resid + {AGE}", m).fit(cov_type="HC3")
        rows.append({"from": build_dataset.SEASONS[s], "to": build_dataset.SEASONS[s + 1], "n": len(m), "corr": r, "corr_p": p,
                     "change_on_resid": reg.params["resid"], "change_on_resid_se": reg.bse["resid"], "change_on_resid_p": reg.pvalues["resid"]})
    return rows


def clean(x):
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(x) else float(f"{float(x):.10g}")
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def main():
    df = prepare(build_dataset.build())
    d = sample(df)
    m = fit(FULL, d)
    m_controls, m_field = fit(CONTROLS_ONLY, d), fit(FIELD_ONLY, d)
    cv = {}
    preds = {}
    for k, f in [("full", FULL), ("controls_only", CONTROLS_ONLY), ("field_only", FIELD_ONLY)]:
        cv[k], preds[k] = cv_r2(f, d)

    cv["field_no_league"], _ = cv_r2(f"log_value ~ {' + '.join(FIELD)}", d)
    shapley_field = 0.5 * ((cv["full"] - cv["controls_only"]) + (cv["field_no_league"] - 0.0))
    d["predicted_value"] = np.exp(preds["full"])
    d["residual"] = d.log_value - preds["full"]
    d["residual_in_sample"] = m.resid
    d["ratio"] = np.exp(d.residual)
    sd = float(d.residual.std(ddof=1))

    league_terms = [t for t in m.params.index if t.startswith("C(league")]
    league_effects = [{"league": t.split("T.")[1].rstrip("]"), "coef": m.params[t], "p": m.pvalues[t],
                      "ci_low": m.conf_int().loc[t, 0], "ci_high": m.conf_int().loc[t, 1], "pct": 100 * (np.exp(m.params[t]) - 1)}
                     for t in league_terms]
    for e in league_effects:
        e["league_name"] = LEAGUE_NAMES[e["league"]]

    results = {
        "meta": {
            "title": "Market Value vs On-Field Performance in Top-League European Football",
            "season": build_dataset.SEASONS[PRIMARY_SEASON], "leagues": [LEAGUE_NAMES[l] for l in LEAGUES],
            "min_minutes": 900, "value_window": "latest Transfermarkt valuation dated 1 May-30 June 2026",
            "source": "transfermarkt-datasets (CC0), downloaded 2026-10-14", "cluster": "club", "seed": SEED,
            "formula": FULL,
        },
        "sample": {"n": int(m.nobs), "clusters": int(d.club_id.nunique()),
                   "by_league": d.groupby("league").size().rename(index=LEAGUE_NAMES).to_dict(),
                   "by_position": d.groupby("position_group").size().to_dict(),
                   "value_median_eur": float(d.value_end.median()), "value_min_eur": float(d.value_end.min()), "value_max_eur": float(d.value_end.max())},
        "fit": {"r2": m.rsquared, "adj_r2": m.rsquared_adj, "r2_controls_only": m_controls.rsquared, "r2_field_only": m_field.rsquared,
                "cv_r2": cv, "cv_r2_gain_from_field": cv["full"] - cv["controls_only"],
                "shapley_field_share": shapley_field / cv["full"], "residual_sd": sd,
                "field_block_test": wald(m, FIELD)},
        "coefficients": coef_table(m, FIELD + ["contract_years", "no_contract"]),
        "age_curve": age_curve(m, d),
        "position_effects": [{"term": t, "coef": m.params[t], "p": m.pvalues[t], "pct": 100 * (np.exp(m.params[t]) - 1)}
                             for t in m.params.index if t.startswith("C(position")],
        "league_effects": league_effects,
        "league_slopes": league_slopes(d),
        "robustness": robustness(df),
        "persistence": persistence(df),
    }
    (DATA / "results.json").write_text(json.dumps(clean(results), indent=1, ensure_ascii=False) + "\n")

    TABLES.mkdir(parents=True, exist_ok=True)
    out = d[["player_id", "name", "club", "league", "position_group", "age", "minutes", "goals", "assists", "team_ppg",
             "contract_years", "no_contract", "value_end", "value_date", "predicted_value", "residual", "residual_in_sample", "url"]].copy()
    out["league"] = out.league.map(LEAGUE_NAMES)
    out.sort_values("residual", ascending=False).to_csv(DATA / "residuals.csv", index=False, float_format="%.6g")
    pd.DataFrame(results["robustness"]).drop(columns=["field_block"]).to_csv(TABLES / "robustness.csv", index=False, float_format="%.6g")
    pd.DataFrame(results["league_slopes"]["by_league"]).to_csv(TABLES / "league_slopes.csv", index=False, float_format="%.6g")
    pd.DataFrame(results["coefficients"]).to_csv(TABLES / "coefficients.csv", index=False, float_format="%.6g")
    return results


if __name__ == "__main__":
    r = main()
    print(json.dumps(clean({k: r[k] for k in ["sample", "fit", "coefficients", "league_effects"]}), indent=1)[:6000])
