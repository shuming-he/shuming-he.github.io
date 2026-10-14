"""Download the public transfermarkt-datasets release (CC0) and keep what the analysis needs.

Source: https://github.com/dcaribou/transfermarkt-datasets (CC0 1.0), built from
Transfermarkt pages. Run by the "Football data" GitHub Action, because the
environment this project was built in cannot reach the download host.

Keeps league games of the big five European leagues from July 2023 on, the
players who appear in them, and their market valuations. Writes ../data/raw/
and ../data/raw/PROVENANCE.md (download time, sizes, SHA-256, row counts).
"""
import hashlib
import io
import time
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfermarkt-datasets.zip"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
LEAGUES = ["GB1", "ES1", "L1", "IT1", "FR1"]
FROM = "2023-07-01"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for old in RAW.glob("head_*"):
        old.unlink()
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    blob = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "shuming-he.github.io"}), timeout=900).read()
    zf = zipfile.ZipFile(io.BytesIO(blob))
    path = {Path(i.filename).name.split(".")[0]: i.filename for i in zf.infolist() if ".csv" in i.filename}

    def read(name):
        return pd.read_csv(zf.open(path[name]), compression="gzip" if path[name].endswith(".gz") else None, low_memory=False)

    games = read("games")
    games = games[games.competition_id.isin(LEAGUES) & (games.date >= FROM)]
    ids = set(games.game_id)
    out = {"games": games}
    out["appearances"] = read("appearances").query("game_id in @ids")
    out["game_lineups"] = read("game_lineups").query("game_id in @ids")
    out["club_games"] = read("club_games").query("game_id in @ids")
    pids = set(out["appearances"].player_id)
    out["players"] = read("players").query("player_id in @pids")
    out["player_valuations"] = read("player_valuations").query("player_id in @pids and date >= '2022-07-01'")
    out["clubs"] = read("clubs")
    out["competitions"] = read("competitions")

    lines = ["# Provenance", "", f"- Source: {URL}", "- Licence: CC0 1.0 (https://github.com/dcaribou/transfermarkt-datasets)",
             f"- Downloaded (UTC): {stamp}", f"- Archive: {len(blob)} bytes, SHA-256 {hashlib.sha256(blob).hexdigest()}",
             f"- Filter: league games in {', '.join(LEAGUES)} dated {FROM} or later, their players, valuations from 2022-07-01", "",
             "| File | Rows kept | Columns |", "|---|---|---|"]
    for name, df in out.items():
        df.to_csv(RAW / f"{name}.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
        lines.append(f"| {name}.csv.gz | {len(df)} | {', '.join(df.columns)} |")
    (RAW / "PROVENANCE.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
