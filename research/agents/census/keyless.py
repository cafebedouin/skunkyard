"""U1b lines (f) and (k): one pass over every block of the window.

(f) Every transaction input whose spending proof is empty (null or "") was spent with no signature. Inputs are
grouped by the explorer's template hash (SHA-256 of the constant-free tree, census/trees.py); the tree comes from
the input's address (P2PK and P2S carry it; a P2SH address does not, and its box is fetched instead).
(k) Fees per block: the sum of outputs to the miner-fee contract, as U1 (census-u1.py fee_sample), on every block.
"""
import collections, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blockscan as B  # noqa: E402
import explorer as X  # noqa: E402
import trees as T  # noqa: E402

SAMPLES = 12


def input_tree(i, cache={}):  # noqa: B006 (deliberate memo)
    a = i["address"]
    if a in cache:
        return cache[a]
    t = T.address_tree(a)
    if t is None:
        box = X.get(f"/boxes/{i['id']}")
        t = box["ergoTree"] if box else None
    cache[a] = t
    return t


def scan(lo, hi, workers=6, log=print):
    hdr = B.headers(lo, hi, workers)
    tmpl = collections.defaultdict(lambda: {"inputs": 0, "keyless": 0, "keylessNanoErg": 0, "signed": 0,
                                            "firstKeyless": None, "lastKeyless": None, "samples": [],
                                            "tree": None, "with": collections.Counter(), "txs": 0})
    fees, txcount, keyless_txs, p2pk_keyless = {}, {}, 0, []
    for h, b in B.full_blocks(hdr, workers, log):
        txs = b["block"]["blockTransactions"]
        txcount[h] = len(txs)
        fees[h] = sum(o["value"] for t in txs for o in t["outputs"] if o["ergoTree"] == T.FEE_TREE)
        for t in txs:
            th_in = []
            for i in t["inputs"]:
                tree = input_tree(i)
                if tree is None:
                    th = "p2sh-unresolved"
                elif tree.startswith("0008cd"):
                    th = "p2pk"           # the key is inline, so every key has its own template hash
                else:
                    th = T.template_hash(tree)
                th_in.append((th, i, tree))
            kl = [x for x in th_in if not x[1]["spendingProof"]]
            if kl:
                keyless_txs += 1
            seen = set()
            for th, i, tree in th_in:
                r = tmpl[th]
                r["inputs"] += 1
                if i["spendingProof"]:
                    r["signed"] += 1
                    continue
                r["keyless"] += 1
                if th == "p2pk":
                    p2pk_keyless.append({"height": h, "tx": t["id"], "box": i["id"], "value": i["value"]})
                r["keylessNanoErg"] += i["value"]
                r["firstKeyless"] = r["firstKeyless"] or h
                r["lastKeyless"] = h
                if r["tree"] is None:
                    r["tree"] = tree
                if th not in seen:
                    seen.add(th)
                    r["txs"] += 1
                    for th2, _, _ in th_in:
                        if th2 != th:
                            r["with"][th2] += 1
                if len(r["samples"]) < SAMPLES:
                    r["samples"].append({"height": h, "tx": t["id"], "box": i["id"], "value": i["value"]})
    out = {k: dict(v, **{"with": dict(v["with"].most_common(8))}) for k, v in tmpl.items()}
    return {"templates": out, "p2pkKeyless": p2pk_keyless, "fees": fees, "txCount": txcount, "keylessTxs": keyless_txs,
            "headers": {h: {"id": hdr[h]["id"], "ts": hdr[h]["timestamp"], "minerReward": hdr[h]["minerReward"],
                            "miner": hdr[h]["miner"]["address"]} for h in hdr}}
