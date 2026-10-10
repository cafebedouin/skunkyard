#!/usr/bin/env python3
"""Experiment 6, rerun (2026-10-10): rekey in place as a receive address (RekeyAccount.es) on the `policy` devnet.

The first run (Rekey.es, results-v1.json) found that a plain payment to a register-keyed vault was unspendable
(row 11). The ruling: such a box is spendable only as a merge input into a box carrying the registers, keeping them;
no compiled-in fallback key. That needed a per-account constant: Rekey.es kept the keys only in registers, so every
owner's vault shared one address and a plain payment to it had no owner. Merging it into "a box that carries the
registers" would then let any account holder take it.

Accounts: KA (account constant a1, first owner A) and KB (account constant a2, owner B). Node A's wallet holds A's
key, node B's wallet holds B's.

   1    in the window: refresh with R4 changed to G                                REFUSE  sibling 3
   2    in the window: refresh with R5 changed                                      REFUSE  sibling 3
   3    in the window: refresh, keys kept                                           ACCEPT (mined)
   4    rekey to B with an empty proof                                              REFUSE  sibling 6
   5    rekey to B signed by B (not yet the owner)                                  REFUSE  sibling 6
   6    rekey to B signed by A                                                      ACCEPT (mined)
   7    A (the old owner) spends the rekeyed box                                    REFUSE  sibling 8
   8    B (the new owner) spends it into a successor                                ACCEPT (mined)
   9    hash-key rekey: WOTS (s2) over a successor with new R4 (B) and R5 (s3)      ACCEPT (mined)
   9b   hash-key rekey keeping the spent commitment (s4 -> R5 still s4)             REFUSE  sibling 9   (RULING R5)
  10    the old seed (s2) signs for the rekeyed box                                 REFUSE  sibling 10.s
  10.s  a fresh signature with the new seed (s3), checked                           ACCEPT
  11    a plain payment P; A tries to spend it with the owner key                   REFUSE (was EVAL-ERROR)
  12    P merged, no key, into the account's one registered box, registers kept     ACCEPT (mined)
  13a   plain P2 "maintained" alone into a successor carrying chosen registers      REFUSE  sibling 13.s
  13b   P2 merged with a registered box into a successor with R4 changed to G       REFUSE  sibling 13.s
  13c   P2 merged with account KB's registered box into KB's address                REFUSE  sibling 13.s
  13d   P2 merged with two registered boxes of its account                          REFUSE  sibling 13.s
  13.s  P2 merged honestly with one registered box, checked                         ACCEPT
"""
import os, sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from common import *  # noqa: E402

PERIOD, WINDOW, PER_INPUT, REFRESH, SLACK = 40, 20, 500_000, 2_000_000, 10


