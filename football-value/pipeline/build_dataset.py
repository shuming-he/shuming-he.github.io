"""Build one row per outfield player and season from the raw public data.

For each league season (2023/24, 2024/25, 2025/26) and player:
- on-field stats from that season's league games only (minutes, starts, goals,
  assists, cards), summed over every club the player played for in that league;
- the club and league where he played most league minutes;
- that club's points per game in the same season (team strength);
- the Transfermarkt market value published at the end of that season
  (latest valuation dated 1 May to 30 June after the season), plus a looser
  fallback used only in a robustness check;
- age and contract years left on 30 June after the season.

Writes ../data/player_seasons.csv and ../data/exclusions.csv. Nothing is
dropped silently: every player who played but is not in the analysis sample is
listed in exclusions.csv with a reason.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SEASONS = {2023: "2023/24", 2024: "2024/25", 2025: "2025/26"}
POSITION_GROUP = {
    "Centre-Back": "Centre-back", "Right-Back": "Full-back", "Left-Back": "Full-back",
    "Defensive Midfield": "Defensive mid", "Central Midfield": "Central mid", "Right Midfield": "Central mid",
    "Left Midfield": "Central mid", "Attacking Midfield": "Attacking mid", "Right Winger": "Winger",
    "Left Winger": "Winger", "Centre-Forward": "Forward", "Second Striker": "Forward",
}
MIN_MINUTES = 900


def load(name):
    return pd.read_csv(RAW / f"{name}.csv.gz", low_memory=False)


def team_points(club_games, games):
    cg = club_games.merge(games[["game_id", "season", "competition_id"]], on="game_id")
    cg["points"] = np.select([cg.own_goals > cg.opponent_goals, cg.own_goals == cg.opponent_goals], [3, 1], 0)
    t = cg.groupby(["season", "club_id"]).agg(team_games=("points", "size"), team_points=("points", "sum"),
                                              team_gd=("own_goals", "sum"), team_ga=("opponent_goals", "sum")).reset_index()
    t["team_ppg"] = t.team_points / t.team_games
    t["team_gd_pg"] = (t.team_gd - t.team_ga) / t.team_games
    return t[["season", "club_id", "team_ppg", "team_gd_pg"]]


def season_values(valuations, season, window_start):
    end = pd.Timestamp(f"{season + 1}-06-30")
    v = valuations[(valuations.date <= end)]
    latest = v.sort_values("date").groupby("player_id").tail(1)
    latest = latest.rename(columns={"date": "value_date", "market_value_in_eur": "value_any"})[["player_id", "value_date", "value_any"]]
    latest["value_end"] = np.where(latest.value_date >= pd.Timestamp(f"{season + 1}-{window_start}"), latest.value_any, np.nan)
    prev_end = pd.Timestamp(f"{season}-06-30")
    prev = valuations[(valuations.date <= prev_end) & (valuations.date >= pd.Timestamp(f"{season}-{window_start}"))]
    prev = prev.sort_values("date").groupby("player_id").tail(1).rename(columns={"market_value_in_eur": "value_prev"})[["player_id", "value_prev"]]
    return latest.merge(prev, on="player_id", how="left")


def build():
    games, apps, lineups = load("games"), load("appearances"), load("game_lineups")
    players, valuations, clubs, comps = load("players"), load("player_valuations"), load("clubs"), load("competitions")
    valuations["date"] = pd.to_datetime(valuations.date)
    apps = apps.merge(games[["game_id", "season"]], on="game_id")
    starts = lineups[lineups.type == "starting_lineup"][["game_id", "player_id"]].drop_duplicates().assign(started=1)
    apps = apps.merge(starts, on=["game_id", "player_id"], how="left").fillna({"started": 0})

    by_club = apps.groupby(["season", "player_id", "player_club_id", "competition_id"]).agg(
        club_minutes=("minutes_played", "sum")).reset_index()
    main_club = by_club.sort_values(["club_minutes", "player_club_id"], ascending=[False, True]).groupby(["season", "player_id"]).head(1)
    n_clubs = by_club.groupby(["season", "player_id"]).size().rename("n_clubs")
    n_leagues = by_club.groupby(["season", "player_id"]).competition_id.nunique().rename("n_leagues")

    stats = apps.groupby(["season", "player_id"]).agg(
        apps=("game_id", "size"), starts=("started", "sum"), minutes=("minutes_played", "sum"),
        goals=("goals", "sum"), assists=("assists", "sum"), yellow=("yellow_cards", "sum"), red=("red_cards", "sum")).reset_index()
    df = stats.merge(main_club.rename(columns={"player_club_id": "club_id", "competition_id": "league"})[["season", "player_id", "club_id", "league"]],
                     on=["season", "player_id"]).join(n_clubs, on=["season", "player_id"]).join(n_leagues, on=["season", "player_id"])
    df = df.merge(team_points(load("club_games"), games), on=["season", "club_id"], how="left")
    league_games = games.groupby(["season", "competition_id"]).size().rename("league_games").reset_index()
    clubs_per = games.groupby(["season", "competition_id"]).home_club_id.nunique().rename("n_teams").reset_index()
    league_games = league_games.merge(clubs_per, on=["season", "competition_id"])
    league_games["matches_per_team"] = league_games.league_games * 2 / league_games.n_teams
    df = df.merge(league_games[["season", "competition_id", "matches_per_team"]].rename(columns={"competition_id": "league"}), on=["season", "league"])

    p = players[["player_id", "name", "date_of_birth", "position", "sub_position", "contract_expiration_date", "url"]].copy()
    df = df.merge(p, on="player_id", how="left")
    df = df.merge(clubs[["club_id", "name"]].rename(columns={"name": "club"}), on="club_id", how="left")
    df = df.merge(comps[["competition_id", "name"]].rename(columns={"competition_id": "league", "name": "league_name"}), on="league", how="left")

    parts = []
    for s in SEASONS:
        parts.append(df[df.season == s].merge(season_values(valuations, s, "05-01"), on="player_id", how="left"))
    df = pd.concat(parts, ignore_index=True)

    ref = pd.to_datetime(df.season.add(1).astype(str) + "-06-30")
    dob = pd.to_datetime(df.date_of_birth, errors="coerce")
    df["age"] = (ref - dob).dt.days / 365.25
    exp = pd.to_datetime(df.contract_expiration_date, errors="coerce")
    df["contract_years"] = ((exp - ref).dt.days / 365.25).clip(lower=0)
    df["contract_known"] = exp.notna() & (exp > ref)
    df["position_group"] = df.sub_position.map(POSITION_GROUP)
    for c in ["goals", "assists", "yellow", "red"]:
        df[f"{c}_p90"] = df[c] / df.minutes * 90
    df["minutes_share"] = df.minutes / (df.matches_per_team * 90)
    df["start_share"] = df.starts / df.matches_per_team
    df["season_label"] = df.season.map(SEASONS)

    reasons = [
        (df.position == "Goalkeeper", "goalkeeper"),
        (df.position_group.isna(), "no outfield position"),
        (df.minutes < MIN_MINUTES, f"fewer than {MIN_MINUTES} league minutes"),
        (df.age.isna(), "no date of birth"),
        (df.value_end.isna(), "no market value published 1 May-30 June after the season"),
    ]
    df["exclusion"] = ""
    for mask, why in reasons:
        df.loc[mask & (df.exclusion == ""), "exclusion"] = why
    df["in_sample"] = df.exclusion == ""
    df["log_value"] = np.log(df.value_end)
    df = df.sort_values(["season", "league", "player_id"]).reset_index(drop=True)
    cols = ["season", "season_label", "league", "league_name", "player_id", "name", "club_id", "club", "n_clubs", "n_leagues",
            "position", "sub_position", "position_group", "age", "contract_years", "contract_known", "apps", "starts", "minutes",
            "minutes_share", "start_share", "goals", "assists", "yellow", "red", "goals_p90", "assists_p90", "yellow_p90", "red_p90",
            "team_ppg", "team_gd_pg", "value_end", "value_any", "value_date", "value_prev", "log_value", "in_sample", "exclusion", "url"]
    df = df[cols]
    df.to_csv(ROOT / "data" / "player_seasons.csv", index=False, float_format="%.6g")
    ex = df[~df.in_sample].groupby(["season_label", "league", "exclusion"]).size().rename("players").reset_index()
    ex.to_csv(ROOT / "data" / "exclusions.csv", index=False)
    return df


if __name__ == "__main__":
    d = build()
    print(d.groupby(["season_label", "league"]).in_sample.agg(["size", "sum"]))
    print(d[~d.in_sample].exclusion.value_counts())
