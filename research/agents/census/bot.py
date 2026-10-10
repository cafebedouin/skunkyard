"""U1d line q: every transaction of the SigmaUSD bank bot, compacted (inputs/outputs by address, value, tokens).

`/addresses/{addr}/transactions` pages newest first; the bot has not traded since 1,888,826, so the pages are stable.
Cached raw (gzipped); compacted to census/out/u1d/bot-txs.json.gz.
"""
import gzip, json, os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CENSUS_GZIP", "1")
import explorer as X  # noqa: E402

BOT = "9fffEXsaT9roF7tKt5GyJUUZfun3NpWrMQ5oMAGGXRYMFK88aJq"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "u1d")


def _io(b):
    return {"box": b["boxId"], "addr": b["address"], "value": b["value"],
            "assets": [[a["tokenId"], a["amount"]] for a in b.get("assets", [])]}


def fetch(addr=BOT, threads=4):
    cp = os.path.join(OUT, f"txs-{addr[:12]}.json.gz")
    total = X.get(f"/addresses/{addr}/transactions?offset=0&limit=1", cache=False)["total"]
    if os.path.exists(cp):
        with gzip.open(cp, "rt") as f:
            have = json.load(f)
        if have["total"] == total:
            return have["txs"]
    offs = list(range(0, total, 100))

    def page(o):
        return X.get(f"/addresses/{addr}/transactions?offset={o}&limit=100", cache=o != 0)["items"]

    with ThreadPoolExecutor(threads) as ex:
        pages = list(ex.map(page, offs))
    txs, seen = [], set()
    for p in pages:
        for t in p:
            if t["id"] in seen:
                continue
            seen.add(t["id"])
            txs.append({"id": t["id"], "h": t["inclusionHeight"], "gix": t["globalIndex"], "index": t["index"],
                        "inputs": [_io(i) for i in t["inputs"]], "outputs": [_io(o) for o in t["outputs"]],
                        "dataInputs": [d["boxId"] for d in t.get("dataInputs", [])]})
    txs.sort(key=lambda t: (t["h"], t["gix"]))
    os.makedirs(OUT, exist_ok=True)
    with gzip.open(cp, "wt") as f:
        json.dump({"addr": addr, "total": total, "txs": txs}, f)
    return txs


if __name__ == "__main__":
    t = fetch(sys.argv[1] if len(sys.argv) > 1 else BOT)
    print(len(t), t[0]["h"], t[-1]["h"], X.stats)
