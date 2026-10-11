#!/usr/bin/env python3
"""WOTS+ against plain WOTS at matched step counts (prompts/policy-post-devnet-fixes-3.md, item B.11).

The round-two figures (17.7%, then 16.3%) each compared one WOTS+ spend with one plain-WOTS spend on different
random messages, so message variance (how many chain steps the verifier hashes) was inside the "overhead". Here each
scheme verifies eight spends; for each the verifier's hashed-step count is sum over the 67 chains of (15 - digit),
and the node's cost is read from the mempool entry. A least-squares line cost = fixed + slope * steps per scheme
(as slhdsa_ref.py fits SLH-DSA) gives the overhead at any matched step count. The verifiers are devnet-test-wotsplus.py's:
WotsPlus.es and the same source with the tweak removed.

Not an attack: public. Writes results-wotsplus-fit.json.
"""
import importlib.util, os, sys, time
from pathlib import Path

HERE = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("wp", HERE / "devnet-test-wotsplus.py")
wp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wp)
from common import *  # noqa: E402,F401

SPENDS = 8
FIXED_1OUT = 10_000 + 2_000 + 100     # devnet: interpreterInitCost + 1 input + 1 output (these spends have one output)


def fit(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    fixed = my - slope * mx
    resid = max(abs(y - (fixed + slope * x)) for x, y in zip(xs, ys))
    return slope, fixed, resid


def main():
    run = Run("6-rekey-wotsplus-fit", HERE, out="results-wotsplus-fit.json")
    dest = "0008cd" + pk_of(A, 2)
    wp_src = (HERE / "WotsPlus.es").read_text()
    w_src = (wp_src.replace("blake2b256(seed ++ Coll(c.toByte, s.toByte) ++ curr)", "blake2b256(curr)")
                   .replace("blake2b256(seed ++ concat) == commit", "blake2b256(concat) == commit"))
    assert w_src != wp_src
    fits = {}
    for name, tweaked, src in (("wotsplus", True, wp_src), ("wots", False, w_src)):
        seed = os.urandom(32)
        sk, commit = wp.keygen(tweaked, seed, os.urandom(32))
        tree, addr = compile_tree(src, {"$SEED": seed.hex(), "$COMMIT": commit.hex()})
        run.tree("WotsPlus-fit" if tweaked else "WotsPlain-fit", tree, addr)   # not WotsPlus.tree, the round-2 record
        boxes = at(send([{"address": addr, "value": 50_000_000 + i} for i in range(SPENDS)]), tree)
        h = full_height()
        pts = []
        for i, b in enumerate(boxes):
            outs = [out(b["value"], dest, h)]
            msg = wp.tx_message(b["boxId"], outs)
            ds = wp.digits(msg)
            steps = sum(15 - d for d in ds)                   # chain hashes the verifier computes
            sig = wp.sign(tweaked, seed, sk, msg)
            tx = {"inputs": [inp(b["boxId"], {"1": coll_bytes(sig.hex())})], "dataInputs": [], "outputs": outs}
            code, o = call(A, "/transactions/check", tx)
            if code != 200:
                run.record(f"{name}-{i}", f"{name} spend {i}", "ACCEPT", classify(code, o), detail=o)
                continue
            txid = must(A, "/transactions", tx)
            cost, ins = run.mempool_cost(txid)
            run.record(f"{name}-{i}", f"{name} spend {i}: {steps} hashed chain steps", "ACCEPT", "ACCEPT",
                       cost=cost, instrument=ins, tx_id=txid, steps=steps, script_cost=cost - FIXED_1OUT if cost else None)
            pts.append((steps, cost))
        wait_tx_outputs(A, run.doc["cases"][-1]["tx_id"])
        slope, fixed, resid = fit([p[0] for p in pts], [p[1] for p in pts])
        fits[name] = {"spends": len(pts), "node_cost_per_step": round(slope, 2), "node_fixed": round(fixed, 1),
                      "max_residual": round(resid, 1), "steps_min": min(p[0] for p in pts),
                      "steps_max": max(p[0] for p in pts)}
        print(f"fit {name} spends={len(pts)} cost_per_step={slope:.2f} fixed={fixed:.0f} max_residual={resid:.0f}")
    # overhead of the tweak at matched step counts: script cost = node cost - the per-transaction charge
    cmp = {}
    for s in (480, 506, 540, 990):
        wp_c = fits["wotsplus"]["node_fixed"] + fits["wotsplus"]["node_cost_per_step"] * s - FIXED_1OUT
        w_c = fits["wots"]["node_fixed"] + fits["wots"]["node_cost_per_step"] * s - FIXED_1OUT
        cmp[str(s)] = {"wotsplus_script": round(wp_c), "wots_script": round(w_c), "overhead_pct": round(100 * (wp_c - w_c) / w_c, 1)}
        print(f"matched steps={s} wotsplus_script={wp_c:.0f} wots_script={w_c:.0f} overhead={100 * (wp_c - w_c) / w_c:.1f}%")
    run.doc["fits"] = fits
    run.doc["matched"] = cmp
    run.doc["note"] = ("node cost from the mempool entry; script cost = node cost - 12,100 (devnet interpreterInitCost "
                       "10,000 + 1 input 2,000 + 1 output 100). 506 is the mean hashed-step count of a random "
                       "message (20,000 simulated: 64 digits at 7.5 each, plus about 26 on the checksum chains); 990 is the maximum "
                       "(every message digit 0: checksum 480 = digits 1, 14, 0), q2's worst case.")
    run.save()
    bad = [c for c in run.doc["cases"] if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


if __name__ == "__main__":
    main()
