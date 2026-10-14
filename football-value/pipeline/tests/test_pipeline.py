"""Tests on small synthetic data with known answers."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_dataset as bd  # noqa: E402
import run_analysis as ra  # noqa: E402


class TeamPoints(unittest.TestCase):
    def test_win_draw_loss(self):
        games = pd.DataFrame({"game_id": [1, 2, 3], "season": [2025] * 3, "competition_id": ["GB1"] * 3})
        cg = pd.DataFrame({"game_id": [1, 2, 3], "club_id": [7, 7, 7], "own_goals": [2, 1, 0], "opponent_goals": [0, 1, 3]})
        t = bd.team_points(cg, games)
        self.assertAlmostEqual(t.team_ppg.iloc[0], 4 / 3)
        self.assertAlmostEqual(t.team_gd_pg.iloc[0], -1 / 3)


class Valuations(unittest.TestCase):
    def test_end_of_season_window(self):
        v = pd.DataFrame({"player_id": [1, 1, 2, 3], "market_value_in_eur": [10, 20, 5, 9],
                          "date": pd.to_datetime(["2026-03-01", "2026-06-02", "2026-03-15", "2026-07-15"])})
        out = bd.season_values(v, 2025, "05-01").set_index("player_id")
        self.assertEqual(out.loc[1, "value_end"], 20)       # latest in May-June window
        self.assertTrue(np.isnan(out.loc[2, "value_end"]))  # only a March value: excluded from primary
        self.assertEqual(out.loc[2, "value_any"], 5)        # but kept for the robustness check
        self.assertNotIn(3, out.index)                      # valuations after 30 June are never used


def fake_players(n=400, seed=0):
    rng = np.random.default_rng(seed)
    club = rng.integers(0, 40, n)
    d = pd.DataFrame({"club_id": club, "league": np.where(club < 20, "GB1", "ES1"),
                      "position_group": rng.choice(["Centre-back", "Winger", "Forward"], n),
                      "age": rng.uniform(18, 34, n), "contract_years": rng.uniform(0, 5, n), "no_contract": 0,
                      "minutes_share": rng.uniform(0.3, 1, n), "goals_p90": rng.gamma(1, 0.15, n), "assists_p90": rng.gamma(1, 0.1, n),
                      "yellow_p90": rng.gamma(1, 0.2, n), "team_ppg": rng.uniform(0.8, 2.4, 40)[club]})
    d["log_value"] = 15 + 1.4 * d.minutes_share + 1.2 * d.goals_p90 + 1.0 * d.team_ppg + rng.normal(0, 0.3, 40)[club] + rng.normal(0, 0.4, n)
    return d


class Models(unittest.TestCase):
    def test_recovers_known_slopes(self):
        m = ra.fit(ra.FULL, fake_players(3000))
        self.assertAlmostEqual(m.params["goals_p90"], 1.2, delta=0.2)
        self.assertAlmostEqual(m.params["team_ppg"], 1.0, delta=0.3)
        self.assertEqual(m.df_resid_inference, 39)  # G - 1 clusters

    def test_cv_holds_out_whole_clubs(self):
        d = fake_players()
        r2, pred = ra.cv_r2(ra.FULL, d, folds=5)
        self.assertTrue(pred.notna().all())
        self.assertLess(r2, ra.fit(ra.FULL, d).rsquared)    # out of sample is lower than in sample

    def test_wild_bootstrap_null(self):
        d = fake_players()  # same slopes in both leagues by construction
        inter = " + ".join(f"{v}:C(league, Treatment('GB1'))" for v in ra.FIELD)
        w = ra.wild_wald(d, ra.FULL, f"{ra.FULL} + {inter}", reps=99)
        self.assertGreater(w["p"], 0.01)
        self.assertLessEqual(w["p"], 1)

    def test_scaled_effect(self):
        m = ra.fit(ra.FULL, fake_players(1000))
        row = [r for r in ra.coef_table(m, ["goals_p90"])][0]
        self.assertAlmostEqual(row["pct"], 100 * (np.exp(row["coef"] * 0.1) - 1))


class Output(unittest.TestCase):
    def test_clean_keeps_tiny_p_values(self):
        out = ra.clean({"p": 3e-24, "nan": float("nan"), "i": np.int64(3)})
        self.assertGreater(out["p"], 0)
        self.assertIsNone(out["nan"])
        self.assertEqual(out["i"], 3)


if __name__ == "__main__":
    unittest.main()
