#!/usr/bin/env python3
"""WOTS+ verifier (WotsPlus.es): a signer/verifier vector and the measured cost, against plain WOTS (SK-053 step 2).

WOTS+ keys every chain hash to a per-vault PUBLIC seed and the (chain, step) address (simple tweakable-hash
instantiation), so two vaults share no hash target (SK-035's multi-target gap). This builds the Python signer against
the in-script verifier with a printed vector, refuses a one-byte forgery, and measures the cost beside a plain-WOTS
baseline that is byte-identical except the tweak -- so the measured overhead is purely the tweak.

Not an attack: a verifier vector, like q2's. Public.

Rows:
  wp-valid    WOTS+ signature over the real spend message, verified in script   ACCEPT (mined) + cost
  wp-forge    the same with one byte of the signature flipped                   REFUSE
  w-valid     plain-WOTS baseline (same verifier minus the tweak), same (n,w)   ACCEPT (mined) + cost
"""
import hashlib, json, os, sys, tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from common import *  # noqa: E402

N, W, L = 32, 16, 67            # n=32, w=16, l = l1(64) + l2(3)
FIXED = 10_000 + 2_000 + 2 * 100  # devnet per-tx overhead (1 input, 2 outputs): interpreterInitCost + input + outputs


def bl(b):
    return hashlib.blake2b(b, digest_size=32).digest()


def digits(msg):
    ds = [(msg[c // 2] // 16 if c % 2 == 0 else msg[c // 2] % 16) for c in range(64)]
    cSum = sum(30 - (b // 16 + b % 16) for b in msg)
    return ds + [cSum // 256, (cSum // 16) % 16, cSum % 16]


def chain(tweaked, seed, c, a, b, x):
    for s in range(a, b):
        x = bl(seed + bytes([c, s]) + x) if tweaked else bl(x)
    return x


def keygen(tweaked, seed, secret):
    sk = [bl(secret + bytes([c])) for c in range(L)]
    pk = b"".join(chain(tweaked, seed, c, 0, W - 1, sk[c]) for c in range(L))
    commit = bl(seed + pk) if tweaked else bl(pk)
    return sk, commit


def sign(tweaked, seed, sk, msg):
    ds = digits(msg)
    return b"".join(chain(tweaked, seed, c, 0, ds[c], sk[c]) for c in range(L))


def tx_message(box_id, outputs):
    """The message the verifier computes: blake2b256(boxId ++ outputs' bytesWithoutRef). Taken from the wots CLI."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(outputs, f)
    try:
        return bytes.fromhex(wots("sign", os.urandom(32).hex(), str(N), str(W), box_id, f.name)["message"])
    finally:
        os.unlink(f.name)


def main():
    run = Run("6-rekey-wotsplus", HERE, out="results-wotsplus.json")
    dest = "0008cd" + pk_of(A, 2)
    wp_src = (HERE / "WotsPlus.es").read_text()
    # plain-WOTS baseline: the same verifier with the tweak removed (keyed hash -> bare hash, no seed in the commit)
    w_src = (wp_src
             .replace("blake2b256(seed ++ Coll(c.toByte, s.toByte) ++ curr)", "blake2b256(curr)")
             .replace("blake2b256(seed ++ concat) == commit", "blake2b256(concat) == commit"))

    def run_scheme(label_valid, tweaked, src, forge=False):
        seed = os.urandom(32)
        sk, commit = keygen(tweaked, seed, os.urandom(32))
        tree, addr = compile_tree(src, {"$SEED": seed.hex(), "$COMMIT": commit.hex()})
        box = at(send([{"address": addr, "value": 50_000_000}]), tree)[0]
        h = full_height()
        outs = [out(box["value"], dest, h)]
        msg = tx_message(box["boxId"], outs)
        sig = sign(tweaked, seed, sk, msg)
        tx = {"inputs": [inp(box["boxId"], {"1": coll_bytes(sig.hex())})], "dataInputs": [], "outputs": outs}
        mined = run.check(label_valid, f"{'WOTS+' if tweaked else 'plain WOTS'} signature verified in script",
                          tx, "ACCEPT", submit=True, cost=True, tree_bytes=len(tree) // 2)
        if forge:
            bad = bytearray(sig); bad[0] ^= 1
            ftx = {"inputs": [inp(box["boxId"], {"1": coll_bytes(bytes(bad).hex())})], "dataInputs": [],
                   "outputs": [out(box["value"], dest, full_height())]}
            # new box for the forgery (the valid one is spent); re-sign nothing, just flip
            fbox = at(send([{"address": addr, "value": 50_000_000}]), tree)[0]
            fh = full_height()
            fouts = [out(fbox["value"], dest, fh)]
            fmsg = tx_message(fbox["boxId"], fouts)
            fsig = bytearray(sign(tweaked, seed, sk, fmsg)); fsig[0] ^= 1
            run.check("wp-forge", "WOTS+ with one byte of the signature flipped",
                      {"inputs": [inp(fbox["boxId"], {"1": coll_bytes(bytes(fsig).hex())})], "dataInputs": [],
                       "outputs": fouts}, "REFUSE", sibling=label_valid)
        return mined, commit, seed

    wp_mined, wp_commit, wp_seed = run_scheme("wp-valid", True, wp_src, forge=True)
    w_mined, _, _ = run_scheme("w-valid", False, w_src)

    # cost read-out beside the estimate
    rows = {c["n"]: c for c in run.doc["cases"]}
    wp_node = rows["wp-valid"].get("cost")
    w_node = rows["w-valid"].get("cost")
    note = {}
    if wp_node and w_node:
        wp_script, w_script = wp_node - FIXED, w_node - FIXED
        note = {"wotsplus_node": wp_node, "wots_node": w_node,
                "wotsplus_script_est": wp_script, "wots_script_est": w_script,
                "tweak_overhead_pct": round(100 * (wp_script - w_script) / w_script, 1),
                "note": ("node cost minus the devnet per-tx overhead %d; both on a random spend message "
                         "(not q2's worst case), so compare the overhead, not the absolute" % FIXED)}
        run.doc["cost_comparison"] = note
        run.save()
        print(f"WOTS+ node {wp_node} (script~{wp_script}) vs plain WOTS node {w_node} (script~{w_script}); "
              f"tweak overhead {note['tweak_overhead_pct']}%")
    print("vector: seed", wp_seed.hex()[:16], "... commit", wp_commit.hex()[:16], "...")
    bad = [c for c in run.doc["cases"] if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


if __name__ == "__main__":
    main()
