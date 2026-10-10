#!/usr/bin/env python3
"""Experiment 2, added rows (2026-10-10): the cancel-side double satisfaction, which the first run guarded in
Pending.es but did not run as a row (EXPERIMENTS.md section 2, "Not run as a row").

Before the deadline, the recovery key cancels two pending boxes; OUTPUTS(0) goes back to the vault with one box's
value, OUTPUTS(1) to a stranger with the other's. Pending.es's "alone" clause covers cancel as well as complete;
PendingNoGuard.es is the counterfactual. Rows are appended to results.json.

  16    recovery key cancels P6 + P7: one back to the vault, one to a stranger        REFUSE  sibling 16.s
  16.s  recovery key cancels P6 alone, checked                                        ACCEPT
  17    the same as 16 on two PendingNoGuard boxes (the theft without the guard)      ACCEPT (checked)
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from common import *  # noqa: E402

DELAY = 15
V = 50_000_000


def main():
    run = Run("2-twostep", HERE)
    run.doc = json.loads(run.path.read_text())
    owner, rec = pk_of(A), pk_of(B)
    x_tree = run.doc["X"]
    pend, _ = compile_tree((HERE / "Pending.es").read_text(), {"$OWNER": owner, "$RECOVERY": rec})
    ng, ng_addr = compile_tree((HERE / "PendingNoGuard.es").read_text(), {"$OWNER": owner, "$RECOVERY": rec})
    vt, vaddr = compile_tree((HERE / "Vault.es").read_text(), {"$OWNER": owner, "$PENDING_TREE": pend,
                                                               "$DELAY": str(DELAY)})
    V6, V7 = at(send([{"address": vaddr, "value": V} for _ in range(2)]), vt)
    H = full_height() + 1
    r5 = H + DELAY + 5
    pend_out = lambda v: out(v["value"], pend, H - 1, [], {"R4": coll_bytes(x_tree), "R5": int_c(r5),
                                                           "R6": coll_bytes(vt)})
    P6 = at(run.key_spend("16.a", "announce V6 -> P6", A, [V6["boxId"]], [], [pend_out(V6)], "ACCEPT", submit=True),
            pend)[0]
    P7 = at(run.key_spend("16.b", "announce V7 -> P7", A, [V7["boxId"]], [], [pend_out(V7)], "ACCEPT", submit=True),
            pend)[0]
    future = full_height() + DELAY
    ngd = send([{"address": ng_addr, "value": V, "registers": {"R4": coll_bytes(x_tree), "R5": int_c(future),
                                                                "R6": coll_bytes(vt)}} for _ in range(2)])
    N1, N2 = at(ngd, ng)
    h = full_height()
    two = lambda a, b: [out(a["value"], vt, h), out(b["value"], NOBODY_TREE, h)]
    run.key_spend(16, "recovery key cancels P6 + P7: one back to the vault, one to a stranger", B,
                  [P6["boxId"], P7["boxId"]], [], two(P6, P7), "REFUSE", sibling="16.s")
    run.key_spend("16.s", "recovery key cancels P6 alone, checked", B, [P6["boxId"]], [], [out(P6["value"], vt, h)],
                  "ACCEPT")
    run.key_spend(17, "the same as 16 on two PendingNoGuard boxes (the theft without the guard), checked", B,
                  [N1["boxId"], N2["boxId"]], [], two(N1, N2), "ACCEPT")
    run.save()
    new = [c for c in run.doc["cases"] if str(c["n"]).startswith(("16", "17"))]
    bad = [c for c in new if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


if __name__ == "__main__":
    main()
