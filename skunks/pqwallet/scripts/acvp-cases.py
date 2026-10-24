#!/usr/bin/env python3
"""Build the ACVP cases for the harness's `acvp` command (SLH-DSA-SHA2-128s, pure external and internal interfaces): M'
framed per interface, the expected verdict (sigVer testPassed; sigGen expected signatures are valid).
Usage: acvp-cases.py <acvp dir> <out cases.json>"""
import json, sys
from pathlib import Path
acvp, out = Path(sys.argv[1]), sys.argv[2]
PS = "SLH-DSA-SHA2-128s"; cases = []
def mprime(g, t):
    m = bytes.fromhex(t["message"])
    if g["signatureInterface"] == "internal": return m
    ctx = bytes.fromhex(t.get("context", "")); return bytes([0, len(ctx)]) + ctx + m
for kind in ("sigVer", "sigGen"):
    for g in json.load(open(acvp / f"{kind}-internalProjection.json"))["testGroups"]:
        if g["parameterSet"] != PS or g["preHash"] == "preHash": continue
        for t in g["tests"]:
            cases.append({"name": f"{kind}-tg{g['tgId']}-tc{t['tcId']}", "pk": t["pk"], "mprime": mprime(g, t).hex(), "sig": t["signature"],
                          "expected": bool(t["testPassed"]) if kind == "sigVer" else True, "reason": t.get("reason", "")})
json.dump({"cases": cases}, open(out, "w")); print(f"acvp-cases {len(cases)} cases ({sum(1 for c in cases if not c['expected'])} expected REFUSE) -> {out}")
