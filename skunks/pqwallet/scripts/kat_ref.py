#!/usr/bin/env python3
"""FIPS 205 known-answer vectors (NIST ACVP) through the Python reference verifier skunks/policy/6-rekey/slhdsa/slhdsa_ref.py,
SLH-DSA-SHA2-128s. The reference verifies only (pure external with a context, and the internal interface); for sigGen
groups it verifies the expected signature. Usage: kat_ref.py <acvp dir> <slhdsa dir>"""
import importlib.util, json, sys, time
from pathlib import Path

acvp, slh = Path(sys.argv[1]), Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("slhdsa_ref", slh / "slhdsa_ref.py")
ref = importlib.util.module_from_spec(spec); spec.loader.exec_module(ref)
PS = "SLH-DSA-SHA2-128s"
fails = total = 0
def check(name, cond, detail=""):
    global fails, total
    total += 1
    if not cond:
        fails += 1; print(f"FAIL {name} {detail}")

def verdict(g, t):
    pk, sig, m = bytes.fromhex(t["pk"]), bytes.fromhex(t["signature"]), bytes.fromhex(t["message"])
    try:
        if g["signatureInterface"] == "internal":
            return ref.verify_internal(m, sig, pk)
        return ref.verify(m, bytes.fromhex(t.get("context", "")), sig, pk)
    except Exception:
        return False

t0 = time.time()
for g in json.load(open(acvp / "sigGen-internalProjection.json"))["testGroups"]:
    if g["parameterSet"] != PS or g["preHash"] == "preHash": continue
    for t in g["tests"]:
        check(f"sigGen tg{g['tgId']} tc{t['tcId']} (expected signature verifies)", verdict(g, t))
    print(f"kat-ref sigGen tg{g['tgId']} {g['signatureInterface']}/{g['preHash']} tests={len(g['tests'])}")
for g in json.load(open(acvp / "sigVer-internalProjection.json"))["testGroups"]:
    if g["parameterSet"] != PS or g["preHash"] == "preHash": continue
    neg = 0
    for t in g["tests"]:
        check(f"sigVer tg{g['tgId']} tc{t['tcId']}", verdict(g, t) == t["testPassed"], f"expected {t['testPassed']} ({t.get('reason','')})")
        neg += (not t["testPassed"])
    print(f"kat-ref sigVer tg{g['tgId']} {g['signatureInterface']}/{g['preHash']} tests={len(g['tests'])} negatives={neg}")
print(f"kat-ref python reference {PS}: checks={total} failures={fails} {'ALL PASS' if fails == 0 else 'FAILED'} seconds={time.time()-t0:.1f}")
sys.exit(0 if fails == 0 else 1)
