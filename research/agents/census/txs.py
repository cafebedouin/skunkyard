"""U1d: transactions by id, compacted (who ran an action: input addresses; what it moved: outputs; data inputs).

`/transactions/{id}` per transaction, cached raw (gzipped); the compacted set is census/out/u1d/txs-<name>.json.gz.
"""
import gzip, json, os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CENSUS_GZIP", "1")
import explorer as X  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "u1d")


def _io(b):
    return {"box": b["boxId"], "addr": b.get("address"), "value": b["value"],
            "assets": [[a["tokenId"], a["amount"]] for a in b.get("assets", [])],
            "regs": {k: v.get("renderedValue") for k, v in (b.get("additionalRegisters") or {}).items()}}


def compact(t):
    return {"id": t["id"], "h": t["inclusionHeight"], "index": t.get("index"),
            "inputs": [_io(i) for i in t["inputs"]], "outputs": [_io(o) for o in t["outputs"]],
            "dataInputs": [{"box": d["boxId"], "addr": d.get("address"),
                            "assets": [[a["tokenId"], a["amount"]] for a in d.get("assets", [])]}
                           for d in t.get("dataInputs", [])]}


def fetch(ids, name, threads=4):
    """{txId: compact tx} for every id (None for a 404)."""
    os.makedirs(OUT, exist_ok=True)
    cp = os.path.join(OUT, f"txs-{name}.json.gz")
    have = {}
    if os.path.exists(cp):
        with gzip.open(cp, "rt") as f:
            have = json.load(f)
    need = sorted(set(ids) - set(have))
    if need:
        def one(i):
            t = X.get(f"/transactions/{i}")
            return i, compact(t) if t else None
        with ThreadPoolExecutor(threads) as ex:
            for i, t in ex.map(one, need):
                have[i] = t
        with gzip.open(cp + ".tmp", "wt") as f:
            json.dump(have, f)
        os.replace(cp + ".tmp", cp)
    return {i: have[i] for i in ids}
