#!/usr/bin/env python3
"""The shared-output theft shape against the two ErgoPad-style staking incentive trees (exact mainnet
trees, network-independent), judged by the policy devnet node's /transactions/check. Consolidation path as
decompiled: SELF.value <= 0.1 ERG, OUTPUTS.size == 3, OUTPUTS(0) same script and > SELF.value,
OUTPUTS(1).value == 500000 * #inputs at the script, OUTPUTS(2).value == 1000000."""
import json, sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "policy"))
from common import *  # noqa

PER, OUT2 = 500_000, 1_000_000
KV = 50_000_000

def main():
    run = Run("staking-shared-output", HERE, out="results-staking-shared-output.json")
    true_t, true_addr = compile_tree("{ sigmaProp(true) }", {})
    stranger = NOBODY_TREE
    for name in ("278ccff2-r01", "b924a4f7-r06"):
        tree = (HERE / f"staking-{name[:8]}.tree").read_text().strip()
        addr = must(A, f"/utils/ergoTreeToAddress/{tree}")["address"]
        run.tree(f"staking-{name[:8]}", tree, addr)
        def boxes():
            return at(send([{"address": addr, "value": KV}, {"address": addr, "value": KV}]), tree)
        def foreign(v):
            return at(send([{"address": true_addr, "value": v}]), true_t)[0]
        t = name[:8]
        # 1 honest consolidation
        K1, K2 = boxes(); h = full_height()
        tx = {"inputs": [inp(K1["boxId"]), inp(K2["boxId"])], "dataInputs": [],
              "outputs": [out(2*KV - 2*PER - OUT2, tree, h), out(2*PER, stranger, h), out(OUT2, FEE_TREE, h)]}
        run.check(f"{t}-honest", f"{t} honest consolidation, 2 boxes", tx, "ACCEPT")
        # 2 shared-output theft: a foreign payout P stands in for out0, the merged value leaves in a 4th output
        K1, K2 = boxes(); Pb = foreign(200_000_000); h = full_height()
        take = 2*KV - 2*PER - OUT2
        tx = {"inputs": [inp(Pb["boxId"]), inp(K1["boxId"]), inp(K2["boxId"])], "dataInputs": [],
              "outputs": [out(Pb["value"], tree, h), out(2*PER, stranger, h), out(OUT2, FEE_TREE, h), out(take, stranger, h)]}
        run.check(f"{t}-theft4", f"{t} shared-output theft, take {take} in a fourth output", tx, "REFUSE", V=Pb["value"], take=take)
        # 3 the take folded into OUTPUTS(1)
        K1, K2 = boxes(); Pb = foreign(200_000_000); h = full_height()
        tx = {"inputs": [inp(Pb["boxId"]), inp(K1["boxId"]), inp(K2["boxId"])], "dataInputs": [],
              "outputs": [out(Pb["value"], tree, h), out(2*PER + take, stranger, h), out(OUT2, FEE_TREE, h)]}
        run.check(f"{t}-theft3", f"{t} shared-output theft, take folded into OUTPUTS(1)", tx, "REFUSE", V=Pb["value"], take=take)
        # 4 foreign input admitted, three outputs: every extra nanoERG lands at the staking script
        K1, K2 = boxes(); Pb = foreign(200_000_000); h = full_height()
        tx = {"inputs": [inp(Pb["boxId"]), inp(K1["boxId"]), inp(K2["boxId"])], "dataInputs": [],
              "outputs": [out(Pb["value"] + 2*KV - 2*PER - OUT2, tree, h), out(2*PER, stranger, h), out(OUT2, FEE_TREE, h)]}
        run.check(f"{t}-foreign3", f"{t} foreign input, three outputs (executor take = bounty only)", tx, "ACCEPT",
                  note="conservation: OUTPUTS(1) and (2) are exact, so the foreign value and the merged value stay at the script")
    bad = [c for c in run.doc["cases"] if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED of {len(run.doc['cases'])}")

if __name__ == "__main__":
    main()
