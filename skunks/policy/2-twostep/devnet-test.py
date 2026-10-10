#!/usr/bin/env python3
"""Experiment 2: two-step withdrawal vault (Vault.es, Pending.es, PendingNoGuard.es) on the `policy` devnet.

Node A's wallet holds the owner key; node B's wallet holds the recovery key (and not the owner's). DELAY 15 blocks.
"At R5" means the evaluated HEIGHT (fullHeight + 1, preflight S14) equals the pending box's deadline.

   1   owner spends V1 straight to X                                      REFUSE wallet-sign      sibling 3
   2   owner announces V1 with R5 = HEIGHT + DELAY - 1                    REFUSE wallet-sign      sibling 3
   2b  owner announces V3 and V4 into ONE pending box, V4's value out      REFUSE wallet-sign      sibling 2b.s
   3   owner announces V1 to X, honest                                    ACCEPT (mined) -> P1
   4   complete P1 at R5 - 1                                              REFUSE node-check       sibling 7
   5   at R5: complete P1 to Y != X                                       REFUSE node-check       sibling 7
   6   at R5: complete P1 keeping value - 0.001 ERG                       REFUSE node-check       sibling 7
   7   at R5: complete P1 to X, honest                                    ACCEPT (mined)
   8   announce V2 -> P2 (mined); a stranger cancels P2, empty proof      REFUSE node-check       sibling 9
   9   recovery key (B) cancels P2 before R5, back to the vault           ACCEPT (mined)
  10   P3, P4 announced (mined); owner cancels P3 at R5 - 1               ACCEPT (checked)
  11   at R5 of P3: owner cancels P3                                      REFUSE wallet-sign      sibling 10
  12   at R5: P3 + P4, OUTPUTS(0) -> X v, OUTPUTS(1) -> stranger v        REFUSE node-check       sibling 12.s
  13   at R5: P3 + P4, both to X (honest batching)                        REFUSE node-check       sibling 12.s
  14   two PendingNoGuard boxes, case 12's shape                          ACCEPT (checked)
  15   two PendingNoGuard boxes, case 13's shape                          ACCEPT (checked)
"""
import json, sys, time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from common import *  # noqa: E402

DELAY = 15
V = 50_000_000


def at_height(H):
    """Wait until the evaluated HEIGHT is H (fullHeight == H - 1). Fails if already past."""
    h = full_height()
    if h > H - 1:
        raise SystemExit(f"missed height {H}: fullHeight already {h}")
    while full_height() < H - 1:
        time.sleep(1)
    h = full_height()
    if h != H - 1:
        raise SystemExit(f"overshot height {H}: fullHeight {h}")
    return h


def rerun_4():
    """Case 4 rerun (harness bug: the first run's at_height overshot by a block, so case 4 was checked at R5, not
    R5 - 1). A fresh vault, announced, then complete at exactly R5 - 1 (REFUSE) and at R5 (4.s, ACCEPT, mined)."""
    run = Run("2-twostep", HERE)
    run.doc = json.loads(run.path.read_text())
    run.doc["cases"] = [c for c in run.doc["cases"] if c["n"] != 4]
    run.bug(4, "at_height polled every 5 s and did not verify the landing height; two quick blocks put the check at "
               "fullHeight 117 (HEIGHT 118 = R5) instead of 116, and the node accepted the completion (correctly, at R5)",
            "at_height polls every second and stops on an overshoot; case 4 rerun on a fresh vault, rows 4 and 4.s")
    owner, rec = pk_of(A), pk_of(B)
    x_tree = run.doc["X"]
    pend, _ = compile_tree((HERE / "Pending.es").read_text(), {"$OWNER": owner, "$RECOVERY": rec})
    vt, vaddr = compile_tree((HERE / "Vault.es").read_text(), {"$OWNER": owner, "$PENDING_TREE": pend,
                                                               "$DELAY": str(DELAY)})
    V5 = at(send([{"address": vaddr, "value": V}]), vt)[0]
    H = full_height() + 1
    m = run.key_spend("4.a", "announce V5 -> P5 (for the case 4 rerun)", A, [V5["boxId"]], [],
                      [out(V5["value"], pend, H - 1, [], {"R4": coll_bytes(x_tree), "R5": int_c(H + DELAY),
                                                          "R6": coll_bytes(vt)})], "ACCEPT", submit=True)
    P5, r5 = at(m, pend)[0], H + DELAY
    tx = lambda h: {"inputs": [inp(P5["boxId"])], "dataInputs": [], "outputs": [out(P5["value"], x_tree, h)]}
    h = at_height(r5 - 1)
    run.check(4, "complete P5 at R5 - 1 (rerun)", tx(h), "REFUSE", sibling="4.s", r5=r5)
    h = at_height(r5)
    run.check("4.s", "complete P5 at R5 (sibling of 4, one block later)", tx(h), "ACCEPT", submit=True, r5=r5)


