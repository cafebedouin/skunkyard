#!/usr/bin/env python3
"""Why a value-only bound is not enough: the boundary probe that decided the fix (part four).

The prompt's proposed fix was next.value <= total alone. This sweeps the completion payout V across
[total - bounty, total] against two variants of KeepAliveAddress:

  value-only:  the merge with next.value <= total but WITHOUT the no-foreign-input rule (the INPUTS.size line removed)
  full:        the shipped fix (no foreign input + value bound)

Row = the row-1 shape (P + K1 + K2 -> out0 = V, out1 = rest to a stranger). The value-only variant ACCEPTS every V
in the window (the executor still drains total - fee, because out1 = total - fee whatever V is); the full fix
REFUSES every one. That contrast is why the no-foreign-input rule, not the value bound, is the fix.

usage: devnet-test-shared-output2.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "policy"))
from common import *  # noqa: E402

DV = {"$PER_INPUTL": "500000L", "$REFRESHL": "2000000L", "$PERIOD": "40", "$WINDOW": "20", "$SLACK": "10"}
PER_INPUT = 500_000
A_VAL = B_VAL = 50_000_000
TOTAL = A_VAL + B_VAL
BOUNTY = min(2 * PER_INPUT, TOTAL - max(A_VAL, B_VAL))   # 1,000,000


def main():
    run = Run("shared-output-boundary", HERE, out="results-shared-output-boundary.json")
    owner, rec = pk_of(A), pk_of(B)
    full_src = (HERE / "KeepAliveAddress.es").read_text()
    # the value-only variant: the shipped source with the no-foreign-input clause removed
    value_only_src = "\n".join(l for l in full_src.splitlines() if "INPUTS.size == mine.size" not in l)
    assert "INPUTS.size == mine.size" in full_src and "INPUTS.size == mine.size" not in value_only_src

    pend, pend_addr = compile_tree((HERE.parent / "policy" / "2-twostep" / "Pending2.es").read_text(),
                                   {"$OWNER": owner, "$RECOVERY": rec})
    variants = {"value-only": compile_tree(value_only_src, dict(DV, **{"$OWNER": owner})),
                "full": compile_tree(full_src, dict(DV, **{"$OWNER": owner}))}
    run.doc["variants"] = {k: {"tree_bytes": len(v[0]) // 2} for k, v in variants.items()}
    run.save()

    def mk_pending(dt, value):
        past = full_height() - 1
        return at(send([{"address": pend_addr, "value": value,
                         "registers": {"R4": coll_bytes(dt), "R5": int_c(past), "R6": coll_bytes(dt)}}]), pend)[0]

    def mk_boxes(da, dt):
        return at(send([{"address": da, "value": A_VAL}, {"address": da, "value": B_VAL}]), dt)

    for name, (dt, da) in variants.items():
        exp = "ACCEPT" if name == "value-only" else "REFUSE"
        for lbl, V in [("V=total", TOTAL), ("V=total-bounty", TOTAL - BOUNTY), ("V=total-bounty//2", TOTAL - BOUNTY // 2)]:
            P = mk_pending(dt, V); K1, K2 = mk_boxes(da, dt)
            h = full_height()
            take = K1["value"] + K2["value"] + P["value"] - V - FEE
            outs = [out(V, dt, h, [], {"R4": coll_bytes(P["boxId"])})] + ([out(take, NOBODY_TREE, h)] if take > 0 else []) + [out(FEE, FEE_TREE, h)]
            tx = {"inputs": [inp(P["boxId"]), inp(K1["boxId"], {"0": "0400"}), inp(K2["boxId"], {"0": "0400"})],
                  "dataInputs": [], "outputs": outs}
            run.check(f"{name} {lbl}", f"{name} variant, shared output {lbl} (executor take={take})", tx, exp,
                      V=V, out1_take=take)
    bad = [c for c in run.doc["cases"] if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED of {len(run.doc['cases'])}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
