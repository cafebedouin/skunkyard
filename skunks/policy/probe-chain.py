#!/usr/bin/env python3
"""Control for experiment 7b row 14: does node A's mempool keep a transaction that spends an unconfirmed output, for
a trivial keyless script (`HEIGHT > 0`)? tx1 spends a confirmed box into a new box at the same script; tx2 spends
tx1's output at once. The mempool entry of each is polled for 3 s. Writes probe-chain.json."""
import json, time
from common import *

t, a = compile_tree("{ sigmaProp(HEIGHT > 0) }", {})
b0 = at(send([{"address": a, "value": 50_000_000}]), t)[0]
h = full_height()
tx1 = {"inputs": [inp(b0["boxId"])], "dataInputs": [], "outputs": [out(b0["value"], t, h)]}
id1 = must(A, "/transactions", tx1)
e1 = must(A, f"/transactions/unconfirmed/byTransactionId/{id1}")
o1 = e1["outputs"][0]
tx2 = {"inputs": [inp(o1["boxId"])], "dataInputs": [], "outputs": [out(o1["value"], t, h)]}
c2, r2 = call(A, "/transactions/check", tx2)
p2 = call(A, "/transactions", tx2)
id2 = p2[1] if p2[0] == 200 else None
polls = []
for _ in range(15):
    polls.append({"tx1": call(A, f"/transactions/unconfirmed/byTransactionId/{id1}")[0],
                  "tx2": call(A, f"/transactions/unconfirmed/byTransactionId/{id2}")[0] if id2 else None})
    time.sleep(0.2)
m1 = wait_tx_outputs(A, id1)
wait_height(A, m1["inclusionHeight"] + 2)
c, m2 = call(A, f"/blockchain/transaction/byId/{id2}") if id2 else (None, None)
res = {"check2": c2, "post2": p2[0], "polls": polls, "tx1_included": m1["inclusionHeight"],
       "tx2_included": m2.get("inclusionHeight") if c == 200 else None}
print(json.dumps(res))
json.dump(res, open(Path(__file__).parent / "probe-chain.json", "w"), indent=1)
