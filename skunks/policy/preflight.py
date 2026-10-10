#!/usr/bin/env python3
"""Preflight live checks for the policy experiments (plan §2 rows S4, S10, S14, plus the wallet's sign-failure texts).

  S4   node B is synced with A, holds no key A holds
  S10  the mempool entry of a submitted transaction carries `cost` and is readable at once
  S14  the HEIGHT that /transactions/check evaluates is fullHeight + 1
  sign the wallet's two refusal texts: "reduced to false" (no path open) and the missing-secret error (the only
       open path needs a key this wallet lacks)

Writes preflight.json beside this file.
"""
import json, time
from common import *

res = {}
ha, hb = full_height(A), full_height(B)
ka, kb = wallet_keys(A), wallet_keys(B)
res["S4"] = {"A_height": ha, "B_height": hb, "A_keys": ka, "B_keys": kb, "shared": sorted(set(ka) & set(kb)),
             "B_peers": must(B, "/info").get("peersCount")}
print("S4", res["S4"]["A_height"], res["S4"]["B_height"], "shared", res["S4"]["shared"])

# S10: one wallet self-payment, then its mempool entry
addr = must(A, "/wallet/addresses")[0]
t0 = time.time()
txid = must(A, "/wallet/transaction/send", {"requests": [{"address": addr, "value": 1_000_000_000}], "fee": FEE})
reads = []
for i in range(50):
    code, o = call(A, f"/transactions/unconfirmed/byTransactionId/{txid}")
    reads.append(code)
    if code == 200:
        res["S10"] = {"tx": txid, "cost": o.get("cost"), "seconds": round(time.time() - t0, 3), "reads": len(reads),
                      "entry_keys": sorted(o.keys())}
        break
    time.sleep(0.2)
else:
    res["S10"] = {"tx": txid, "missed": reads}
print("S10", res["S10"])
wait_tx_outputs(A, txid)

# S14: boxes guarded by HEIGHT == g for g = best+4 .. best+9; once the chain is inside that range, check a spend of
# every box at once; exactly one should accept, and its g relative to fullHeight is the answer
best = full_height()
guards = list(range(best + 4, best + 10))
trees = {g: compile_tree("{ sigmaProp(HEIGHT == $H) }", {"$H": str(g)}) for g in guards}
dep = send([{"address": trees[g][1], "value": 10_000_000} for g in guards])
wait_height(A, best + 6)
h_check = full_height()
rows = []
for g in guards:
    o = at(dep, trees[g][0])[0]
    tx = {"inputs": [inp(o["boxId"])], "dataInputs": [], "outputs": [out(o["value"], NOBODY_TREE, h_check)]}
    code, r = call(A, "/transactions/check", tx)
    rows.append({"guard_height": g, "verdict": classify(code, r), "detail": str(r)[:160] if code != 200 else ""})
h_after = full_height()
res["S14"] = {"rows": rows, "fullHeight_before": h_check, "fullHeight_after": h_after}
print("S14", json.dumps(res["S14"]))

# sign texts: A signs a box whose guard is false, and a box whose only path is B's key
false_tree, false_addr = compile_tree("{ sigmaProp(HEIGHT < 0) }", {})
b_tree, b_addr = compile_tree("{ proveDlog(decodePoint(fromBase16(\"$PK\"))) }", {"$PK": kb[0]})
d = send([{"address": false_addr, "value": 10_000_000}, {"address": b_addr, "value": 10_000_000}])
h = full_height()
texts = {}
for name, tree in (("false", false_tree), ("b_key", b_tree)):
    o = at(d, tree)[0]
    unsigned = {"inputs": [{"boxId": o["boxId"], "extension": {}}], "dataInputs": [],
                "outputs": [out(o["value"], NOBODY_TREE, h)]}
    code, s = call(A, "/wallet/transaction/sign", {"tx": unsigned, "inputsRaw": [raw(o["boxId"])],
                                                    "dataInputsRaw": []})
    texts[name] = {"code": code, "text": str(s)[:600]}
    if name == "b_key":
        code, s = call(B, "/wallet/transaction/sign", {"tx": unsigned, "inputsRaw": [raw(o["boxId"])],
                                                        "dataInputsRaw": []})
        texts["b_key_signed_by_B"] = {"code": code}
res["sign_texts"] = texts
print(json.dumps(texts, indent=1))
info = must(A, "/info")
res["info"] = {k: info[k] for k in ("appVersion", "fullHeight", "parameters")}
json.dump(res, open(Path(__file__).parent / "preflight.json", "w"), indent=1)
