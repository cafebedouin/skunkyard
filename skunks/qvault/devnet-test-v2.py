#!/usr/bin/env python3
"""SK-055 variant 2 (pqwallet step 3): the qvault suite against QVault2.es (a keyless forward to a pre-committed
successor after quantum day) plus the f-rows of skunks/pqwallet/SK055-PREREG.md. Derived from devnet-test.py.

Quantum-day vault with KeepAlive on a peeryard devnet: every path and attack, judged by the node.

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

Round 3 (2026-10-11, prompts/policy-post-devnet-fixes-3.md A.5-A.8; QDay.es gains a refresh window):
  6d  hash key: another WOTS+ key's signature (same PKSEED) on A's digest           REFUSE  sibling 4
  6e  hash key: A's valid signature replayed on A2 (same vault, same outputs)       REFUSE  sibling 4
  7a  owner spend of A citing the flag box, signed now, held                         (signed)
  7b  flag box refreshed unchanged, in its window, no key                            ACCEPT (mined)
  7c  the held owner spend submitted after 7b                                        REFUSE (its data input is gone)
  7d  the refreshed flag box refreshed again at once (churn)                         REFUSE (outside the window)
  7e  control: a flag box under the pre-window QDay, refreshed twice in a row        ACCEPT, ACCEPT (mined)
  7f  owner spend of A rebuilt on the refreshed flag box                             ACCEPT
  8a  FAR2 (flag NFT minted with amount 2): owner spend, the real flag (false)       ACCEPT
  8b  after the oracle sets that flag true: owner spend with it                      REFUSE
  8c  owner spend with the NFT's second unit, at a key address, R4 = false           ACCEPT (the vault cannot tell)
  8d  FAR3 (flag NFT minted amount 1 into a key address, R4 = false): owner spend    ACCEPT (the vault cannot tell)
  m1  after NEAR's backstop and its hash-key spend (row 10), a new payment F1:
      owner key spends it                                                         REFUSE
  m2  keyless merge of F1 and F2 at NEAR                                             ACCEPT (mined)
  m3  NEAR's already-used hash key signs again, spending the merged box              ACCEPT (the second signature)
  14  the flag box refreshed unchanged right after the oracle's flip (now outside its window)  REFUSE
  14b the same refresh in its window                                                 ACCEPT

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


# WOTS+ (n=32, w=16), simple tweakable-hash instantiation (SK-053 swap). The chain hash is keyed by the per-vault
# public PKSEED and the (chain, step) address, matching QVault.es. The CLI still provides the spend message digest.
import hashlib  # noqa: E402

WL = 67


def _bl(b):
    return hashlib.blake2b(b, digest_size=32).digest()


def _wp_chain(pkseed, c, a, b, x):
    for s in range(a, b):
        x = _bl(pkseed + bytes([c, s]) + x)
    return x


def _wp_digits(msg):
    ds = [(msg[c // 2] // 16 if c % 2 == 0 else msg[c // 2] % 16) for c in range(64)]
    cSum = sum(30 - (b // 16 + b % 16) for b in msg)
    return ds + [cSum // 256, (cSum // 16) % 16, cSum % 16]


def wotsplus_keygen(pkseed, secret):
    sk = [_bl(secret + bytes([c])) for c in range(WL)]
    pk = b"".join(_wp_chain(pkseed, c, 0, 15, sk[c]) for c in range(WL))
    return sk, _bl(pkseed + pk)


def wotsplus_sign(pkseed, sk, msg):
    ds = _wp_digits(msg)
    return b"".join(_wp_chain(pkseed, c, 0, ds[c], sk[c]) for c in range(WL))


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
    ap.add_argument("--node", default="http://127.0.0.1:9181")
    ap.add_argument("--out", default="devnet-results-v2.json")
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
    def issue(name, amount=1):
        tx = wait_tx_outputs(base, must(base, "/wallet/transaction/send", {"requests": [{
            "address": owner_addr, "ergValue": 1_000_000, "amount": amount, "name": name, "description": name,
            "decimals": 0}], "fee": FEE}))
        return tx["outputs"][0]["assets"][0]["tokenId"]
    qday_nft, fake_nft = issue("QDAY"), issue("QDAY-FAKE")
    qsubs = {"$ORACLE": oracle_pk, "$PERIOD": str(PERIOD), "$WINDOW": str(WINDOW), "$SLACK": str(SLACK)}
    qsrc = (HERE / "QDay.es").read_text()
    qtree, qaddr = compile_tree(base, qsrc, qsubs)
    # the pre-window QDay (before round 3), for the churn control 7e
    old_qsrc = qsrc.replace("now == was && inWindow", "now == was")
    assert old_qsrc != qsrc
    oqtree, oqaddr = compile_tree(base, old_qsrc, qsubs)
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

    # A.8: a flag NFT minted with amount 2 (one unit in a real flag box, one at a key address), and one minted
    # into a key address only; each guards its own far-backstop vault. 7e: a flag box under the pre-window QDay.
    q2_nft, q3_nft, old_nft = issue("QDAY2", 2), issue("QDAY3"), issue("QDAY-OLD")
    q23 = wait_tx_outputs(base, must(base, "/wallet/transaction/send", {"requests": [
        {"address": qaddr, "value": 10_000_000, "assets": [{"tokenId": q2_nft, "amount": 1}], "registers": {"R4": FALSE}},
        {"address": nobody_addr, "value": 10_000_001, "assets": [{"tokenId": q2_nft, "amount": 1}], "registers": {"R4": FALSE}},
        {"address": nobody_addr, "value": 10_000_002, "assets": [{"tokenId": q3_nft, "amount": 1}], "registers": {"R4": FALSE}},
        {"address": oqaddr, "value": 10_000_000, "assets": [{"tokenId": old_nft, "amount": 1}], "registers": {"R4": FALSE}},
    ], "fee": FEE}))
    holds = lambda o, t: any(x["tokenId"] == t for x in o["assets"])
    flag_q2 = [o for o in q23["outputs"] if o["ergoTree"] == qtree and holds(o, q2_nft)][0]
    keyaddr_q2 = [o for o in q23["outputs"] if o["ergoTree"] != qtree and holds(o, q2_nft)][0]
    keyaddr_q3 = [o for o in q23["outputs"] if holds(o, q3_nft)][0]
    old_flag = [o for o in q23["outputs"] if o["ergoTree"] == oqtree][0]

    # two vaults, each with its own WOTS key (and, round 3, FAR2 / FAR3 on the A.8 flag NFTs)
    # f8: a fourth NFT minted straight into a key address with R4 = TRUE (a fake "quantum day" nobody's oracle fired)
    q4_nft = issue("QDAY4")
    q4 = wait_tx_outputs(base, must(base, "/wallet/transaction/send", {"requests": [
        {"address": nobody_addr, "value": 10_000_003, "assets": [{"tokenId": q4_nft, "amount": 1}], "registers": {"R4": TRUE}},
    ], "fee": FEE}))
    fake_true_q4 = [o for o in q4["outputs"] if holds(o, q4_nft)][0]

    names = ("FAR'", "NEAR'", "FAR4'", "FAR", "NEAR", "FAR2", "FAR3", "FAR4")   # successors first: a vault commits to its successor's tree hash
    seeds = {n: os.urandom(32).hex() for n in names}
    start = height(base)
    backstop = {"FAR": start + 1_000_000, "NEAR": start + 45, "FAR2": start + 1_000_000, "FAR3": start + 1_000_000,
                "FAR4": start + 1_000_000, "FAR'": start + 1_000_000, "NEAR'": start + 1_000_000, "FAR4'": start + 1_000_000}
    successor_of = {"FAR": "FAR'", "NEAR": "NEAR'", "FAR4": "FAR4'"}
    vault = {}
    for name in names:
        pkseed = os.urandom(32)                       # per-vault public seed (WOTS+ domain separation)
        sk, commit_b = wotsplus_keygen(pkseed, bytes.fromhex(seeds[name]))
        commit = commit_b.hex()
        nft = {"FAR2": q2_nft, "FAR3": q3_nft, "FAR4": q4_nft}.get(name, qday_nft)
        succ = _bl(bytes.fromhex(vault[successor_of[name]]["tree"])).hex() if name in successor_of else "00" * 32
        tree, addr = compile_tree(base, (HERE / "QVault2.es").read_text(), {
            "$OWNER": owner_pk, "$QDAY_NFT": nft, "$BACKSTOP": str(backstop[name]), "$PKCOMMIT": commit,
            "$PKSEED": pkseed.hex(), "$SUCCESSOR": succ,
            "$PER_INPUTL": f"{PER_INPUT}L", "$REFRESHL": f"{REFRESH}L", "$PERIOD": str(PERIOD),
            "$WINDOW": str(WINDOW), "$SLACK": str(SLACK)})
        vault[name] = {"tree": tree, "addr": addr, "seed": seeds[name], "sk": sk, "pkseed": pkseed, "commit": commit,
                       "successor": successor_of.get(name)}
        print(name, "vault tree", len(tree) // 2, "bytes; backstop", backstop[name], "successor", successor_of.get(name))
    # an anyone-can-spend box (sigmaProp(true)) for the foreign-input row f5: its own script passes, so a refusal is the vault's
    true_tree = "10010101d17300"
    true_addr = must(base, f"/utils/ergoTreeToAddress/{true_tree}")["address"]
    tb = wait_tx_outputs(base, must(base, "/wallet/transaction/send", {"requests": [{"address": true_addr, "value": 5_000_000}], "fee": FEE}))
    TRUEBOX = [o for o in tb["outputs"] if o["ergoTree"] == true_tree][0]

    token = issue("QV", 2)          # A and A2 (the replay row 6e) each carry one
    pays = [("A", "FAR", 50_000_000, 1), ("B", "FAR", 10_000_000, 0), ("C", "FAR", 10_000_000, 0),
            ("D", "NEAR", 50_000_000, 0), ("A2", "FAR", 50_000_000, 1), ("G2", "FAR2", 20_000_000, 0),
            ("G3", "FAR3", 20_000_000, 0), ("E0", "FAR", 12_000_000, 0), ("G4", "FAR4", 20_000_000, 0)]
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

    def hash_spend(n, label, inputs, outputs, expect, submit=False, signed_outputs=None, seed=None, sig_xform=None,
                   sk=None, signed_box=None):
        v = vault[seed]            # `seed` is the vault name; the WOTS+ key lives in the vault dict
        ins = []
        for b in inputs:
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                json.dump(signed_outputs or outputs, f)
            # the CLI gives the spend message digest; WOTS+ signs it with this vault's key and public seed
            # (signed_box: the digest of another box's spend, for the replay row)
            msg = bytes.fromhex(wots("sign", v["seed"], "32", "16", (signed_box or b)["boxId"], f.name)["message"])
            os.unlink(f.name)
            sb = wotsplus_sign(v["pkseed"], sk or v["sk"], msg)
            if sig_xform:
                sb = sig_xform(sb)       # tamper the signature for a negative row
            ins.append({"boxId": b["boxId"],
                        "spendingProof": {"proofBytes": "", "extension": {"1": coll_bytes(sb.hex())}}})
        return check(n, label, {"inputs": ins, "dataInputs": [], "outputs": outputs}, expect, submit)

    def merge(n, label, inputs, h, expect, submit=False, name="FAR"):
        tree = vault[name]["tree"]
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

    def forward(n, label, inputs, h, expect, submit=False, name="NEAR", to=None, data=(), extra_inputs=(), keep=None):
        """SK-055 variant 2: the keyless forward. Like merge(), but the successor output sits at `to` (default: the
        vault's committed successor tree), with optional data inputs (the flag) and foreign inputs (row f5)."""
        tree = to if to is not None else vault[vault[name]["successor"]]["tree"]
        total = sum(b["value"] for b in inputs)
        bounty = min(len(inputs) * PER_INPUT, total - max(b["value"] for b in inputs)) if len(inputs) > 1 \
            else min(inputs[0]["value"] // 2, REFRESH)
        value = keep if keep is not None else total - bounty
        assets = {}
        for b in inputs:
            for t in b["assets"]:
                assets[t["tokenId"]] = assets.get(t["tokenId"], 0) + t["amount"]
        outs = [{"value": value, "ergoTree": tree, "creationHeight": h,
                 "assets": [{"tokenId": t, "amount": v} for t, v in assets.items()], "additionalRegisters": {}},
                {"value": total + sum(b["value"] for b in extra_inputs) - value, "ergoTree": FEE_TREE, "creationHeight": h,
                 "assets": [], "additionalRegisters": {}}]
        tx = {"inputs": [{"boxId": b["boxId"], "spendingProof": {"proofBytes": "", "extension": {"0": "0400"}}}
                         for b in list(inputs) + list(extra_inputs)],
              "dataInputs": [{"boxId": d["boxId"]} for d in data], "outputs": outs}
        return check(n, label, tx, expect, submit)

    def flag_successor(b, value_r4, h):
        # The flag box keeps its whole value (its script requires at least that), so the fee must come from the
        # refresher's own input on mainnet; the devnet's minimum fee is 0, so these are fee-less to test the script
        # alone.
        return [{"value": b["value"], "ergoTree": qtree, "creationHeight": h,
                 "assets": [{"tokenId": t["tokenId"], "amount": t["amount"]} for t in b["assets"]],
                 "additionalRegisters": {"R4": value_r4}}]

    A, B, C, D, A2 = box["A"], box["B"], box["C"], box["D"], box["A2"]
    far, near = "FAR", "NEAR"   # hash_spend looks up the WOTS+ key by vault name

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
    # Cryptography seat negatives on the WOTS+ hash key (sig.size guard + a deep flip); sibling of row 4. The
    # other-key and replay negatives are proven on the identical verifier in 6-rekey/devnet-test-wotsplus.py.
    hash_spend("6a", "hash key, signature with 32 bytes appended", [A], outs_to_owner([A], h), "REFUSE", seed=far,
               sig_xform=lambda s: s + b"\x00" * 32)
    hash_spend("6b", "hash key, signature truncated by 32 bytes", [A], outs_to_owner([A], h), "REFUSE", seed=far,
               sig_xform=lambda s: s[:-32])
    hash_spend("6c", "hash key, a byte flipped deep in the signature (chain 33)", [A], outs_to_owner([A], h),
               "REFUSE", seed=far, sig_xform=lambda s: s[:33 * 32] + bytes([s[33 * 32] ^ 1]) + s[33 * 32 + 1:])
    other_sk, _ = wotsplus_keygen(vault["FAR"]["pkseed"], os.urandom(32))
    hash_spend("6d", "hash key: another WOTS+ key's signature (same PKSEED) on A's digest", [A], outs_to_owner([A], h),
               "REFUSE", seed=far, sk=other_sk)
    hash_spend("6e", "hash key: A's valid signature replayed on A2 (same vault, same outputs)", [A2],
               outs_to_owner([A], h), "REFUSE", seed=far, signed_box=A)
    bc = merge(7, "keyless merge of B and C", [B, C], h, "ACCEPT", submit=True)
    BC = [o for o in bc["outputs"] if o["ergoTree"] == vault["FAR"]["tree"]][0]
    wait_height(base, A["creationHeight"] + PERIOD - WINDOW)
    merge(8, "lone refresh of A in the KeepAlive window, no key", [A], height(base), "ACCEPT")
    E0 = box["E0"]
    h = height(base)
    forward("f4", "forward E0 (FAR) to FAR' before quantum day, flag false as a data input", [E0], h, "REFUSE", name="FAR", data=[flag])
    forward("f4b", "forward E0 (FAR) to FAR' before quantum day, no data input", [E0], h, "REFUSE", name="FAR")

    # ---- A.7: flag-box churn. The flag box is older than A, so its refresh window is open now.
    h = height(base)
    held = {"inputs": [{"boxId": A["boxId"], "extension": {}}], "dataInputs": [{"boxId": flag["boxId"]}],
            "outputs": outs_to_owner([A], h)}
    code, held_signed = call(base, "/wallet/transaction/sign", {"tx": held, "inputsRaw": [raw(A)],
                                                               "dataInputsRaw": [raw(flag)]})
    record("7a", "owner spend of A citing the flag box, signed now and held", "SIGNED",
           "SIGNED" if code == 200 else "SIGN-FAIL", "" if code == 200 else held_signed)
    rf = check("7b", "flag box refreshed unchanged in its window, no key",
               {"inputs": [{"boxId": flag["boxId"], "spendingProof": {"proofBytes": "", "extension": {}}}],
                "dataInputs": [], "outputs": flag_successor(flag, FALSE, height(base))}, "ACCEPT", submit=True)
    flag = [o for o in rf["outputs"] if o["ergoTree"] == qtree][0]
    code, o = call(base, "/transactions/check", held_signed)
    record("7c", "the held owner spend submitted after the refresh", "REFUSE",
           "ACCEPT" if code == 200 else "REFUSE", o)
    h = height(base)
    check("7d", "the refreshed flag box refreshed again at once (churn)",
          {"inputs": [{"boxId": flag["boxId"], "spendingProof": {"proofBytes": "", "extension": {}}}],
           "dataInputs": [], "outputs": flag_successor(flag, FALSE, h)}, "REFUSE")
    oq = old_flag
    for n in ("7e", "7e2"):
        r = check(n, "control: pre-window QDay flag box refreshed unchanged (twice in a row)",
                  {"inputs": [{"boxId": oq["boxId"], "spendingProof": {"proofBytes": "", "extension": {}}}],
                   "dataInputs": [], "outputs": [dict(flag_successor(oq, FALSE, height(base))[0], ergoTree=oqtree)]},
                  "ACCEPT", submit=True)
        oq = [x for x in r["outputs"] if x["ergoTree"] == oqtree][0]
    key_spend("7f", "owner spend of A rebuilt on the refreshed flag box", [A], [flag], outs_to_owner([A], height(base)),
              "ACCEPT")

    # ---- A.8: flag NFT provenance (the vault reads the token id of a data input, nothing else)
    G2, G3 = box["G2"], box["G3"]
    h = height(base)
    key_spend("8a", "FAR2 (flag NFT minted with amount 2): owner spend with the real flag (false)", [G2], [flag_q2],
              outs_to_owner([G2], h), "ACCEPT")
    fq = key_spend("8b.a", "the oracle sets FAR2's real flag true", [flag_q2], [], flag_successor(flag_q2, TRUE, h),
                   "ACCEPT", submit=True)
    flag_q2t = [x for x in fq["outputs"] if x["ergoTree"] == qtree][0]
    h = height(base)
    key_spend("8b", "FAR2: owner spend with the real flag, now true", [G2], [flag_q2t], outs_to_owner([G2], h), "REFUSE")
    key_spend("8c", "FAR2: owner spend with the NFT's second unit (a key address, R4 = false)", [G2], [keyaddr_q2],
              outs_to_owner([G2], h), "ACCEPT")
    key_spend("8d", "FAR3 (flag NFT minted amount 1 into a key address, R4 = false): owner spend", [G3], [keyaddr_q3],
              outs_to_owner([G3], h), "ACCEPT")

    # ---- the backstop, flag still false
    wait_height(base, backstop["NEAR"])
    h = height(base)
    key_spend(9, "owner key spends D after NEAR's backstop", [D], [flag], outs_to_owner([D], h), "REFUSE")
    hash_spend(10, "hash key spends D after the backstop", [D], outs_to_owner([D], h), "ACCEPT", submit=True,
               seed=near)

    # ---- A.6: a payment after migration (NEAR's hash key signed once, at row 10)
    fvals = [30_000_000, 31_000_000, 32_000_000, 33_000_000, 34_000_000]
    fdep = wait_tx_outputs(base, must(base, "/wallet/transaction/send", {"requests": [
        {"address": vault["NEAR"]["addr"], "value": v} for v in fvals], "fee": FEE}))
    F1, F2, F3, F4, F5 = [[o for o in fdep["outputs"] if o["ergoTree"] == vault["NEAR"]["tree"] and o["value"] == v][0] for v in fvals]
    h = height(base)
    key_spend("m1", "after migration: owner key spends a new payment F1 (flag false, past the backstop)", [F1], [flag],
              outs_to_owner([F1], h), "REFUSE")
    fm = merge("m2", "after migration: keyless merge of F1 and F2", [F1, F2], h, "ACCEPT", submit=True, name="NEAR")
    FM = [o for o in fm["outputs"] if o["ergoTree"] == vault["NEAR"]["tree"]][0]
    hash_spend("m3", "after migration: NEAR's already-used hash key signs again (checked, not submitted; the forward replaces it)",
               [FM], outs_to_owner([FM], height(base)), "ACCEPT", seed=near)
    # ---- SK-055 variant 2: the keyless forward to the committed successor (NEAR is past its backstop: afterQday holds)
    h = height(base)
    f1 = forward("f1", "forward F3 alone, keyless, to NEAR' (past the backstop, no data input)", [F3], h, "ACCEPT", submit=True)
    F3f = [o for o in f1["outputs"] if o["ergoTree"] == vault["NEAR'"]["tree"]][0]
    forward("f2", "forward F5 to the owner's key address", [F5], h, "REFUSE", to=owner_tree)
    forward("f3", "forward F5 to FAR' (a QVault2 tree that is not NEAR's committed successor)", [F5], h, "REFUSE", to=vault["FAR'"]["tree"])
    forward("f5", "forward F5 with a foreign input (an anyone-can-spend box paying the fee)", [F5], h, "REFUSE", extra_inputs=[TRUEBOX])
    forward("f6", "forward F5 keeping less than total - bounty", [F5], h, "REFUSE", keep=F5["value"] - REFRESH - 1)
    f7 = forward("f7", "FM and F4 merged and forwarded to NEAR' in one transaction", [FM, F4], h, "ACCEPT", submit=True)
    FMf = [o for o in f7["outputs"] if o["ergoTree"] == vault["NEAR'"]["tree"]][0]
    h = height(base)
    hash_spend("f9", "the forwarded box at NEAR' spent by NEAR''s own hash key", [FMf], outs_to_owner([FMf], h), "ACCEPT",
               submit=True, seed="NEAR'")
    G4 = box["G4"]
    forward("f8", "FAR4: forward G4 to FAR4' opened by a fake flag (NFT unit at a key address, R4 = true)", [G4], h, "ACCEPT",
            name="FAR4", data=[fake_true_q4])

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
    check(14, "flag box refreshed unchanged right after the flip, no key (outside its window)",
          {"inputs": [{"boxId": flag2["boxId"], "spendingProof": {"proofBytes": "", "extension": {}}}],
           "dataInputs": [], "outputs": flag_successor(flag2, TRUE, h)}, "REFUSE")

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
    e2 = wait_tx_outputs(base, must(base, "/wallet/transaction/send", {"requests": [
        {"address": vault["FAR"]["addr"], "value": 11_000_000}], "fee": FEE}))
    E2 = [o for o in e2["outputs"] if o["ergoTree"] == vault["FAR"]["tree"]][0]
    h = height(base)
    forward("f1b", "after the flag: forward E2 (FAR) to FAR' with the true flag box as a data input", [E2], h, "ACCEPT",
            submit=True, name="FAR", data=[flag2])
    forward("f4c", "after the flag: forward E0 (FAR) with no data input (flag not shown, before FAR's backstop)", [box["E0"]], h, "REFUSE", name="FAR")
    wait_height(base, flag2["creationHeight"] + PERIOD - WINDOW)
    check("14b", "flag box refreshed unchanged in its window, no key",
          {"inputs": [{"boxId": flag2["boxId"], "spendingProof": {"proofBytes": "", "extension": {}}}],
           "dataInputs": [], "outputs": flag_successor(flag2, TRUE, height(base))}, "ACCEPT")

    # keep only JSON-serializable, non-secret vault fields (drop the seed, the WOTS+ secret key sk and the raw seed)
    _keep = {"tree", "addr", "commit", "successor"}
    json.dump({"qdayNft": qday_nft, "flagTree": qtree, "flagTreePreWindow": oqtree,
               "vaults": {k: {kk: vv for kk, vv in v.items() if kk in _keep} for k, v in vault.items()},
               "backstops": backstop, "results": results}, open(HERE / a.out, "w"), indent=1)
    bad = [r for r in results if not r["ok"]]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


if __name__ == "__main__":
    main()
