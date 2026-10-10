#!/usr/bin/env python3
"""Experiment 5: hash-weakness canary (HCanary.es, K = 2) read by QVault.es unchanged, on the `policy` devnet.

The colliding pair is found off-chain by brute force (random 8-byte inputs until two agree on the first K bytes of
blake2b256), and a pair agreeing on K - 1 bytes but not K. QVault is compiled with QDAY_NFT = the canary's NFT and
BACKSTOP = start + 1,000,000, so height cannot explain a refusal.

   1  owner spends vault A while the canary is false (data input)       ACCEPT (checked)
   2  flip with a = b                                                    REFUSE node-check    sibling 5
   3  flip with a pair agreeing on K - 1 bytes only                      REFUSE node-check    sibling 5
   4  flip with a non-colliding pair                                     REFUSE node-check    sibling 5
   5  flip with a colliding pair                                         ACCEPT (mined)
   6  true -> false                                                      REFUSE node-check    sibling 6.s
 6.s  the flipped box refreshed unchanged                                ACCEPT (checked)
   7  owner spends vault A with the true canary as data input            REFUSE wallet-sign   sibling 1 (state flip)
   8  hash key spends vault A                                            ACCEPT (checked); exempt from both signs
"""
import hashlib, os, sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from common import *  # noqa: E402

K = 2
KA = {"$PER_INPUTL": "500000L", "$REFRESHL": "2000000L", "$PERIOD": "40", "$WINDOW": "20", "$SLACK": "10"}


def bh(x):
    return hashlib.blake2b(x, digest_size=32).digest()


def find_pairs():
    seen, draws, coll, near = {}, 0, None, None
    while coll is None or near is None:
        x = os.urandom(8)
        draws += 1
        d = bh(x)
        p = d[:K]
        if p in seen and seen[p] != x and coll is None:
            coll = (seen[p], x, draws)
        seen.setdefault(p, x)
        if near is None:
            for q, y in list(seen.items())[:2000]:
                if q[:K - 1] == p[:K - 1] and q != p:
                    near = (y, x)
                    break
    return coll, near


def main():
    run = Run("5-canary", HERE)
    (ca, cb, draws), (na, nb) = find_pairs()
    run.doc["pairs"] = {"collide": [ca.hex(), cb.hex()], "draws": draws, "near": [na.hex(), nb.hex()],
                        "hash_prefixes": {"collide": [bh(ca)[:K].hex(), bh(cb)[:K].hex()],
                                          "near": [bh(na)[:K].hex(), bh(nb)[:K].hex()]}}
    print("pairs", run.doc["pairs"])
    owner = pk_of(A)
    ct, caddr = compile_tree((HERE / "HCanary.es").read_text(), {"$K": str(K)})
    nft = issue("HCANARY")
    seed = os.urandom(32).hex()
    commit = wots("commit", seed, "32", "16")["commitment"]
    start = full_height()
    vt, vaddr = compile_tree((HERE.parent.parent / "qvault" / "QVault.es").read_text(), {
        "$OWNER": owner, "$QDAY_NFT": nft, "$BACKSTOP": str(start + 1_000_000), "$PKCOMMIT": commit, **KA})
    dep = send([{"address": caddr, "value": 10_000_000, "assets": [{"tokenId": nft, "amount": 1}],
                 "registers": {"R4": FALSE}}, {"address": vaddr, "value": 50_000_000}])
    C, VA = at(dep, ct)[0], at(dep, vt)[0]
    run.tree("HCanary", ct, caddr, C["boxId"])
    run.tree("QVault-canary", vt, vaddr, VA["boxId"])
    owner_tree = "0008cd" + owner

    def vault_owner(n, label, flag, expect, sibling=None):
        h = full_height()
        return run.key_spend(n, label, A, [VA["boxId"]], [flag["boxId"]], [out(VA["value"], owner_tree, h)], expect,
                             sibling)

    def flip(box, a, b, r4=TRUE, submit=False, n=None, label="", expect="", sibling=None, cost=False):
        h = full_height()
        ext = {}
        if a is not None:
            ext = {"1": coll_bytes(a.hex()), "2": coll_bytes(b.hex())}
        tx = {"inputs": [inp(box["boxId"], ext)], "dataInputs": [],
              "outputs": [out(box["value"], ct, h, box["assets"], {"R4": r4})]}
        return run.check(n, label, tx, expect, sibling, submit=submit, cost=cost)

    vault_owner(1, "owner spends vault A while the canary is false (data input)", C, "ACCEPT")
    flip(C, ca, ca, n=2, label="flip with a = b", expect="REFUSE", sibling=5)
    flip(C, na, nb, n=3, label=f"flip with a pair agreeing on {K - 1} byte(s) only", expect="REFUSE", sibling=5)
    x, y = os.urandom(8), os.urandom(8)
    while bh(x)[:1] == bh(y)[:1]:
        y = os.urandom(8)
    flip(C, x, y, n=4, label="flip with a non-colliding pair", expect="REFUSE", sibling=5)
    m = flip(C, ca, cb, n=5, label=f"flip with a colliding pair (first {K} bytes)", expect="ACCEPT", submit=True,
             cost=True)
    C2 = at(m, ct)[0]
    flip(C2, None, None, r4=FALSE, n=6, label="true -> false", expect="REFUSE", sibling="6.s")
    flip(C2, None, None, r4=TRUE, n="6.s", label="the flipped box refreshed unchanged", expect="ACCEPT")
    vault_owner(7, "owner spends vault A with the true canary as data input", C2, "REFUSE", sibling=1)
    h = full_height()
    outs = [out(VA["value"], owner_tree, h)]
    sig = wots_sign(seed, VA["boxId"], outs)
    run.check(8, "hash key spends vault A", {"inputs": [inp(VA["boxId"], {"1": coll_bytes(sig)})], "dataInputs": [],
                                             "outputs": outs}, "ACCEPT")
    bad = [c for c in run.doc["cases"] if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


if __name__ == "__main__":
    main()
