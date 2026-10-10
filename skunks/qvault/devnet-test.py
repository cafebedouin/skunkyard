#!/usr/bin/env python3
"""Quantum-day vault with KeepAlive on a peeryard devnet: every path and attack, judged by the node.

Against one mining node (peeryard devnet `keepalive`, ergo 6.0.7, 20 s blocks; `rig/devnet.sh expose A 9180
keepalive`). The node's wallet holds the owner key (its first address) and the oracle key (a second derived key).
WOTS keys (n 32, w 16) come from skunks/oneshot/scripts/wots-cli.mts. Two vaults: FAR (backstop far away) and NEAR
(backstop about 45 blocks after the start), each with its own WOTS key. ACCEPT cases marked (mined) are mined; the
rest are checked only. A REFUSE is the node's "should pass verification", or, for a key path, the wallet failing to
sign because the proposition reduces to false.

Before quantum day
   1  owner key spends A, flag box (false) as a data input           ACCEPT
   2  owner key spends A with no flag box                            REFUSE
   3  owner key spends A with a look-alike flag (another token)      REFUSE
   4  hash key spends A                                              ACCEPT
   5  hash key: signed for one set of outputs, sent with another     REFUSE
   6  hash key spends B and C together (a one-time key twice)        REFUSE
   7  keyless merge of B and C                                       ACCEPT (mined)
   8  lone refresh of A in the KeepAlive window, no key              ACCEPT
Backstop (NEAR, flag still false)
   9  owner key spends D after NEAR's backstop                       REFUSE
  10  hash key spends D after the backstop                           ACCEPT (mined)
The flag
  11  flag false -> true with no key                                  REFUSE
  12  flag false -> true by the oracle                                ACCEPT (mined)
  13  flag true -> false by the oracle                                REFUSE
  14  flag box refreshed unchanged, no key                            ACCEPT
After quantum day
  15  owner key spends A, flag box (true) as a data input            REFUSE
  16  owner key spends A with no flag box                            REFUSE
  17  keyless merge of A, the B+C box and a new payment E            ACCEPT (mined)
  18  hash key spends the merged box to the owner                    ACCEPT (mined)

usage: devnet-test.py [--node http://127.0.0.1:9180] [--out results.json]
"""
import argparse, importlib.util, json, os, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("kt", HERE.parent / "keepalive" / "devnet-test.py")
kt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kt)
call, must, height, wait_height, wait_tx_outputs = kt.call, kt.must, kt.height, kt.wait_height, kt.wait_tx_outputs
FEE, FEE_TREE = kt.FEE, kt.FEE_TREE
PERIOD, WINDOW, PER_INPUT, REFRESH, SLACK = 40, 20, 500_000, 2_000_000, 10
ONESHOT = HERE.parent / "oneshot"
FALSE, TRUE = "0100", "0101"


def wots(*args):
    out = subprocess.run(["npx", "tsx", "scripts/wots-cli.mts", *args], cwd=ONESHOT, capture_output=True, text=True)
    if out.returncode:
        sys.exit("wots-cli: " + out.stderr[-400:])
    return json.loads(out.stdout.strip().splitlines()[-1])


def coll_bytes(h):
    n, v = len(h) // 2, bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        v.append(b | (0x80 if n else 0))
        if not n:
            break
    return "0e" + v.hex() + h


