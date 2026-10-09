#!/usr/bin/env python3
"""Collect a staking incentive box's consolidation bounty, keyless, oldest boxes first (U1b follow-up, 2026-10-09).

The ErgoPad-style staking incentive contracts (explorer template hashes 278ccff2… and b924a4f7…; NETA and other
staking setups) have a path anyone may take with no key:

    every input of this script holds at most 0.1 ERG, and OUTPUTS.size == 3:
      OUTPUTS(0)  same script, value greater than each such input's value      (the merged box)
      OUTPUTS(1)  exactly 0.0005 ERG per input of this script, any script         (the executor's bounty)
      OUTPUTS(2)  exactly 0.001 ERG, any script                                   (used here as the miner fee)

Each of these boxes is about 770 bytes, so a storage-rent claim (about 0.96 ERG at today's factor) consumes it whole
once it is 1,051,200 blocks old. Merging creates a fresh box: the rent clock restarts and the protocol keeps the
value. Builds one transaction per call from the oldest boxes of one tree, checks it with a node, submits only with
--submit.

usage: consolidate.py --template <hash> --to <mainnet P2PK address> [--n 50] [--skip 0] [--tree-index 0]
                      [--node URL] [--submit] [--out tx.json]
"""
import argparse, collections, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import importlib
bt = importlib.import_module("babel-take")

BOUNTY, FEE, CAP = 500_000, 1_000_000, 100_000_000


def all_unspent(th):
    boxes, off = [], 0
    while True:
        d = bt.get(f"/boxes/unspent/byErgoTreeTemplateHash/{th}?limit=500&offset={off}")
        boxes += d["items"]
        off += 500
        if off >= d["total"]:
            return boxes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--to", required=True)
    ap.add_argument("--n", type=int, default=50, help="inputs per transaction; 600 passes a node check, 1,200 does not")
    ap.add_argument("--skip", type=int, default=0, help="skip the oldest N (boxes already in a pending transaction)")
    ap.add_argument("--tree-index", type=int, default=0, help="which distinct tree of the template, by box count")
    ap.add_argument("--node", default="http://128.253.41.100:9053")
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--out", default="consolidate-tx.json")
    a = ap.parse_args()

    # Boxes already spent by a transaction saved beside --out (submitted, maybe not yet mined) are left out
    used = set()
    for f in Path(a.out).resolve().parent.glob("*.json"):
        if f.resolve() != Path(a.out).resolve():
            used |= {i["boxId"] for i in json.load(open(f)).get("inputs", [])}
    boxes = [b for b in all_unspent(a.template)
             if b["value"] <= CAP and not b["assets"] and not b["additionalRegisters"] and b["boxId"] not in used]
    by = collections.defaultdict(list)
    for b in boxes:
        by[b["ergoTree"]].append(b)
    tree, group = sorted(by.items(), key=lambda kv: -len(kv[1]))[a.tree_index]
    group.sort(key=lambda b: (b["creationHeight"], b["boxId"]))
    pick = group[a.skip:a.skip + a.n]
    if len(pick) < 2:
        sys.exit("fewer than two boxes to merge")
    height = bt.get("/networkState")["height"]
    total = sum(b["value"] for b in pick)
    bounty = BOUNTY * len(pick)
    merged = total - bounty - FEE
    if merged <= max(b["value"] for b in pick):
        sys.exit("merged box would not exceed its largest input")

    tx = {
        "inputs": [{"boxId": b["boxId"], "spendingProof": {"proofBytes": "", "extension": {}}} for b in pick],
        "dataInputs": [],
        "outputs": [
            {"value": merged, "ergoTree": tree, "creationHeight": height, "assets": [], "additionalRegisters": {}},
            {"value": bounty, "ergoTree": bt.p2pk_tree(a.to), "creationHeight": height, "assets": [],
             "additionalRegisters": {}},
            {"value": FEE, "ergoTree": bt.FEE_TREE, "creationHeight": height, "assets": [], "additionalRegisters": {}},
        ],
    }
    json.dump(tx, open(a.out, "w"), indent=1)
    print(json.dumps({"height": height, "tree": tree[:24] + "…", "boxesInTree": len(group), "inputs": len(pick),
                      "oldest": pick[0]["creationHeight"], "newest": pick[-1]["creationHeight"],
                      "rentAgeAt": pick[0]["creationHeight"] + 1_051_200, "merged": merged, "bounty": bounty,
                      "to": a.to}, indent=1))
    code, text = bt.http(a.node + "/transactions/check", tx)
    print(f"node check {a.node}: {code} {text[:400]}")
    if code != 200:
        sys.exit(1)
    if a.submit:
        # The explorer refuses large bodies ("exhausted input" at 600 inputs); the node takes them
        code, text = bt.http(a.node + "/transactions", tx)
        print(f"submit: {code} {text[:400]}")
        if code != 200:
            sys.exit(1)


if __name__ == "__main__":
    main()
