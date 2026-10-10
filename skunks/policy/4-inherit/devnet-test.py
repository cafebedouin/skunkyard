#!/usr/bin/env python3
"""Experiment 4: inheritance alongside KeepAlive (Inherit.es) on the `policy` devnet.

Node A's wallet holds the owner key; node B's wallet holds the heir key (not the owner's). Deposit at h0 with
R5 = h0; refresh window from h0 + 20; heir window at R5 + N = h0 + 30, when the refreshed box is about 10 blocks old.

Heights. /wallet/transaction/sign reduces at HEIGHT = fullHeight, /transactions/check at fullHeight + 1 (experiment
2, probe-sign-height.json). A key-path case "at R5 + N" is therefore run where the SIGNING wallet sees that height
(fullHeight = R5 + N); the node then checks it at R5 + N + 1. The case table states both.

   1  in the window: refresh with R5 bumped to HEIGHT                    REFUSE node-check              sibling 2
   2  in the window: refresh, R5 kept, honest                            ACCEPT (mined)
   3  heir (B) at wallet height R5 + N - 1                               REFUSE wallet-sign/no-secret   sibling 4
   4  heir (B) at wallet height R5 + N, on the refreshed box (age < N)   ACCEPT (checked)
   5  owner (A) spends into a successor with R5 = HEIGHT + 1             REFUSE wallet-sign/no-secret   sibling 7
   6  owner (A) spends into a successor with R5 = h0 (old)               REFUSE wallet-sign/no-secret   sibling 7
   7  owner (A) resets R5 = HEIGHT after the heir's window opened (R1)   ACCEPT (mined), default, unruled
   8  heir (B) right after case 7                                        REFUSE wallet-sign/no-secret   sibling 9
   9  heir (B) at the new R5 + N                                         ACCEPT (mined)
"""
import sys, time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from common import *  # noqa: E402

N, PERIOD, WINDOW, BOUNTY, SLACK = 30, 40, 20, 2_000_000, 10
V = 100_000_000


def at_full(h, base=None):
    """Wait until the SIGNING node's fullHeight == h exactly (its wallet reduces at its own fullHeight; B trails A),
    and A has it too; stop on an overshoot. Run 1 waited on A only (results-run1.json, harness_bugs)."""
    base = base or A
    while full_height(base) < h or full_height(A) < h:
        time.sleep(1)
    got = full_height(base)
    if got != h:
        raise SystemExit(f"overshot fullHeight {h} on {base}: {got}")
    return got


def main():
    run = Run("4-inherit", HERE)
    owner, heir = pk_of(A), pk_of(B)
    t, addr = compile_tree((HERE / "Inherit.es").read_text(), {"$HEIR": heir, "$N": str(N), "$PERIOD": str(PERIOD),
                                                               "$WINDOW": str(WINDOW), "$BOUNTYL": f"{BOUNTY}L",
                                                               "$SLACK": str(SLACK)})
    tok = issue("INHERIT", 1)
    h0 = full_height()
    dep = send([{"address": addr, "value": V, "assets": [{"tokenId": tok, "amount": 1}],
                 "registers": {"R4": sigprop_c(owner), "R5": int_c(h0)}}])
    X = at(dep, t)[0]
    run.tree("Inherit", t, addr, X["boxId"])
    run.doc["h0"], run.doc["deposit_created"] = h0, X["creationHeight"]
    created = X["creationHeight"]
    dest = "0008cd" + pk_of(A, 2)
    heir_dest = "0008cd" + pk_of(B, 1)

    def refresh(box, h, r5):
        regs = {"R4": sigprop_c(owner), "R5": int_c(r5), "R6": coll_bytes(box["boxId"])}
        outs = [out(box["value"] - BOUNTY, t, h, box["assets"], regs), out(BOUNTY, FEE_TREE, h)]
        return {"inputs": [inp(box["boxId"], {"0": "0400"})], "dataInputs": [], "outputs": outs}

    # ---- refresh window (evaluated HEIGHT = fullHeight + 1 >= created + PERIOD - WINDOW)
    wait_height(A, created + PERIOD - WINDOW)
    h = full_height()
    run.check(1, "in the window: refresh with R5 bumped to HEIGHT", refresh(X, h, h + 1), "REFUSE", sibling=2)
    m = run.check(2, "in the window: refresh, R5 kept, honest", refresh(X, h, h0), "ACCEPT", submit=True)
    Y = at(m, t)[0]
    run.tree("Inherit-refreshed", t, addr, Y["boxId"])

    def heir_spend(n, label, box, expect, sibling=None, submit=False, cost=False):
        h = full_height(B)
        return run.key_spend(n, label, B, [box["boxId"]], [], [out(box["value"], heir_dest, h, box["assets"])],
                             expect, sibling, submit=submit, cost=cost, wallet_height=h, box_age=h - box["creationHeight"])

    run.bug("run1", "case 4 refused: at_full waited on node A's height, but B signs and B's wallet reduces at B's own "
                    "fullHeight, which trailed A's by one (results-run1.json)",
            "at_full waits on the signing node; experiment rerun on a fresh deposit")
    at_full(h0 + N - 1, B)
    heir_spend(3, "heir (B) at wallet height R5 + N - 1", Y, "REFUSE", sibling=4)
    at_full(h0 + N, B)
    heir_spend(4, "heir (B) at wallet height R5 + N, on the refreshed box (its age < N)", Y, "ACCEPT", cost=False)

    def owner_spend(n, label, box, r5, expect, sibling=None, submit=False):
        h = full_height()
        regs = {"R4": sigprop_c(owner), "R5": int_c(r5)}
        return run.key_spend(n, label, A, [box["boxId"]], [], [out(box["value"], t, h, box["assets"], regs)],
                             expect, sibling, submit=submit, wallet_height=h, successor_r5=r5)

    h = full_height()
    owner_spend(5, "owner (A) spends into a successor with R5 = HEIGHT + 1 (node HEIGHT)", Y, h + 2, "REFUSE", sibling=7)
    owner_spend(6, "owner (A) spends into a successor with R5 = h0, the old value", Y, h0, "REFUSE", sibling=7)
    m = owner_spend(7, "owner (A) resets R5 = HEIGHT after the heir's window opened (R1 default)", Y, h, "ACCEPT",
                    submit=True)
    Z = at(m, t)[0]
    r5z = h          # the R5 case 7 wrote
    heir_spend(8, "heir (B) right after case 7", Z, "REFUSE", sibling=9)
    at_full(r5z + N, B)
    heir_spend(9, "heir (B) at the new R5 + N", Z, "ACCEPT", submit=True, cost=True)
    bad = [c for c in run.doc["cases"] if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


if __name__ == "__main__":
    main()
