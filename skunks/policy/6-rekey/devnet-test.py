#!/usr/bin/env python3
"""Experiment 6: rekey in place (Rekey.es) on the `policy` devnet.

Node A's wallet holds the first owner key; node B's wallet holds the second owner key (not A's). Two vaults: X1
(owner A, WOTS seed s1) for the secp rekey, X2 (owner A, WOTS seed s2) for the hash-key rekey.

   1  in the window: refresh with R4 changed to the generator G          REFUSE node-check             sibling 3
   2  in the window: refresh with R5 changed                             REFUSE node-check             sibling 3
   3  in the window: refresh, keys kept, honest                          ACCEPT (mined)
   4  rekey to B's key with an empty proof                               REFUSE node-check             sibling 6
   5  rekey to B's key, signed by B (not yet the owner)                  REFUSE wallet-sign/no-secret  sibling 6
   6  rekey to B's key, signed by A, the owner                           ACCEPT (mined)
   7  A (the old owner) spends the rekeyed box                           REFUSE wallet-sign/no-secret  sibling 8
   8  B (the new owner) spends it into a successor                       ACCEPT (mined)
   9  hash-key rekey of X2: WOTS over outputs carrying a new R5 and R4    ACCEPT (mined)
  10  the old WOTS seed signs for the rekeyed box                        REFUSE node-check             sibling 10.s
10.s  a fresh WOTS signature with the new seed                           ACCEPT (checked)
  11  a plain wallet payment to the address, then A tries to spend it    EVAL-ERROR                    sibling 6
"""
import os, sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from common import *  # noqa: E402

PERIOD, WINDOW, BOUNTY, SLACK = 40, 20, 2_000_000, 10


def main():
    run = Run("6-rekey", HERE)
    pa, pb = pk_of(A), pk_of(B)
    t, addr = compile_tree((HERE / "Rekey.es").read_text(), {"$PERIOD": str(PERIOD), "$WINDOW": str(WINDOW),
                                                             "$BOUNTYL": f"{BOUNTY}L", "$SLACK": str(SLACK)})
    s1, s2, s3 = (os.urandom(32).hex() for _ in range(3))
    c1, c2, c3 = (wots("commit", s, "32", "16")["commitment"] for s in (s1, s2, s3))
    regs = lambda pk, c: {"R4": ge_c(pk), "R5": coll_bytes(c)}
    dep = send([{"address": addr, "value": 100_000_000, "registers": regs(pa, c1)},
                {"address": addr, "value": 100_000_000, "registers": regs(pa, c2)},
                {"address": addr, "value": 10_000_000}])
    boxes = at(dep, t)
    X1 = [b for b in boxes if b["additionalRegisters"].get("R5", "").endswith(c1)][0]
    X2 = [b for b in boxes if b["additionalRegisters"].get("R5", "").endswith(c2)][0]
    P = [b for b in boxes if not b["additionalRegisters"]][0]
    run.tree("Rekey", t, addr, X1["boxId"])
    run.doc["plain_payment_box_bytes"] = box_bytes(P["boxId"])
    dest_a, dest_b = "0008cd" + pk_of(A, 2), "0008cd" + pk_of(B, 1)

    def refresh(box, h, r4=None, r5=None):
        rr = {"R4": ge_c(r4 or pa), "R5": coll_bytes(r5 or c1), "R6": coll_bytes(box["boxId"])}
        return {"inputs": [inp(box["boxId"], {"0": "0400"})], "dataInputs": [],
                "outputs": [out(box["value"] - BOUNTY, t, h, [], rr), out(BOUNTY, FEE_TREE, h)]}

    wait_height(A, X1["creationHeight"] + PERIOD - WINDOW)
    h = full_height()
    run.check(1, "in the window: refresh with R4 changed to the generator G", refresh(X1, h, r4=G), "REFUSE", sibling=3)
    run.check(2, "in the window: refresh with R5 changed", refresh(X1, h, r5=c3), "REFUSE", sibling=3)
    m = run.check(3, "in the window: refresh, keys kept, honest", refresh(X1, h), "ACCEPT", submit=True)
    Y = at(m, t)[0]
    run.tree("Rekey-refreshed", t, addr, Y["boxId"])

    h = full_height()
    rekey = [out(Y["value"], t, h, [], regs(pb, c1))]
    run.check(4, "rekey to B's key with an empty proof", {"inputs": [inp(Y["boxId"])], "dataInputs": [],
              "outputs": rekey}, "REFUSE", sibling=6)
    run.key_spend(5, "rekey to B's key, signed by B (not yet the owner)", B, [Y["boxId"]], [], rekey, "REFUSE", sibling=6)
    m = run.key_spend(6, "rekey to B's key, signed by A, the owner", A, [Y["boxId"]], [], rekey, "ACCEPT", submit=True,
                      cost=True)
    Z = at(m, t)[0]
    h = full_height()
    succ = [out(Z["value"], t, h, [], regs(pb, c1))]
    run.key_spend(7, "A (the old owner) spends the rekeyed box", A, [Z["boxId"]], [], succ, "REFUSE", sibling=8)
    run.key_spend(8, "B (the new owner) spends it into a successor", B, [Z["boxId"]], [], succ, "ACCEPT", submit=True)

    h = full_height()
    outs = [out(X2["value"], t, h, [], regs(pb, c3))]
    sig = wots_sign(s2, X2["boxId"], outs)
    m = run.check(9, "hash-key rekey of X2: WOTS (s2) over outputs carrying new R4 (B) and R5 (s3)",
                  {"inputs": [inp(X2["boxId"], {"1": coll_bytes(sig)})], "dataInputs": [], "outputs": outs}, "ACCEPT",
                  submit=True, cost=True)
    X2b = at(m, t)[0]
    h = full_height()
    outs = [out(X2b["value"], dest_a, h)]
    run.check(10, "the old WOTS seed (s2) signs for the rekeyed box", {"inputs": [inp(X2b["boxId"], {
        "1": coll_bytes(wots_sign(s2, X2b["boxId"], outs))})], "dataInputs": [], "outputs": outs}, "REFUSE",
        sibling="10.s")
    run.check("10.s", "a fresh WOTS signature with the new seed (s3), checked", {"inputs": [inp(X2b["boxId"], {
        "1": coll_bytes(wots_sign(s3, X2b["boxId"], outs))})], "dataInputs": [], "outputs": outs}, "ACCEPT")

    h = full_height()
    run.key_spend(11, "a plain wallet payment to the address (no registers); A tries to spend it", A, [P["boxId"]],
                  [], [out(P["value"], dest_a, h)], "EVAL-ERROR", sibling=6)
    c, o = call(A, "/transactions/check", {"inputs": [inp(P["boxId"])], "dataInputs": [],
                                          "outputs": [out(P["value"], dest_a, h)]})
    run.doc["cases"][-1]["node_check_unsigned"] = {"class": classify(c, o), "text": str(o)[:400]}
    run.save()
    bad = [c for c in run.doc["cases"] if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


if __name__ == "__main__":
    main()
