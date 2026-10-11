#!/usr/bin/env python3
"""Fixed-key move at 1, 2, 4 and 8 boxes (prompts/policy-post-devnet-fixes-3.md, item B.13).

results-fixedkey.json measured one move of four boxes (19,712, quoted as 4,928 per box). A per-box quarter of a
four-box transaction is not like for like with a one-box or a merge figure, because most of a small transaction's
cost is the per-transaction charge. This measures the move at each size, beside the schedule's keyless merge at 2,
4 and 8 inputs (results-schedule-r3.json, r3-merge-2/4/8). Same construction as devnet-test-fixedkey.py: the native
P2PK at A's index-1 key, moved to index 2, one output. Public (a cost measurement).
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from common import *  # noqa: E402

VP = 40_000_000


def main():
    run = Run("6-rekey-fixedkey-n", HERE, out="results-fixedkey-n.json")
    old_tree, new_tree = "0008cd" + pk_of(A, 1), "0008cd" + pk_of(A, 2)
    old_addr = must(A, "/wallet/addresses")[1]
    for n in (1, 2, 4, 8):
        boxes = at(send([{"address": old_addr, "value": VP + i} for i in range(n)]), old_tree)
        assert len(boxes) == n, f"expected {n} boxes, got {len(boxes)}"
        h = full_height()
        run.key_spend(f"fixed-move-{n}", f"owner moves {n} box(es) at the fixed-key address into one at a new one", A,
                      [b["boxId"] for b in boxes], [], [out(sum(b["value"] for b in boxes), new_tree, h)], "ACCEPT",
                      submit=True, cost=True, n_boxes=n, n_outputs=1)
    for c in run.doc["cases"]:
        print(c["n"], c.get("cost"))
    bad = [c for c in run.doc["cases"] if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


if __name__ == "__main__":
    main()