def main():
    run = Run("6-rekey-account", HERE, out="results.json")
    pa, pb = pk_of(A), pk_of(B)
    src = (HERE / "RekeyAccount.es").read_text()
    subs = lambda acct: {"$ACCOUNT": acct, "$PER_INPUTL": f"{PER_INPUT}L", "$REFRESHL": f"{REFRESH}L",
                         "$PERIOD": str(PERIOD), "$WINDOW": str(WINDOW), "$SLACK": str(SLACK)}
    a1, a2 = os.urandom(32).hex(), os.urandom(32).hex()
    t, addr = compile_tree(src, subs(a1))
    tb, addrb = compile_tree(src, subs(a2))
    seeds = [os.urandom(32).hex() for _ in range(4)]
    c1, c2, c3, c4 = (wots("commit", s, "32", "16")["commitment"] for s in seeds)
    s1, s2, s3, s4 = seeds
    regs = lambda pk, c, rid=None: dict({"R4": ge_c(pk), "R5": coll_bytes(c)}, **({"R6": coll_bytes(rid)} if rid else {}))
    dep = send([{"address": addr, "value": 100_000_000, "registers": regs(pa, c1)},
                {"address": addr, "value": 100_000_000, "registers": regs(pa, c2)},
                {"address": addr, "value": 100_000_000, "registers": regs(pa, c4)},
                {"address": addr, "value": 10_000_000},
                {"address": addr, "value": 10_000_000},
                {"address": addrb, "value": 100_000_000, "registers": regs(pb, c3)}])
    boxes = at(dep, t)
    by_c = lambda c: [b for b in boxes if b["additionalRegisters"].get("R5", "").endswith(c)][0]
    X1, X2, X4 = by_c(c1), by_c(c2), by_c(c4)
    P, P2 = [b for b in boxes if not b["additionalRegisters"]]
    XB = at(dep, tb)[0]
    run.tree("RekeyAccount", t, addr, X1["boxId"], extra={"plain_box_bytes": box_bytes(P["boxId"]),
                                                          "second_account_address_differs": addr != addrb})
    dest_a = "0008cd" + pk_of(A, 2)

    def refresh(box, h, r4=None, r5=None):
        rr = regs(r4 or pa, r5 or c1, box["boxId"])
        return {"inputs": [inp(box["boxId"], {"0": "0400"})], "dataInputs": [],
                "outputs": [out(box["value"] - REFRESH, t, h, [], rr), out(REFRESH, FEE_TREE, h)]}

    def merge(ins, h, tree, r4, r5, rid, fee_bounty=True):
        total = sum(b["value"] for b in ins)
        bounty = min(len(ins) * PER_INPUT, total - max(b["value"] for b in ins))
        return {"inputs": [inp(b["boxId"], {"0": "0400"}) for b in ins], "dataInputs": [],
                "outputs": [out(total - bounty, tree, h, [], regs(r4, r5, rid)), out(bounty, FEE_TREE, h)]}

    # ---- refresh, secp rekey, hash-key rekey (rows 1-10, as in the first run)
    wait_height(A, X1["creationHeight"] + PERIOD - WINDOW)
    h = full_height()
    run.check(1, "in the window: refresh with R4 changed to G", refresh(X1, h, r4=G), "REFUSE", sibling=3)
    run.check(2, "in the window: refresh with R5 changed", refresh(X1, h, r5=c3), "REFUSE", sibling=3)
    Y = at(run.check(3, "in the window: refresh, keys kept", refresh(X1, h), "ACCEPT", submit=True), t)[0]
    h = full_height()
    rekey = [out(Y["value"], t, h, [], regs(pb, c1, Y["boxId"]))]
    run.check(4, "rekey to B with an empty proof", {"inputs": [inp(Y["boxId"])], "dataInputs": [], "outputs": rekey},
              "REFUSE", sibling=6)
    run.key_spend(5, "rekey to B signed by B (not yet the owner)", B, [Y["boxId"]], [], rekey, "REFUSE", sibling=6)
    Z = at(run.key_spend(6, "rekey to B signed by A", A, [Y["boxId"]], [], rekey, "ACCEPT", submit=True, cost=True),
           t)[0]
    h = full_height()
    succ = [out(Z["value"], t, h, [], regs(pb, c1, Z["boxId"]))]
    run.key_spend(7, "A (the old owner) spends the rekeyed box", A, [Z["boxId"]], [], succ, "REFUSE", sibling=8)
    Z2 = at(run.key_spend(8, "B (the new owner) spends it into a successor", B, [Z["boxId"]], [], succ, "ACCEPT",
                          submit=True), t)[0]
    h = full_height()
    outs = [out(X2["value"], t, h, [], regs(pb, c3, X2["boxId"]))]
    X2b = at(run.check(9, "hash-key rekey: WOTS (s2) over a successor with new R4 (B) and R5 (s3)",
                       {"inputs": [inp(X2["boxId"], {"1": coll_bytes(wots_sign(s2, X2["boxId"], outs))})],
                        "dataInputs": [], "outputs": outs}, "ACCEPT", submit=True, cost=True), t)[0]
    outs4 = [out(X4["value"], t, h, [], regs(pb, c4, X4["boxId"]))]
    run.check("9b", "hash-key rekey keeping the spent commitment (s4 signs, R5 still s4)",
              {"inputs": [inp(X4["boxId"], {"1": coll_bytes(wots_sign(s4, X4["boxId"], outs4))})], "dataInputs": [],
               "outputs": outs4}, "REFUSE", sibling=9)
    h = full_height()
    outs = [out(X2b["value"], dest_a, h)]
    run.check(10, "the old seed (s2) signs for the rekeyed box", {"inputs": [inp(X2b["boxId"], {
        "1": coll_bytes(wots_sign(s2, X2b["boxId"], outs))})], "dataInputs": [], "outputs": outs}, "REFUSE",
        sibling="10.s")
    run.check("10.s", "a fresh signature with the new seed (s3), checked", {"inputs": [inp(X2b["boxId"], {
        "1": coll_bytes(wots_sign(s3, X2b["boxId"], outs))})], "dataInputs": [], "outputs": outs}, "ACCEPT")

    # ---- plain payments
    h = full_height()
    run.key_spend(11, "a plain payment P; A tries to spend it with the owner key", A, [P["boxId"]], [],
                  [out(P["value"], dest_a, h)], "REFUSE", sibling=12)
    R = at(run.check(12, "P merged, no key, into the account's one registered box (Z2), registers kept",
                     merge([Z2, P], h, t, pb, c1, Z2["boxId"]), "ACCEPT", submit=True, cost=True), t)[0]
    h = full_height()
    alone = {"inputs": [inp(P2["boxId"], {"0": "0400"})], "dataInputs": [],
             "outputs": [out(P2["value"] - REFRESH, t, h, [], regs(pa, c3, P2["boxId"])), out(REFRESH, FEE_TREE, h)]}
    run.check("13a", "plain P2 'maintained' alone into a successor carrying chosen registers", alone, "REFUSE",
              sibling="13.s")
    run.check("13b", "P2 merged with a registered box (R) into a successor with R4 changed to G",
              merge([R, P2], h, t, G, c1, R["boxId"]), "REFUSE", sibling="13.s")
    run.check("13c", "P2 merged with account KB's registered box into KB's address",
              merge([XB, P2], h, tb, pb, c3, XB["boxId"]), "REFUSE", sibling="13.s")
    run.check("13d", "P2 merged with two registered boxes of its account (R and X2b)",
              merge([R, X2b, P2], h, t, pb, c1, R["boxId"]), "REFUSE", sibling="13.s")
    run.check("13.s", "P2 merged honestly with one registered box (R), checked",
              merge([R, P2], h, t, pb, c1, R["boxId"]), "ACCEPT")
    run.save()
    bad = [c for c in run.doc["cases"] if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


if __name__ == "__main__":
    main()