def main():
    if "--rerun-4" in sys.argv:
        return rerun_4()
    run = Run("2-twostep", HERE)
    owner, rec = pk_of(A), pk_of(B)
    x_tree = "0008cd" + pk_of(A, 2)          # the destination X
    y_tree = NOBODY_TREE                     # another destination, and the stranger
    pend, pend_addr = compile_tree((HERE / "Pending.es").read_text(), {"$OWNER": owner, "$RECOVERY": rec})
    ng, ng_addr = compile_tree((HERE / "PendingNoGuard.es").read_text(), {"$OWNER": owner, "$RECOVERY": rec})
    vt, vaddr = compile_tree((HERE / "Vault.es").read_text(), {"$OWNER": owner, "$PENDING_TREE": pend,
                                                               "$DELAY": str(DELAY)})
    tok = issue("TWOSTEP", 10)
    dep = send([{"address": vaddr, "value": V, "assets": [{"tokenId": tok, "amount": 1}]} for _ in range(4)])
    V1, V2, V3, V4 = at(dep, vt)
    run.tree("Vault", vt, vaddr, V1["boxId"])
    run.doc["recovery_key"], run.doc["owner_key"], run.doc["X"] = rec, owner, x_tree

    def pending_out(v, dest, r5, tree=pend, value=None, h=None):
        return out(value if value is not None else v["value"], tree, h or full_height(), v["assets"],
                   {"R4": coll_bytes(dest), "R5": int_c(r5), "R6": coll_bytes(vt)})

    def announce(n, label, v, r5, expect, sibling=None, submit=False):
        return run.key_spend(n, label, A, [v["boxId"]], [], [pending_out(v, x_tree, r5)], expect, sibling, submit)

    # ---- the gate
    H = full_height() + 1
    run.key_spend(1, "owner spends V1 straight to X", A, [V1["boxId"]], [], [out(V1["value"], x_tree, H - 1,
                  V1["assets"])], "REFUSE", sibling=3)
    announce(2, "owner announces V1 with R5 = HEIGHT + DELAY - 1", V1, H + DELAY - 1, "REFUSE", sibling=3)
    two = [pending_out(V3, x_tree, H + DELAY), out(V4["value"], y_tree, H - 1, V4["assets"])]
    run.key_spend("2b", "owner announces V3 and V4 into one pending box, V4's value out", A,
                  [V3["boxId"], V4["boxId"]], [], two, "REFUSE", sibling="2b.s")
    run.key_spend("2b.s", "owner announces V3 alone (sibling of 2b), checked", A, [V3["boxId"]], [],
                  [pending_out(V3, x_tree, H + DELAY)], "ACCEPT")
    H = full_height() + 1
    m = announce(3, "owner announces V1 to X, honest", V1, H + DELAY, "ACCEPT", submit=True)
    P1 = at(m, pend)[0]
    r5_1 = H + DELAY
    run.tree("Pending", pend, pend_addr, P1["boxId"])

    # ---- cancel by the recovery key, P2
    H = full_height() + 1
    m = announce("8.a", "announce V2 -> P2", V2, H + DELAY, "ACCEPT", submit=True)
    P2 = at(m, pend)[0]
    h = full_height()
    back = [out(P2["value"], vt, h, P2["assets"])]
    run.check(8, "a stranger cancels P2 before R5, empty proof", {"inputs": [inp(P2["boxId"])], "dataInputs": [],
              "outputs": back}, "REFUSE", sibling=9)
    run.key_spend(9, "recovery key (B) cancels P2 before R5, back to the vault", B, [P2["boxId"]], [], back,
                  "ACCEPT", submit=True)

    # ---- P3, P4 with one deadline
    r5_3 = full_height() + 1 + DELAY + 2
    m3 = announce("10.a", "announce V3 -> P3", V3, r5_3, "ACCEPT", submit=True)
    m4 = announce("10.b", "announce V4 -> P4", V4, r5_3, "ACCEPT", submit=True)
    P3, P4 = at(m3, pend)[0], at(m4, pend)[0]

    # ---- NoGuard boxes for the counterfactual: deadline already passed
    past = full_height() - 1
    ngd = send([{"address": ng_addr, "value": V, "assets": [{"tokenId": tok, "amount": 1}],
                 "registers": {"R4": coll_bytes(x_tree), "R5": int_c(past), "R6": coll_bytes(vt)}} for _ in range(2)])
    N1, N2 = at(ngd, ng)
    run.tree("PendingNoGuard", ng, ng_addr, N1["boxId"])

    def complete(boxes, outs):
        return {"inputs": [inp(b["boxId"]) for b in boxes], "dataInputs": [], "outputs": outs}

    # ---- complete P1 around its deadline
    at_height(r5_1 - 1)
    h = full_height()
    run.check(4, "complete P1 at R5 - 1", complete([P1], [out(P1["value"], x_tree, h, P1["assets"])]), "REFUSE",
              sibling=7)
    at_height(r5_1)
    h = full_height()
    run.check(5, "at R5: complete P1 to Y != X", complete([P1], [out(P1["value"], y_tree, h, P1["assets"])]),
              "REFUSE", sibling=7)
    run.check(6, "at R5: complete P1 keeping value - 0.001 ERG (the rest to a stranger)",
              complete([P1], [out(P1["value"] - 1_000_000, x_tree, h, P1["assets"]), out(1_000_000, y_tree, h)]),
              "REFUSE", sibling=7)
    run.check(7, "at R5: complete P1 to X, honest", complete([P1], [out(P1["value"], x_tree, h, P1["assets"])]),
              "ACCEPT", submit=True, cost=True)

    # ---- P3 around its deadline
    at_height(r5_3 - 1)
    h = full_height()
    run.key_spend(10, "owner cancels P3 at R5 - 1", A, [P3["boxId"]], [], [out(P3["value"], vt, h, P3["assets"])],
                  "ACCEPT")
    at_height(r5_3)
    h = full_height()
    run.key_spend(11, "at R5: owner cancels P3", A, [P3["boxId"]], [], [out(P3["value"], vt, h, P3["assets"])],
                  "REFUSE", sibling=10)
    run.check("12.s", "at R5: complete P3 alone to X (sibling of 12, 13), checked",
              complete([P3], [out(P3["value"], x_tree, h, P3["assets"])]), "ACCEPT")
    run.check(12, "at R5: P3 + P4, OUTPUTS(0) -> X v, OUTPUTS(1) -> stranger v",
              complete([P3, P4], [out(V, x_tree, h, P3["assets"]), out(V, y_tree, h, P4["assets"])]), "REFUSE",
              sibling="12.s")
    run.check(13, "at R5: P3 + P4, both to X (honest batching)",
              complete([P3, P4], [out(V, x_tree, h, P3["assets"]), out(V, x_tree, h, P4["assets"])]), "REFUSE",
              sibling="12.s")
    h = full_height()
    run.check(14, "two PendingNoGuard boxes, case 12's shape (the theft)",
              complete([N1, N2], [out(V, x_tree, h, N1["assets"]), out(V, y_tree, h, N2["assets"])]), "ACCEPT")
    run.check(15, "two PendingNoGuard boxes, case 13's shape (batching)",
              complete([N1, N2], [out(V, x_tree, h, N1["assets"]), out(V, x_tree, h, N2["assets"])]), "ACCEPT")
    bad = [c for c in run.doc["cases"] if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


if __name__ == "__main__":
    main()