def compile_tree(base, src, subs):
    for k, v in subs.items():
        src = src.replace(k, v)
    assert "$" not in src
    addr = must(base, "/script/p2sAddress", {"source": src, "treeVersion": 1})["address"]
    return must(base, f"/script/addressToTree/{addr}")["tree"], addr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", default="http://127.0.0.1:9180")
    ap.add_argument("--out", default="devnet-results.json")
    a = ap.parse_args()
    base = a.node
    results = []

    owner_addr = must(base, "/wallet/addresses")[0]
    owner_pk = must(base, f"/utils/addressToRaw/{owner_addr}")["raw"]
    owner_tree = "0008cd" + owner_pk
    addrs = must(base, "/wallet/addresses")
    if len(addrs) < 2:
        must(base, "/wallet/deriveNextKey")
        addrs = must(base, "/wallet/addresses")
    oracle_pk = must(base, f"/utils/addressToRaw/{addrs[1]}")["raw"]
    assert oracle_pk != owner_pk

    # the flag: mint the singleton, put it in the flag box with R4 = false; and a look-alike with another token
    def issue(name):
        tx = wait_tx_outputs(base, must(base, "/wallet/transaction/send", {"requests": [{
            "address": owner_addr, "ergValue": 1_000_000, "amount": 1, "name": name, "description": name,
            "decimals": 0}], "fee": FEE}))
        return tx["outputs"][0]["assets"][0]["tokenId"]
    qday_nft, fake_nft = issue("QDAY"), issue("QDAY-FAKE")
    qtree, qaddr = compile_tree(base, (HERE / "QDay.es").read_text(), {"$ORACLE": oracle_pk})
    # the look-alike sits at a key nobody holds (the curve generator), so the node wallet never spends it as change
    nobody_addr = must(base, "/utils/ergoTreeToAddress/0008cd" + kt.G)["address"]
    sent = wait_tx_outputs(base, must(base, "/wallet/transaction/send", {"requests": [
        {"address": qaddr, "value": 10_000_000, "assets": [{"tokenId": qday_nft, "amount": 1}],
         "registers": {"R4": FALSE}},
        {"address": nobody_addr, "value": 10_000_000, "assets": [{"tokenId": fake_nft, "amount": 1}],
         "registers": {"R4": FALSE}}], "fee": FEE}))
    flag = [o for o in sent["outputs"] if o["ergoTree"] == qtree][0]
    fake = [o for o in sent["outputs"] if any(t["tokenId"] == fake_nft for t in o["assets"])][0]
    print("flag box", flag["boxId"][:8], "nft", qday_nft[:8], "fake", fake["boxId"][:8])

    # two vaults, each with its own WOTS key
    seeds = {"FAR": os.urandom(32).hex(), "NEAR": os.urandom(32).hex()}
    start = height(base)
    backstop = {"FAR": start + 1_000_000, "NEAR": start + 45}
    vault = {}
    for name in ("FAR", "NEAR"):
        commit = wots("commit", seeds[name], "32", "16")["commitment"]
        tree, addr = compile_tree(base, (HERE / "QVault.es").read_text(), {
            "$OWNER": owner_pk, "$QDAY_NFT": qday_nft, "$BACKSTOP": str(backstop[name]), "$PKCOMMIT": commit,
            "$PER_INPUTL": f"{PER_INPUT}L", "$REFRESHL": f"{REFRESH}L", "$PERIOD": str(PERIOD),
            "$WINDOW": str(WINDOW), "$SLACK": str(SLACK)})
        vault[name] = {"tree": tree, "addr": addr, "seed": seeds[name], "commit": commit}
        print(name, "vault tree", len(tree) // 2, "bytes; backstop", backstop[name])

    token = issue("QV")
    pays = [("A", "FAR", 50_000_000, 1), ("B", "FAR", 10_000_000, 0), ("C", "FAR", 10_000_000, 0),
            ("D", "NEAR", 50_000_000, 0)]
    dep = wait_tx_outputs(base, must(base, "/wallet/transaction/send", {"requests": [
        {"address": vault[v]["addr"], "value": val, "assets": [{"tokenId": token, "amount": n}] if n else []}
        for _, v, val, n in pays], "fee": FEE}))
    box = {}
    for (k, v, val, n) in pays:
        box[k] = [o for o in dep["outputs"] if o["ergoTree"] == vault[v]["tree"] and o["value"] == val
                  and len(o["assets"]) == (1 if n else 0) and o["boxId"] not in [b["boxId"] for b in box.values()]][0]
    print("payments", {k: b["boxId"][:8] for k, b in box.items()}, "at", box["A"]["creationHeight"])

    def outs_to_owner(boxes, h, fee=FEE):
        assets = {}
        for b in boxes:
            for t in b["assets"]:
                assets[t["tokenId"]] = assets.get(t["tokenId"], 0) + t["amount"]
        return [{"value": sum(b["value"] for b in boxes) - fee, "ergoTree": owner_tree, "creationHeight": h,
                 "assets": [{"tokenId": t, "amount": n} for t, n in assets.items()], "additionalRegisters": {}},
                {"value": fee, "ergoTree": FEE_TREE, "creationHeight": h, "assets": [], "additionalRegisters": {}}]

    def raw(b):
        return must(base, f"/utxo/byIdBinary/{b['boxId']}")["bytes"]

    def record(n, label, expect, got, detail=""):
        ok = got == expect
        results.append({"case": n, "label": label, "expect": expect, "got": got, "ok": ok,
                        "detail": str(detail).replace("\n", " ")[:300]})
        print(f"{n:>2} {label:<62} expect {expect:<6} got {got:<9} {'ok' if ok else 'WRONG'}")

    def check(n, label, tx, expect, submit=False):
        code, out = call(base, "/transactions/check", tx)
        detail = out if isinstance(out, str) else ""
        got = "ACCEPT" if code == 200 else ("REFUSE" if "should pass verification" in detail else "MALFORMED")
        record(n, label, expect, got, detail)
        if submit and code == 200:
            return wait_tx_outputs(base, must(base, "/transactions", tx))
        return None

    def key_spend(n, label, inputs, data, outputs, expect, submit=False):
        """A spend the node wallet must sign (owner or oracle key). A refusal to sign is a REFUSE when the
        proposition is false; the unsigned form is also checked, to show the node's own verdict."""
        unsigned = {"inputs": [{"boxId": b["boxId"], "extension": {}} for b in inputs],
                    "dataInputs": [{"boxId": d["boxId"]} for d in data], "outputs": outputs}
        code, signed = call(base, "/wallet/transaction/sign", {"tx": unsigned, "inputsRaw": [raw(b) for b in inputs],
                                                              "dataInputsRaw": [raw(d) for d in data]})
        if code != 200:
            empty = {"inputs": [{"boxId": b["boxId"], "spendingProof": {"proofBytes": "", "extension": {}}}
                                for b in inputs], "dataInputs": unsigned["dataInputs"], "outputs": outputs}
            c2, o2 = call(base, "/transactions/check", empty)
            refused = "should pass verification" in str(o2)
            record(n, label, expect, "REFUSE" if refused else "SIGN-FAIL", f"sign: {signed}; unsigned check: {o2}")
            return None
        return check(n, label, signed, expect, submit)

    def hash_spend(n, label, inputs, outputs, expect, submit=False, signed_outputs=None, seed=None):
        ins = []
        for b in inputs:
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                json.dump(signed_outputs or outputs, f)
            sig = wots("sign", seed, "32", "16", b["boxId"], f.name)["signature"]
            os.unlink(f.name)
            ins.append({"boxId": b["boxId"], "spendingProof": {"proofBytes": "", "extension": {"1": coll_bytes(sig)}}})
        return check(n, label, {"inputs": ins, "dataInputs": [], "outputs": outputs}, expect, submit)

    def merge(n, label, inputs, h, expect, submit=False):
        tree = vault["FAR"]["tree"]
        total = sum(b["value"] for b in inputs)
        bounty = min(len(inputs) * PER_INPUT, total - max(b["value"] for b in inputs)) if len(inputs) > 1 \
            else min(inputs[0]["value"] // 2, REFRESH)
        assets = {}
        for b in inputs:
            for t in b["assets"]:
                assets[t["tokenId"]] = assets.get(t["tokenId"], 0) + t["amount"]
        outs = [{"value": total - bounty, "ergoTree": tree, "creationHeight": h,
                 "assets": [{"tokenId": t, "amount": v} for t, v in assets.items()], "additionalRegisters": {}},
                {"value": bounty, "ergoTree": FEE_TREE, "creationHeight": h, "assets": [], "additionalRegisters": {}}]
        tx = {"inputs": [{"boxId": b["boxId"], "spendingProof": {"proofBytes": "", "extension": {"0": "0400"}}}
                         for b in inputs], "dataInputs": [], "outputs": outs}
        return check(n, label, tx, expect, submit)

    def flag_successor(b, value_r4, h):
        # The flag box keeps its whole value (its script requires at least that), so the fee must come from the
        # refresher's own input on mainnet; the devnet's minimum fee is 0, so these are fee-less to test the script
        # alone.
        return [{"value": b["value"], "ergoTree": qtree, "creationHeight": h,
                 "assets": [{"tokenId": t["tokenId"], "amount": t["amount"]} for t in b["assets"]],
                 "additionalRegisters": {"R4": value_r4}}]

    A, B, C, D = box["A"], box["B"], box["C"], box["D"]
    far, near = vault["FAR"]["seed"], vault["NEAR"]["seed"]

    # ---- before quantum day
    h = height(base)
    key_spend(1, "owner key spends A, flag box (false) as a data input", [A], [flag], outs_to_owner([A], h), "ACCEPT")
    key_spend(2, "owner key spends A with no flag box", [A], [], outs_to_owner([A], h), "REFUSE")
    key_spend(3, "owner key spends A with a look-alike flag (another token)", [A], [fake], outs_to_owner([A], h),
              "REFUSE")
    hash_spend(4, "hash key spends A", [A], outs_to_owner([A], h), "ACCEPT", seed=far)
    redirect = outs_to_owner([A], h)
    redirect[0] = dict(redirect[0], ergoTree="0008cd" + oracle_pk)
    hash_spend(5, "hash key: signed for one set of outputs, sent with another", [A], redirect, "REFUSE",
               signed_outputs=outs_to_owner([A], h), seed=far)
    hash_spend(6, "hash key spends B and C together (a one-time key twice)", [B, C], outs_to_owner([B, C], h),
               "REFUSE", seed=far)
    bc = merge(7, "keyless merge of B and C", [B, C], h, "ACCEPT", submit=True)
    BC = [o for o in bc["outputs"] if o["ergoTree"] == vault["FAR"]["tree"]][0]
    wait_height(base, A["creationHeight"] + PERIOD - WINDOW)
    merge(8, "lone refresh of A in the KeepAlive window, no key", [A], height(base), "ACCEPT")

    # ---- the backstop, flag still false
    wait_height(base, backstop["NEAR"])
    h = height(base)
    key_spend(9, "owner key spends D after NEAR's backstop", [D], [flag], outs_to_owner([D], h), "REFUSE")
    hash_spend(10, "hash key spends D after the backstop", [D], outs_to_owner([D], h), "ACCEPT", submit=True,
               seed=near)

    # ---- the flag
    h = height(base)
    flip = {"inputs": [{"boxId": flag["boxId"], "spendingProof": {"proofBytes": "", "extension": {}}}],
            "dataInputs": [], "outputs": flag_successor(flag, TRUE, h)}
    check(11, "flag false -> true with no key", flip, "REFUSE")
    flipped = key_spend(12, "flag false -> true by the oracle", [flag], [], flag_successor(flag, TRUE, h), "ACCEPT",
                        submit=True)
    flag2 = [o for o in flipped["outputs"] if o["ergoTree"] == qtree][0]
    h = height(base)
    key_spend(13, "flag true -> false by the oracle", [flag2], [], flag_successor(flag2, FALSE, h), "REFUSE")
    check(14, "flag box refreshed unchanged, no key",
          {"inputs": [{"boxId": flag2["boxId"], "spendingProof": {"proofBytes": "", "extension": {}}}],
           "dataInputs": [], "outputs": flag_successor(flag2, TRUE, h)}, "ACCEPT")

    # ---- after quantum day
    key_spend(15, "owner key spends A, flag box (true) as a data input", [A], [flag2], outs_to_owner([A], h),
              "REFUSE")
    key_spend(16, "owner key spends A with no flag box", [A], [], outs_to_owner([A], h), "REFUSE")
    e = wait_tx_outputs(base, must(base, "/wallet/transaction/send", {"requests": [
        {"address": vault["FAR"]["addr"], "value": 10_000_000}], "fee": FEE}))
    E = [o for o in e["outputs"] if o["ergoTree"] == vault["FAR"]["tree"]][0]
    h = height(base)
    m = merge(17, "keyless merge of A, the B+C box and a new payment E", [A, BC, E], h, "ACCEPT", submit=True)
    M = [o for o in m["outputs"] if o["ergoTree"] == vault["FAR"]["tree"]][0]
    h = height(base)
    hash_spend(18, "hash key spends the merged box to the owner", [M], outs_to_owner([M], h), "ACCEPT", submit=True,
               seed=far)

    json.dump({"qdayNft": qday_nft, "flagTree": qtree, "vaults": {k: {kk: vv for kk, vv in v.items() if kk != "seed"}
                                                                  for k, v in vault.items()},
               "backstops": backstop, "results": results}, open(HERE / a.out, "w"), indent=1)
    bad = [r for r in results if not r["ok"]]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


if __name__ == "__main__":
    main()
