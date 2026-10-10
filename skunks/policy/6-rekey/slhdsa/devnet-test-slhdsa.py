#!/usr/bin/env python3
"""The SLH-DSA-SHA2-128s verifier on the policy devnet, judged by the node (SK-053 step 3, the node's verdict).

The cloud session's result (README.md) is harness-only: the sigma compiler and interpreter, no node. This runs the
same verifier as a box's guard on the peeryard devnet `policy` (ergo 6.0.7, `rig/devnet.sh expose A 9181 policy`):
the tree is the harness's own compiled bytes (`run.sh tree`), the signature is BouncyCastle's on the spend digest
(`run.sh sign <digest>`), and every verdict is the node's (`/transactions/check`; ACCEPT = 200, REFUSE = "should
pass verification"). Forgeries are checked first, as siblings of the honest spend, then the honest spend is mined.

  1  one byte of the signature flipped                              REFUSE
  2  signed for one set of outputs, sent with another               REFUSE
  3  the honest spend                                               ACCEPT (mined), cost from the mempool entry

usage: devnet-test-slhdsa.py [--node http://127.0.0.1:9181] [--out results-devnet.json]
"""
import argparse, importlib.util, json, os, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location("kt", ROOT / "skunks" / "keepalive" / "devnet-test.py")
kt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kt)
call, must, height, wait_tx_outputs = kt.call, kt.must, kt.height, kt.wait_tx_outputs
FEE, FEE_TREE = kt.FEE, kt.FEE_TREE
ONESHOT = ROOT / "skunks" / "oneshot"


def runner(*args):
    out = subprocess.run(["bash", str(HERE / "run.sh"), *args], cwd=ROOT, capture_output=True, text=True)
    if out.returncode:
        sys.exit("run.sh " + " ".join(args) + ": " + out.stderr[-600:])
    lines = [l for l in out.stdout.splitlines() if l.startswith(("TREE ", "SIG "))]
    return lines[-1].split(" ", 1)[1]


def spend_digest(box_id, outputs):
    """blake2b256(boxId ++ outputs' bytesWithoutRef), computed by the oneshot WOTS signer (any seed; its message)."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(outputs, f)
    out = subprocess.run(["npx", "tsx", "scripts/wots-cli.mts", "sign", "11" * 32, "32", "16", box_id, f.name],
                         cwd=ONESHOT, capture_output=True, text=True)
    os.unlink(f.name)
    if out.returncode:
        sys.exit("wots-cli: " + out.stderr[-400:])
    return json.loads(out.stdout.strip().splitlines()[-1])["message"]


def coll_bytes(h):
    n, v = len(h) // 2, bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        v.append(b | (0x80 if n else 0))
        if not n:
            break
    return "0e" + v.hex() + h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", default="http://127.0.0.1:9181")
    ap.add_argument("--out", default="results-devnet.json")
    a = ap.parse_args()
    base = a.node
    info = must(base, "/info")
    results = []

    tree = runner("tree")
    addr = must(base, f"/utils/ergoTreeToAddress/{tree}")["address"]
    owner_addr = must(base, "/wallet/addresses")[0]
    owner_tree = "0008cd" + must(base, f"/utils/addressToRaw/{owner_addr}")["raw"]
    print("verifier tree", len(tree) // 2, "bytes; address", addr[:12], "…; node", info["appVersion"], "height", info["fullHeight"])

    dep = wait_tx_outputs(base, must(base, "/wallet/transaction/send", {"requests": [
        {"address": addr, "value": 20_000_000}], "fee": FEE}))
    A = [o for o in dep["outputs"] if o["ergoTree"] == tree][0]
    print("deposit", dep["id"][:8], "box", A["boxId"][:8], "at", A["creationHeight"])

    h = height(base)
    outs = [{"value": A["value"] - FEE, "ergoTree": owner_tree, "creationHeight": h, "assets": [],
             "additionalRegisters": {}},
            {"value": FEE, "ergoTree": FEE_TREE, "creationHeight": h, "assets": [], "additionalRegisters": {}}]
    digest = spend_digest(A["boxId"], outs)
    sig = runner("sign", digest)
    print("digest", digest[:16], "… signature", len(sig) // 2, "bytes")

    def tx(signature, outputs):
        return {"inputs": [{"boxId": A["boxId"], "spendingProof": {"proofBytes": "", "extension": {"1": coll_bytes(signature)}}}],
                "dataInputs": [], "outputs": outputs}

    def record(n, label, expect, got, detail="", **extra):
        row = {"case": n, "label": label, "expect": expect, "got": got, "ok": got == expect,
               "detail": str(detail).replace("\n", " ")[:300], **extra}
        results.append(row)
        print(f"{n:>2} {label:<58} expect {expect:<6} got {got:<9} {'ok' if row['ok'] else 'WRONG'}")

    def check(n, label, t, expect, sibling=None):
        code, out = call(base, "/transactions/check", t)
        detail = out if isinstance(out, str) else ""
        got = "ACCEPT" if code == 200 else ("REFUSE" if "should pass verification" in detail else "MALFORMED")
        record(n, label, expect, got, detail, source="node-check", sibling_n=sibling)
        return code == 200

    # siblings first: both forgeries are single mutations of the honest spend (case 3), same input, same height
    flipped = sig[:2] + format(int(sig[2:4], 16) ^ 1, "02x") + sig[4:]
    check(1, "one byte of the signature flipped (sibling of 3)", tx(flipped, outs), "REFUSE", 3)
    redirect = [dict(outs[0], ergoTree="0008cd" + kt.G), outs[1]]
    check(2, "signed for one set of outputs, sent with another (sibling of 3)", tx(sig, redirect), "REFUSE", 3)

    honest = tx(sig, outs)
    if check(3, "the honest spend", honest, "ACCEPT"):
        txid = must(base, "/transactions", honest)
        cost, instrument = None, "missed"
        for _ in range(50):
            code, ent = call(base, f"/transactions/unconfirmed/byTransactionId/{txid}")
            if code == 200 and isinstance(ent, dict) and ent.get("cost") is not None:
                cost, instrument = ent["cost"], "mempool"
                break
            time.sleep(0.2)
        mined = wait_tx_outputs(base, txid)
        results[-1].update({"tx_id": txid, "cost": cost, "cost_instrument": instrument,
                            "mined_height": mined.get("inclusionHeight"), "tx_size": mined.get("size")})
        print("   mined", txid[:8], "cost", cost, f"({instrument})", "size", mined.get("size"))

    json.dump({"experiment": "6-rekey-slhdsa-devnet", "node": {"appVersion": info["appVersion"],
               "parameters": info["parameters"]}, "tree_bytes": len(tree) // 2, "address": addr,
               "deposit_tx": dep["id"], "results": results}, open(HERE / a.out, "w"), indent=1)
    bad = [r for r in results if not r["ok"]]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


if __name__ == "__main__":
    main()
