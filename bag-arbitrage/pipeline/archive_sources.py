"""Ask the Internet Archive (Save Page Now) to keep a copy of every source URL.

Writes archived_sources.csv: one row per unique URL in collected_prices.csv with
the snapshot URL the archive returned, or the reason it failed. Run by the
"Archive source pages" GitHub Action; needs only the standard library.
"""
import csv
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "archived_sources.csv"
BUDGET_S = int(os.environ.get("ARCHIVE_BUDGET_S", 3 * 3600))
FIELDS = ["url", "snapshot", "status", "requested_utc"]
UA = "shuming-he.github.io source archiver (smhe@outlook.com)"


def existing(url):
    """Latest snapshot the archive already holds, if any."""
    q = "https://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe="")
    try:
        with urllib.request.urlopen(urllib.request.Request(q, headers={"User-Agent": UA}), timeout=30) as r:
            snap = json.load(r).get("archived_snapshots", {}).get("closest") or {}
            return snap.get("url", "").replace("http://", "https://", 1)
    except Exception:
        return ""


def save(url, tries=2):
    last = ""
    for attempt in range(tries):
        req = urllib.request.Request("https://web.archive.org/save/" + url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                loc = r.headers.get("Content-Location") or ""
                final = r.geturl()
                if loc.startswith("/web/"):
                    return "https://web.archive.org" + loc, "saved"
                if "/web/" in final and "/save/" not in final:
                    return final, "saved"
                last = f"no snapshot location (HTTP {r.status})"
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 429:
                time.sleep(60)
            elif e.code < 500:
                break
        except Exception as e:  # network errors, timeouts
            last = type(e).__name__
        time.sleep(15)
    return "", last


def main():
    with open(HERE / "collected_prices.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    urls = list(dict.fromkeys(r["url"] for r in rows if r["url"]))
    done = {}
    if OUT.exists():
        with open(OUT, newline="") as f:
            done = {r["url"]: r for r in csv.DictReader(f) if r["status"] == "saved"}
    start = time.time()
    out = []
    for i, url in enumerate(urls, 1):
        if url in done:
            out.append(done[url])
            continue
        if time.time() - start > BUDGET_S:
            out.append({"url": url, "snapshot": "", "status": "not attempted (time budget)", "requested_utc": ""})
            continue
        snap, status = save(url)
        if not snap:
            snap = existing(url)
            if snap:
                status = f"existing snapshot ({status})"
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        out.append({"url": url, "snapshot": snap, "status": status, "requested_utc": stamp})
        print(f"{i}/{len(urls)} {status} {url}", flush=True)
        write(out + [{"url": u, "snapshot": "", "status": "pending", "requested_utc": ""} for u in urls[i:]])
        time.sleep(8)
    write(out)
    ok = sum(r["status"] == "saved" for r in out)
    old = sum(r["status"].startswith("existing") for r in out)
    print(f"::notice::saved {ok}, existing older snapshot {old}, none {len(out) - ok - old}, of {len(out)} unique source URLs")


def write(rows):
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
