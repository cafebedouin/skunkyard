#!/usr/bin/env python3
"""SK-055 variant 2 cost probe, run right after devnet-test-v2.py on the same devnet: the node's mempool cost of a
plain keyless merge of two payments at NEAR, a merge-and-forward of two payments to NEAR', and a lone forward.
Reads the vault trees from devnet-results-v2.json. Usage: devnet-cost-probe-v2.py [--node URL] [--results FILE]"""
import argparse, importlib.util, json, time
from pathlib import Path
HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("kt", HERE.parent / "keepalive" / "devnet-test.py")
kt = importlib.util.module_from_spec(spec); spec.loader.exec_module(kt)
call, must, height, wait_tx_outputs = kt.call, kt.must, kt.height, kt.wait_tx_outputs
FEE, FEE_TREE, PER_INPUT = kt.FEE, kt.FEE_TREE, 500_000
ap = argparse.ArgumentParser(); ap.add_argument("--node", default="http://127.0.0.1:9181"); ap.add_argument("--results", default="devnet-results-v2.json")
a = ap.parse_args(); base = a.node
v = json.load(open(HERE / a.results))["vaults"]
near, nearp = v["NEAR"], v["NEAR'"]
addr = must(base, f"/utils/ergoTreeToAddress/{near['tree']}")["address"]

def pay(vals):
    tx = wait_tx_outputs(base, must(base, "/wallet/transaction/send", {"requests": [{"address": addr, "value": x} for x in vals], "fee": FEE}))
    return [[o for o in tx["outputs"] if o["ergoTree"] == near["tree"] and o["value"] == x][0] for x in vals]

def keyless(inputs, to_tree, h):
    total = sum(b["value"] for b in inputs)
    bounty = min(len(inputs) * PER_INPUT, total - max(b["value"] for b in inputs)) if len(inputs) > 1 else min(inputs[0]["value"] // 2, 2_000_000)
    outs = [{"value": total - bounty, "ergoTree": to_tree, "creationHeight": h, "assets": [], "additionalRegisters": {}},
            {"value": bounty, "ergoTree": FEE_TREE, "creationHeight": h, "assets": [], "additionalRegisters": {}}]
    return {"inputs": [{"boxId": b["boxId"], "spendingProof": {"proofBytes": "", "extension": {"0": "0400"}}} for b in inputs], "dataInputs": [], "outputs": outs}

def submit_cost(label, tx):
    code, tid = call(base, "/transactions", tx)
    assert code == 200, (label, tid)
    cost = size = None
    for _ in range(40):
        c2, u = call(base, f"/transactions/unconfirmed/byTransactionId/{tid}")
        if c2 == 200 and isinstance(u, dict):
            cost, size = u.get("cost"), u.get("size"); break
        time.sleep(0.25)
    print(f"cost-probe {label} tx={tid[:8]} inputs={len(tx['inputs'])} mempool_cost={cost} size={size}")
    wait_tx_outputs(base, tid)
    return must(base, f"/blockchain/transaction/byId/{tid}") if False else None

p1, p2, p3, p4 = pay([21_000_000, 22_000_000, 23_000_000, 24_000_000])
h = height(base)
submit_cost("plain_merge_2_at_NEAR", keyless([p1, p2], near["tree"], h))
submit_cost("merge_forward_2_to_NEARprime", keyless([p3, p4], nearp["tree"], h))
p5, = pay([25_000_000])
submit_cost("lone_forward_1_to_NEARprime", keyless([p5], nearp["tree"], height(base)))
