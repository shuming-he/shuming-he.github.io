"""Compare a recomputed results.json with the committed one (numbers to 8 significant digits)."""
import json
import math
import sys


def same(a, b, path="results"):
    if isinstance(a, dict) and isinstance(b, dict):
        if a.keys() != b.keys():
            return [f"{path}: keys differ"]
        return [m for k in a for m in same(a[k], b[k], f"{path}.{k}")]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: lengths differ"]
        return [m for i, (x, y) in enumerate(zip(a, b)) for m in same(x, y, f"{path}[{i}]")]
    if isinstance(a, float) or isinstance(b, float):
        if a is None or b is None or not math.isclose(a, b, rel_tol=1e-8, abs_tol=1e-12):
            return [f"{path}: {a} != {b}"]
        return []
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


if __name__ == "__main__":
    diffs = same(json.load(open(sys.argv[1])), json.load(open(sys.argv[2])))
    print("\n".join(diffs[:50]) or "results reproduced")
    sys.exit(1 if diffs else 0)
