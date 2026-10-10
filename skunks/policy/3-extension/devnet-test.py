#!/usr/bin/env python3
"""Experiment 3, part A: prove an existing block-extension key in script (ExtFlag.es), and the header depth
(Depth.es), on the `policy` devnet.

Control first (off-chain): for consecutive blocks, rebuild the extension Merkle root from /blocks/{id}'s fields
(merkle.py, plan S12), compare with the header's extensionRoot, record leaf counts (odd and even), and flip one byte
of one leaf (must mismatch).

   1  spend the Depth box compiled with N = 9                           ACCEPT (checked)
   2  spend the Depth box compiled with N = 10                          REFUSE node-check    sibling 1
   3  flip with the leaf's value byte changed                           REFUSE node-check    sibling 6
   4  flip with a proof for a different key present in the block        REFUSE node-check    sibling 6
   5  flip with a valid proof against H-9 (i = 8)                       ACCEPT (checked)
   6  flip with a valid proof against H-1 (i = 0)                       ACCEPT (mined)
   7  case 5's proof one block later (i = 9), on a second flag box      EVAL-ERROR           sibling 5
   8  refresh the flipped box unchanged, no key                         ACCEPT
   9  true -> false                                                     REFUSE node-check    sibling 8
  10  ExtFlagAny: flip with a proof 4 blocks old, submitted               ACCEPT (mined)
  11  ExtFlagAny: the same flip, leaf value byte changed                  REFUSE node-check    sibling 10

Case 6 is resubmitted with a fresh proof against the new tip until it is mined (the first run of this harness
waited forever: a proof against headers(i) for a fixed i is valid at exactly one height); every attempt is recorded.
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from common import *  # noqa: E402
import merkle  # noqa: E402

KEY = "0100"     # the first interlink field: present in every non-genesis block


def block_at(k):
    return must(A, f"/blocks/{must(A, f'/blocks/at/{k}')[0]}")


def path_var(path):
    """Coll[(Coll[Byte], Boolean)]: type 0x0c 0x49 0x0e (Coll of Pair2(Coll[Byte], Boolean)), then the values."""
    v = "0c490e" + vlq(len(path))
    for sib, left in path:
        v += vlq(len(sib)) + sib.hex() + ("01" if left else "00")
    return v


def proof_ext(k, key=KEY, i=0, tamper=False):
    b = block_at(k)
    fields = b["extension"]["fields"]
    idx = [j for j, (kk, _) in enumerate(fields) if kk == key][0]
    leaf = merkle.leaf(*fields[idx])
    path = merkle.proof(fields, idx)
    assert merkle.fold(leaf, path).hex() == b["header"]["extensionHash"]
    if tamper:
        leaf = leaf[:-1] + bytes([leaf[-1] ^ 1])
    return {"2": coll_bytes(leaf.hex()), "3": path_var(path), "4": int_c(i)}


def main():
    run = Run("3-extension", HERE)
    # ---- control
    h = full_height()
    control, odd, even = [], False, False
    for k in range(h - 1, max(1, h - 30), -1):
        b = block_at(k)
        f = b["extension"]["fields"]
        ok = merkle.root(f).hex() == b["header"]["extensionHash"]
        bad = list(f)
        bad[0] = [bad[0][0], bad[0][1][:-2] + ("00" if bad[0][1][-2:] != "00" else "01")]
        neg = merkle.root(bad).hex() != b["header"]["extensionHash"]
        control.append({"height": k, "leaves": len(f), "match": ok, "flipped_byte_mismatch": neg,
                        "has_key": any(kk == KEY for kk, _ in f)})
        odd |= ok and len(f) % 2 == 1
        even |= ok and len(f) % 2 == 0
        if (odd and even and len(control) >= 3) or len(control) >= 10:
            break
    run.doc["control"] = {"blocks": control, "odd_matched": odd, "even_matched": even, "reconstruction_changes": 0}
    print("control", control)
    if not all(c["match"] and c["flipped_byte_mismatch"] and c["has_key"] for c in control):
        raise SystemExit("control failed")

    # ---- contracts
    ft, faddr = compile_tree((HERE / "ExtFlag.es").read_text(), {"$KEY": KEY})
    d9, d9a = compile_tree((HERE / "Depth.es").read_text(), {"$N": "9"})
    d10, d10a = compile_tree((HERE / "Depth.es").read_text(), {"$N": "10"})
    nft1, nft2 = issue("EXTFLAG-1"), issue("EXTFLAG-2")
    dep = send([{"address": faddr, "value": 10_000_000, "assets": [{"tokenId": nft1, "amount": 1}],
                 "registers": {"R4": FALSE}},
                {"address": faddr, "value": 10_000_000, "assets": [{"tokenId": nft2, "amount": 1}],
                 "registers": {"R4": FALSE}},
                {"address": d9a, "value": 10_000_000}, {"address": d10a, "value": 10_000_000}])
    F1 = [o for o in at(dep, ft) if o["assets"][0]["tokenId"] == nft1][0]
    F2 = [o for o in at(dep, ft) if o["assets"][0]["tokenId"] == nft2][0]
    D9, D10 = at(dep, d9)[0], at(dep, d10)[0]
    run.tree("ExtFlag", ft, faddr, F1["boxId"])
    run.tree("Depth-9", d9, d9a, D9["boxId"])
    run.tree("Depth-10", d10, d10a, D10["boxId"])

    def flip(box, ext, h, r4=TRUE):
        return {"inputs": [inp(box["boxId"], ext)], "dataInputs": [],
                "outputs": [out(box["value"], ft, h, box["assets"], {"R4": r4})]}

    h = full_height()
    run.check(1, "spend the Depth box compiled with N = 9", {"inputs": [inp(D9["boxId"])], "dataInputs": [],
              "outputs": [out(D9["value"], NOBODY_TREE, h)]}, "ACCEPT")
    run.check(2, "spend the Depth box compiled with N = 10", {"inputs": [inp(D10["boxId"])], "dataInputs": [],
              "outputs": [out(D10["value"], NOBODY_TREE, h)]}, "REFUSE", sibling=1)

    # HEIGHT = h + 1; headers(i) is the block at h - i
    h = full_height()
    run.check(3, "flip with the leaf's value byte changed", flip(F1, proof_ext(h, tamper=True), h), "REFUSE", sibling=6)
    run.check(4, "flip with a proof for a different key present in the block (0101)",
              flip(F1, proof_ext(h, key="0101"), h), "REFUSE", sibling=6)
    p5 = proof_ext(h - 8, i=8)
    run.check(5, "flip with a valid proof against H-9 (i = 8)", flip(F1, p5, h), "ACCEPT", proof_block=h - 8)
    attempts, m = [], None
    for _ in range(6):
        h = full_height()
        tx = flip(F1, proof_ext(h, i=0), h)
        code, o = call(A, "/transactions/check", tx)
        if code != 200:
            attempts.append({"fullHeight": h, "check": classify(code, o), "detail": str(o)[:200]})
            continue
        tid = must(A, "/transactions", tx)
        c, ins = run.mempool_cost(tid)
        wait_height(A, h + 2)
        cm, mt = call(A, f"/blockchain/transaction/byId/{tid}")
        attempts.append({"fullHeight": h, "tx_id": tid, "cost": c, "mined": cm == 200,
                         "inclusionHeight": mt.get("inclusionHeight") if cm == 200 else None})
        print("case 6 attempt", attempts[-1], flush=True)
        if cm == 200:
            m = mt
            break
    got = "ACCEPT" if m else "NOT-MINED"
    run.record(6, "flip with a valid proof against H-1 (i = 0), mined (resubmitted until mined)", "ACCEPT", got,
               cost=attempts[-1].get("cost"), instrument="mempool", tx_id=attempts[-1].get("tx_id"),
               heights={"attempts": attempts}, detail=f"{len(attempts)} attempt(s)")
    if not m:
        raise SystemExit("case 6 never mined")
    h = full_height()
    if full_height() == h:
        wait_height(A, h + 1)
    h2 = full_height()
    p7 = dict(p5, **{"4": int_c(h2 - (h - 8))})
    run.check(7, f"case 5's proof {h2 - h} block(s) later, i = {h2 - (h - 8)}, on a second flag box",
              flip(F2, p7, h2), "EVAL-ERROR", sibling=5, proof_block=h - 8)
    F1b = at(m, ft)[0]
    h = full_height()
    run.check(9, "true -> false", flip(F1b, {}, h, FALSE), "REFUSE", sibling=8)
    run.check(8, "refresh the flipped box unchanged, no key", flip(F1b, {}, h, TRUE), "ACCEPT")
    # ---- ExtFlagAny: the 9-block window
    at_, ata = compile_tree((HERE / "ExtFlagAny.es").read_text(), {"$KEY": KEY})
    nft3 = issue("EXTFLAG-3")
    F3 = at(send([{"address": ata, "value": 10_000_000, "assets": [{"tokenId": nft3, "amount": 1}],
                   "registers": {"R4": FALSE}}]), at_)[0]
    run.tree("ExtFlagAny", at_, ata, F3["boxId"])
    h = full_height()
    k = h - 4
    pa = proof_ext(k)
    del pa["4"]
    pt = proof_ext(k, tamper=True)
    del pt["4"]
    fa = lambda e, h: {"inputs": [inp(F3["boxId"], e)], "dataInputs": [],
                       "outputs": [out(F3["value"], at_, h, F3["assets"], {"R4": TRUE})]}
    run.check(11, "ExtFlagAny: flip with a 4-block-old proof, leaf value byte changed", fa(pt, h), "REFUSE",
              sibling=10)
    m10 = run.check(10, "ExtFlagAny: flip with a proof against the block 4 below the tip, submitted", fa(pa, h),
                    "ACCEPT", submit=True, cost=True, proof_block=k)
    run.doc["cases"][-1]["inclusionHeight"] = m10.get("inclusionHeight")
    run.save()
    bad = [c for c in run.doc["cases"] if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


if __name__ == "__main__":
    main()
