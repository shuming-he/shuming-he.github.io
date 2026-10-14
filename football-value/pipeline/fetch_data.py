"""Download the public transfermarkt-datasets release (CC0) and keep what the analysis needs.

Source: https://github.com/dcaribou/transfermarkt-datasets (CC0 1.0).
Run by the "Football data" GitHub Action, because this repository's build
environment cannot reach the download host. Writes ../data/raw/ and
../data/raw/PROVENANCE.md (download time, file sizes, SHA-256).
"""
import csv
import gzip
import hashlib
import io
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfermarkt-datasets.zip"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def main(mode):
    RAW.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    blob = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "shuming-he.github.io"}), timeout=600).read()
    zf = zipfile.ZipFile(io.BytesIO(blob))
    lines = [f"# Provenance", "", f"- Source: {URL}", f"- Downloaded (UTC): {stamp}",
             f"- Archive size: {len(blob)} bytes, SHA-256 {hashlib.sha256(blob).hexdigest()}", "", "| File | Bytes | Rows | Columns |", "|---|---|---|---|"]
    for info in zf.infolist():
        if not info.filename.endswith((".csv", ".csv.gz")):
            continue
        data = zf.read(info)
        if info.filename.endswith(".gz"):
            data = gzip.decompress(data)
        text = data.decode("utf-8")
        rows = list(csv.reader(io.StringIO(text)))
        lines.append(f"| {info.filename} | {len(data)} | {len(rows) - 1} | {', '.join(rows[0])} |")
        name = Path(info.filename).name.replace(".gz", "")
        if mode == "schema":
            (RAW / ("head_" + name)).write_text("".join(",".join(f'"{c}"' for c in r) + "\n" for r in rows[:4]))
        elif name in KEEP:
            out = KEEP[name](rows)
            with gzip.open(RAW / (name + ".gz"), "wt", newline="") as f:
                csv.writer(f, lineterminator="\n").writerows(out)
    (RAW / "PROVENANCE.md").write_text("\n".join(lines) + "\n")


KEEP = {}

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "schema")
