"""Ask the Internet Archive (Save Page Now) to keep a copy of every source URL.

Writes archived_sources.csv: one row per unique URL in collected_prices.csv with
the snapshot URL the archive returned, or the reason it failed. Run by the
"Archive source pages" GitHub Action; needs only the standard library.
"""
import csv
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "archived_sources.csv"
UA = "shuming-he.github.io source archiver (smhe@outlook.com)"


def save(url, tries=3):
    last = ""
    for attempt in range(tries):
        req = urllib.request.Request("https://web.archive.org/save/" + url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
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
        except Exception as e:  # network errors, timeouts
            last = type(e).__name__
        time.sleep(20 * (attempt + 1))
    return "", last


def main():
    with open(HERE / "collected_prices.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    urls = list(dict.fromkeys(r["url"] for r in rows if r["url"]))
    done = {}
    if OUT.exists():
        with open(OUT, newline="") as f:
            done = {r["url"]: r for r in csv.DictReader(f) if r["status"] == "saved"}
    out = []
    for i, url in enumerate(urls, 1):
        if url in done:
            out.append(done[url])
            continue
        snap, status = save(url)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        out.append({"url": url, "snapshot": snap, "status": status, "requested_utc": stamp})
        print(f"{i}/{len(urls)} {status} {url}", flush=True)
        time.sleep(12)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["url", "snapshot", "status", "requested_utc"], lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    ok = sum(r["status"] == "saved" for r in out)
    print(f"saved {ok} of {len(out)} unique source URLs")


if __name__ == "__main__":
    main()
