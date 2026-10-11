#!/usr/bin/env python3
"""278ccff2 theft rows again with a token-bearing foreign box, so the stake path's INPUTS(0).tokens(0) read
does not throw and the verdict is the script's own."""
import json, sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "policy"))
from common import *  # noqa
PER, OUT2, KV = 500_000, 1_000_000, 50_000_000
def main():
    run = Run("staking-shared-output-tokrow", HERE, out="results-staking-tokrow.json")
    true_t, true_addr = compile_tree("{ sigmaProp(true) }", {})
    tree = (HERE / "staking-278ccff2.tree").read_text().strip()
    addr = must(A, f"/utils/ergoTreeToAddress/{tree}")["address"]
    tok = issue("STAKETOK", 10)
    for n, fold in (("theft4-tok", False), ("theft3-tok", True)):
        K1, K2 = at(send([{"address": addr, "value": KV}, {"address": addr, "value": KV}]), tree)
        Pb = at(send([{"address": true_addr, "value": 200_000_000, "assets": [{"tokenId": tok, "amount": 1}]}]), true_t)[0]
        h = full_height(); take = 2*KV - 2*PER - OUT2; T = [{"tokenId": tok, "amount": 1}]
        outs = [out(Pb["value"], tree, h, T), out(2*PER + (take if fold else 0), NOBODY_TREE, h), out(OUT2, FEE_TREE, h)]
        if not fold: outs.append(out(take, NOBODY_TREE, h))
        run.check(f"278ccff2-{n}", f"278ccff2 theft, token-bearing foreign box, {'folded' if fold else 'fourth output'}",
                  {"inputs": [inp(Pb["boxId"]), inp(K1["boxId"]), inp(K2["boxId"])], "dataInputs": [], "outputs": outs}, "REFUSE")
main()
