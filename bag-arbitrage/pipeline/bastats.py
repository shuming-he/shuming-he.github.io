"""Core calculations for the Bag Arbitrage study.

Conventions used everywhere in the project:

* Prices are list prices before sales tax: P_US in USD, P_CA in CAD.
* The exchange rate `fx` is CAD per USD (Bank of Canada FXUSDCAD convention).
  A US price in CAD is therefore P_US * fx.
* The paired log-price difference for product i is
      d_i = ln(P_CA,i / (P_US,i * fx)).
  d_i > 0 means the Canadian list price is higher after conversion.
* Tax scenarios multiply each side by (1 + rate). Because the same rates apply to
  every product, a tax scenario shifts every d_i by the same constant.

All functions are pure and work on numpy arrays or pandas objects so they can be
unit-tested with small synthetic inputs.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------- price maths
def validate_prices(us, ca) -> None:
    """Reject missing or non-positive prices instead of silently using them."""
    us, ca = np.asarray(us, dtype=float), np.asarray(ca, dtype=float)
    if us.shape != ca.shape:
        raise ValueError("US and CA price arrays must have the same length")
    if np.isnan(us).any() or np.isnan(ca).any():
        raise ValueError("missing price: every pair needs both a US and a CA price")
    if (us <= 0).any() or (ca <= 0).any():
        raise ValueError("prices must be strictly positive")


def usd_to_cad(price_usd, fx_cad_per_usd: float):
    if fx_cad_per_usd <= 0:
        raise ValueError("exchange rate must be positive")
    return np.asarray(price_usd, dtype=float) * fx_cad_per_usd


def with_tax(price, rate_pct: float):
    if rate_pct < 0:
        raise ValueError("tax rate cannot be negative")
    return np.asarray(price, dtype=float) * (1 + rate_pct / 100)


def log_diff(us, ca, fx: float, tax_us_pct: float = 0.0, tax_ca_pct: float = 0.0) -> np.ndarray:
    """d_i = ln(CA price / US price converted to CAD), optionally after tax."""
    validate_prices(us, ca)
    us_cad = with_tax(usd_to_cad(us, fx), tax_us_pct)
    return np.log(with_tax(ca, tax_ca_pct) / us_cad)


def pct_from_log(m: float) -> float:
    """Geometric-mean percentage difference implied by a mean log difference."""
    return float(np.expm1(m) * 100)


# ---------------------------------------------------------------- estimators
@dataclass
class Estimate:
    method: str
    n: int
    clusters: int | None
    mean_log: float
    se: float | None
    ci_low: float | None
    ci_high: float | None
    stat: float | None
    df: float | None
    p: float | None
    note: str = ""

    def as_dict(self) -> dict:
        d = asdict(self)
        d["pct"] = pct_from_log(self.mean_log)
        d["ci_low_pct"] = None if self.ci_low is None else pct_from_log(self.ci_low)
        d["ci_high_pct"] = None if self.ci_high is None else pct_from_log(self.ci_high)
        d["ratio"] = float(np.exp(self.mean_log))
        return d


def paired_iid(d: np.ndarray, method="Paired t-test (products independent)") -> Estimate:
    """One-sample t on d_i: equivalent to a paired t-test on log prices."""
    d = np.asarray(d, dtype=float)
    n = d.size
    m, sd = d.mean(), d.std(ddof=1)
    se = sd / np.sqrt(n)
    t = m / se
    tc = stats.t.ppf(0.975, n - 1)
    return Estimate(method, n, None, m, se, m - tc * se, m + tc * se, t, n - 1, 2 * stats.t.sf(abs(t), n - 1))


def cluster_robust_mean(d: np.ndarray, cluster: np.ndarray, method="Cluster-robust by brand (CR1, t with G−1 df)") -> Estimate:
    """Product-weighted mean of d with a brand-clustered standard error.

    Uses the CR1 sandwich variance for an intercept-only regression,
        V = G/(G-1) * sum_g (sum_{i in g} e_i)^2 / n^2,
    and t critical values with G-1 degrees of freedom (Cameron & Miller 2015).
    """
    d, cluster = np.asarray(d, dtype=float), np.asarray(cluster)
    n = d.size
    m = d.mean()
    e = d - m
    sums = pd.Series(e).groupby(cluster).sum().to_numpy()
    G = sums.size
    if G < 2:
        raise ValueError("need at least two clusters")
    se = np.sqrt(G / (G - 1) * np.sum(sums ** 2) / n ** 2)
    t = m / se
    tc = stats.t.ppf(0.975, G - 1)
    return Estimate(method, n, G, m, se, m - tc * se, m + tc * se, t, G - 1, 2 * stats.t.sf(abs(t), G - 1))


def brand_equal(d: np.ndarray, cluster: np.ndarray) -> Estimate:
    """Average of brand means: every brand gets equal weight (t on G brand means)."""
    means = pd.Series(np.asarray(d, dtype=float)).groupby(np.asarray(cluster)).mean().to_numpy()
    e = paired_iid(means, "Brand-equal weights (t on brand means)")
    e.n, e.clusters = int(np.asarray(d).size), int(means.size)
    return e


def cluster_bootstrap(d: np.ndarray, cluster: np.ndarray, reps: int = 9999, seed: int = 20261013) -> Estimate:
    """Percentile CI from resampling whole brands with replacement."""
    d, cluster = np.asarray(d, dtype=float), np.asarray(cluster)
    groups = [d[cluster == g] for g in pd.unique(cluster)]
    G = len(groups)
    sums = np.array([g.sum() for g in groups])
    sizes = np.array([g.size for g in groups])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, G, size=(reps, G))
    boot = sums[idx].sum(axis=1) / sizes[idx].sum(axis=1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return Estimate(f"Brand cluster bootstrap (percentile, B = {reps}, seed {seed})", d.size, G, d.mean(),
                    float(boot.std(ddof=1)), float(lo), float(hi), None, None, None,
                    "Few clusters: bootstrap intervals can be too narrow (Cameron, Gelbach & Miller 2008).")


def wild_cluster_bootstrap_p(d: np.ndarray, cluster: np.ndarray, max_enumerate: int = 16,
                             reps: int = 9999, seed: int = 20261013) -> dict:
    """Wild cluster bootstrap-t p-value for H0: mean d = 0 (Rademacher weights, null imposed).

    Recommended for few clusters by Cameron, Gelbach & Miller (2008). With G <= max_enumerate
    clusters all 2^G sign patterns are enumerated, so the result needs no random seed.
    """
    d, cluster = np.asarray(d, dtype=float), np.asarray(cluster)
    labels = pd.unique(cluster)
    G, n = labels.size, d.size
    t_obs = cluster_robust_mean(d, cluster).stat
    code = pd.Categorical(cluster, categories=labels).codes
    if G <= max_enumerate:
        signs = ((np.arange(2 ** G)[:, None] >> np.arange(G)) & 1) * 2 - 1
        how = f"all {2 ** G} Rademacher sign patterns enumerated"
    else:
        signs = np.random.default_rng(seed).choice([-1, 1], size=(reps, G))
        how = f"{reps} random Rademacher draws, seed {seed}"
    # Under H0 the restricted residuals are d itself; d* = w_g * d_i.
    ds = signs[:, code] * d                       # (B, n)
    m = ds.mean(axis=1)
    e = ds - m[:, None]
    sums = np.zeros((ds.shape[0], G))
    for g in range(G):
        sums[:, g] = e[:, code == g].sum(axis=1)
    se = np.sqrt(G / (G - 1) * (sums ** 2).sum(axis=1) / n ** 2)
    t_star = m / se
    p = float(np.mean(np.abs(t_star) >= abs(t_obs) - 1e-12))
    return {"method": "Wild cluster bootstrap-t (Rademacher, H0 imposed)", "t": float(t_obs), "p": p,
            "draws": how, "min_possible_p": float(2 / signs.shape[0])}


def wilcoxon_signed_rank(d: np.ndarray) -> Estimate:
    """Signed-rank test of a zero median d (products treated as independent)."""
    d = np.asarray(d, dtype=float)
    res = stats.wilcoxon(d)
    return Estimate("Wilcoxon signed-rank (median, products independent)", d.size, None, float(np.median(d)),
                    None, None, None, float(res.statistic), None, float(res.pvalue),
                    "Estimate shown is the median d, not the mean.")


def leave_one_cluster_out(d: np.ndarray, cluster: np.ndarray) -> pd.DataFrame:
    d, cluster = np.asarray(d, dtype=float), np.asarray(cluster)
    rows = []
    for g in pd.unique(cluster):
        keep = cluster != g
        rows.append({"dropped": g, "n": int(keep.sum()), "mean_log": d[keep].mean(), "pct": pct_from_log(d[keep].mean())})
    return pd.DataFrame(rows)


def brand_summary(d: np.ndarray, cluster: np.ndarray) -> pd.DataFrame:
    """Per-brand mean d with a within-brand t interval (descriptive)."""
    df = pd.DataFrame({"d": d, "brand": cluster})
    rows = []
    for b, g in df.groupby("brand", sort=False):
        x = g["d"].to_numpy()
        n, m = x.size, x.mean()
        if n > 1:
            se = x.std(ddof=1) / np.sqrt(n)
            tc = stats.t.ppf(0.975, n - 1)
            lo, hi = m - tc * se, m + tc * se
        else:
            se = lo = hi = np.nan
        rows.append({"brand": b, "n": n, "mean_log": m, "pct": pct_from_log(m), "se": se,
                     "ci_low_pct": pct_from_log(lo) if n > 1 else None, "ci_high_pct": pct_from_log(hi) if n > 1 else None})
    return pd.DataFrame(rows)


def ols_cluster(y: np.ndarray, X: np.ndarray, cluster: np.ndarray, names: list[str]) -> pd.DataFrame:
    """OLS with CR1 brand-clustered standard errors and t(G-1) p-values."""
    y, X, cluster = np.asarray(y, float), np.asarray(X, float), np.asarray(cluster)
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    G = len(pd.unique(cluster))
    meat = np.zeros((k, k))
    for g in pd.unique(cluster):
        s = X[cluster == g].T @ e[cluster == g]
        meat += np.outer(s, s)
    c = G / (G - 1) * (n - 1) / (n - k)
    V = c * XtX_inv @ meat @ XtX_inv
    se = np.sqrt(np.diag(V))
    t = beta / se
    p = 2 * stats.t.sf(np.abs(t), G - 1)
    r2 = 1 - (e @ e) / np.sum((y - y.mean()) ** 2)
    out = pd.DataFrame({"term": names, "coef": beta, "se_cluster": se, "t": t, "p": p})
    out.attrs.update(n=n, clusters=G, r2=float(r2))
    return out


def collapse_identical_variants(df: pd.DataFrame) -> pd.DataFrame:
    """Keep one row per brand and identical (US price, CA price) pair.

    Colour variants of one model usually share both prices; counting each colour
    as a separate observation overstates the effective sample size.
    """
    return df.drop_duplicates(subset=["brand_id", "us", "ca"]).reset_index(drop=True)
