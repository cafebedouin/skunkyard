#!/usr/bin/env python3
"""Probe: which HEIGHT does /wallet/transaction/sign reduce the script at, against /transactions/check (S14)?
Boxes guarded by `sigmaProp(HEIGHT == g) && proveDlog(A's key)` for g around the current height; A's wallet signs
each at one fullHeight; signed ones are then checked. Writes probe-sign-height.json."""
import json
from common import *

pk = pk_of(A)
best = full_height()
gs = list(range(best + 3, best + 8))
trees = {g: compile_tree('{ sigmaProp(HEIGHT == $G) && proveDlog(decodePoint(fromBase16("$PK"))) }',
                         {"$G": str(g), "$PK": pk}) for g in gs}
dep = send([{"address": trees[g][1], "value": 10_000_000} for g in gs])
wait_height(A, best + 5)
h = full_height()
rows = []
for g in gs:
    o = at(dep, trees[g][0])[0]
    tx = {"inputs": [{"boxId": o["boxId"], "extension": {}}], "dataInputs": [],
          "outputs": [out(o["value"], NOBODY_TREE, h)]}
    code, s = call(A, "/wallet/transaction/sign", {"tx": tx, "inputsRaw": [raw(o["boxId"])], "dataInputsRaw": []})
    row = {"guard": g, "sign": "signed" if code == 200 else str(s)[60:140]}
    if code == 200:
        c2, o2 = call(A, "/transactions/check", s)
        row["check"] = classify(c2, o2)
    rows.append(row)
res = {"fullHeight_before": h, "fullHeight_after": full_height(), "rows": rows}
print(json.dumps(res, indent=1))
json.dump(res, open(Path(__file__).parent / "probe-sign-height.json", "w"), indent=1)
