#!/usr/bin/env python3
"""Experiment 3, part B: a custom extension key from a patched miner (devnet `policy-miner`: A = ergo 6.0.7 with
partB-patch.diff, mining; B = stock 6.0.7, not mining; REST 9183 / 9184).

 (a) relay: does stock B accept A's blocks carrying field F001 = "policy"? B's header id at a height 20 below A's tip
     against A's, after at least 40 blocks, with B's peer count and height (tells "never connected" from "rejected").
 (b) ExtFlag.es compiled with KEY = F001: a flip with a proof of the custom field, against H-1 (i = 0), mined; and
     the same flip with the value byte changed, REFUSE (sibling).
Writes partB.json.
"""
import json, os, sys, time
from pathlib import Path

HERE = Path(__file__).parent
os.environ["POLICY_A"], os.environ["POLICY_B"] = "http://127.0.0.1:9183", "http://127.0.0.1:9184"
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import common  # noqa: E402
from common import *  # noqa: E402
import merkle  # noqa: E402

A, B = common.A, common.B
KEY = "f001"
res = {}
wait_height(A, 40)
ta = full_height(A)
k = ta - 20
ida = must(A, f"/blocks/at/{k}")[0]
cb, idb = call(B, f"/blocks/at/{k}")
infob = must(B, "/info")
blk = must(A, f"/blocks/{ida}")
fields = blk["extension"]["fields"]
res["a"] = {"A_tip": ta, "height": k, "A_id": ida, "B_id": idb[0] if cb == 200 and idb else None,
            "same": cb == 200 and bool(idb) and idb[0] == ida, "B_height": infob["fullHeight"],
            "B_peers": infob.get("peersCount"), "B_version": infob["appVersion"],
            "A_version": must(A, "/info")["appVersion"],
            "custom_field_in_A_block": [f for f in fields if f[0] == KEY],
            "root_matches_header": merkle.root(fields).hex() == blk["header"]["extensionHash"]}
cb2, bb = call(B, f"/blocks/{ida}")
res["a"]["B_has_block_with_field"] = cb2 == 200 and any(f[0] == KEY for f in bb["extension"]["fields"])
print("a", json.dumps(res["a"]))

# (b) the flag with the custom key
src = (HERE / "ExtFlag.es").read_text()
ft, faddr = compile_tree(src, {"$KEY": KEY}, base=A)
while must(A, "/wallet/balances")["balance"] < 1_000_000_000:
    time.sleep(5)
nft = issue("EXTFLAG-F001", base=A)
F = at(send([{"address": faddr, "value": 10_000_000, "assets": [{"tokenId": nft, "amount": 1}],
              "registers": {"R4": FALSE}}], base=A), ft)[0]


def flip_tx(h, tamper=False):
    b = must(A, f"/blocks/{must(A, f'/blocks/at/{h}')[0]}")
    f = b["extension"]["fields"]
    idx = [j for j, (kk, _) in enumerate(f) if kk == KEY][0]
    leaf = merkle.leaf(*f[idx])
    path = merkle.proof(f, idx)
    if tamper:
        leaf = leaf[:-1] + bytes([leaf[-1] ^ 1])
    v = "0c490e" + vlq(len(path)) + "".join(vlq(len(s)) + s.hex() + ("01" if l else "00") for s, l in path)
    return {"inputs": [inp(F["boxId"], {"2": coll_bytes(leaf.hex()), "3": v, "4": int_c(0)})], "dataInputs": [],
            "outputs": [out(F["value"], ft, h, F["assets"], {"R4": TRUE})]}, leaf.hex()


rows = []
h = full_height(A)
code, o = call(A, "/transactions/check", flip_tx(h, True)[0])
rows.append({"n": "B2", "label": "flip with the custom field's value byte changed", "expect": "REFUSE",
             "got": classify(code, o), "sibling_n": "B1", "fullHeight": h})
for attempt in range(6):
    h = full_height(A)
    tx, leaf = flip_tx(h)
    code, o = call(A, "/transactions/check", tx)
    if code != 200:
        rows.append({"n": "B1", "attempt": attempt, "got": classify(code, o), "detail": str(o)[:300]})
        break
    tid = must(A, "/transactions", tx)
    c, _ = None, None
    for _ in range(50):
        cc, e = call(A, f"/transactions/unconfirmed/byTransactionId/{tid}")
        if cc == 200:
            c = e.get("cost")
            break
        time.sleep(0.2)
    wait_height(A, h + 2)
    cm, mt = call(A, f"/blockchain/transaction/byId/{tid}")
    rows.append({"n": "B1", "label": "flip with a proof of the custom field F001 against H-1, mined", "expect": "ACCEPT",
                 "got": "ACCEPT" if cm == 200 else "NOT-MINED", "attempt": attempt, "tx_id": tid, "cost": c,
                 "leaf": leaf, "fullHeight": h, "inclusionHeight": mt.get("inclusionHeight") if cm == 200 else None})
    if cm == 200:
        break
for r in rows:
    if "expect" in r:
        r["ok"] = r["got"] == r["expect"]
res["b"] = {"tree_bytes": len(ft) // 2, "rows": rows}
print("b", json.dumps(res["b"]))
time.sleep(1)
res["a_after"] = {"A_tip": full_height(A), "B_height": full_height(B), "B_peers": must(B, "/info").get("peersCount")}
json.dump(res, open(HERE / "partB.json", "w"), indent=1)
