#!/usr/bin/env python3
"""Fixed-key rekey-by-move baseline (FixedKey.es), program item 3.

The fixed-key address (owner key a script constant) accepts plain payments safely with no token and no watcher. Its
rekey is not in place: the owner moves every box at the old address to a new fixed-key address in one owner-signed
transaction. This measures the per-box cost of that move -- the baseline the in-place rotating-key variants (NFT
account 14,791 per merged box; key schedule) must beat.

Not an exploit; a legitimate cost measurement, so it lives in the public repo next to the contracts.

Rows (A = owner key pa; the new address uses A's key index 2):
  fixed-move  owner moves N plain boxes at the old fixed-key address into one box at a new one   ACCEPT (mined) + cost
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from common import *  # noqa: E402

N = 4            # boxes to move (one registered-equivalent payment plus three later plain payments)
VP = 40_000_000


def main():
    run = Run("6-rekey-fixedkey", HERE, out="results-fixedkey.json")
    pa_old, pa_new = pk_of(A, 1), pk_of(A, 2)
    # the fixed key is the native P2PK (0008cd || key); FixedKey.es is the readable form of the same script. We
    # measure the canonical P2PK, the cheapest fixed key, so the baseline is the floor the rotating variants must beat.
    # The old address uses A's index-1 key (A can sign it); the send's change returns to index 0, so it does not
    # land at the old address and inflate the box count.
    old_tree = "0008cd" + pa_old
    new_tree = "0008cd" + pa_new
    old_addr = must(A, "/wallet/addresses")[1]
    run.tree("FixedKey", old_tree, old_addr)

    dep = send([{"address": old_addr, "value": VP} for _ in range(N)])
    boxes = at(dep, old_tree)
    assert len(boxes) == N, f"expected {N} boxes, got {len(boxes)}"

    h = full_height()
    total = sum(b["value"] for b in boxes)
    moved = run.key_spend("fixed-move", f"owner moves {N} boxes at the old fixed-key address into one at a new one",
                          A, [b["boxId"] for b in boxes], [], [out(total, new_tree, h)], "ACCEPT",
                          submit=True, cost=True, n_boxes=N)
    row = [c for c in run.doc["cases"] if c["n"] == "fixed-move"][0]
    if row.get("cost"):
        row["cost_per_box"] = row["cost"] / N
        run.save()
        print(f"move cost {row['cost']} for {N} boxes = {row['cost'] / N:.0f} per box")
    bad = [c for c in run.doc["cases"] if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


if __name__ == "__main__":
    main()
