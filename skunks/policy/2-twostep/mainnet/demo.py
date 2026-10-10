#!/usr/bin/env python3
"""The two-step withdrawal vault on mainnet: the skunkyard test wallet's vault, an announce, a keyless completion and
a recovery cancel.

Trees: skunks/oneshot/scripts/twostep-trees.mjs (the devnet-tested Vault.tree and Pending.tree with only the owner
and recovery keys substituted, each placeholder exactly once; DELAY 15 blocks, as tested). Owner = the wallet's key
(m/44'/429'/0'/0/0), recovery = its second path (m/44'/429'/0'/0/1).

  deposit          (wallet signs)      two vault boxes V1, V2 of 0.005 ERG, and a 0.003 ERG fee box at the recovery
                                       address (it pays the cancel's fee, so the cancel is signed by the recovery key
                                       alone)
  announce V       (wallet signs)      vault box V -> a pending box: destination R4 = the wallet, deadline R5 = the
                                       next block's height + DELAY + 3, vault R6; a wallet box pays the fee
  complete P       (no vault key)      at or after the deadline, P -> the wallet, exactly its value; a wallet box pays
                                       the fee (sponsored, as the sponsored KeepAlive merge)
  cancel P         (recovery key)      before the deadline, P -> back to the vault, exactly its value; the recovery
                                       address's box pays the fee (scripts/mainnet-sign-cancel.mts)

Every step writes tx/<step>.json, unsigned; deposit, announce and complete are signed and checked by
skunks/oneshot/scripts/mainnet-sign.mjs, cancel by mainnet-sign-cancel.mts. Each is built for the next block and the
node's check is the verdict (the wallet-versus-check height offset, EXPERIMENTS.md finding 1).

usage: demo.py deposit | announce <vaultBoxId> | complete <pendingBoxId> | cancel <pendingBoxId>
"""
import importlib.util, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location("bt", ROOT / "upkeep" / "mainnet" / "babel-take.py")
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)
NODE = "http://128.253.41.100:9053"
FEE = 1_100_000
V_VALUE, RECOVERY_FEE_BOX = 5_000_000, 3_000_000

info = json.loads(subprocess.run(["node", "scripts/twostep-info.mjs"], cwd=ROOT / "oneshot", capture_output=True,
                                 text=True, check=True).stdout)
WALLET, RECOVERY, VAULT, PENDING, DELAY = (info[k] for k in ("walletTree", "recoveryTree", "vault", "pending", "delay"))


def tip():
    return json.loads(bt.http(NODE + "/info")[1])["fullHeight"]


def vlq(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out).hex()


def coll(h):
    return "0e" + vlq(len(h) // 2) + h


def int_c(n):
    return "04" + vlq((n << 1) ^ (n >> 31))


def inp(box_id):
    return {"boxId": box_id, "spendingProof": {"proofBytes": "", "extension": {}}}


def out(value, tree, h, assets=(), regs=None):
    return {"value": value, "ergoTree": tree, "creationHeight": h,
            "assets": [{"tokenId": a["tokenId"], "amount": a["amount"]} for a in assets], "additionalRegisters": regs or {}}


def box(box_id):
    b = bt.get(f"/boxes/{box_id}")
    if b.get("spentTransactionId"):
        sys.exit(f"box {box_id} is spent")
    return b


def wallet_box(need):
    addr = (Path.home() / ".config" / "skunkyard" / "mainnet-wallet.address").read_text().strip()
    bs = sorted([b for b in bt.get(f"/boxes/unspent/byAddress/{addr}?limit=50")["items"] if not b["assets"]],
                key=lambda b: -b["value"])
    if not bs or bs[0]["value"] < need:
        sys.exit("no wallet box large enough")
    return bs[0]


def save(name, tx):
    p = HERE / "tx" / f"{name}.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(tx, indent=1))
    print("wrote", p)


def main():
    step = sys.argv[1]
    h = tip()
    if step == "deposit":
        w = wallet_box(30_000_000)
        change = w["value"] - 2 * V_VALUE - RECOVERY_FEE_BOX - FEE
        save("deposit", {"inputs": [inp(w["boxId"])], "dataInputs": [],
                         "outputs": [out(V_VALUE, VAULT, h), out(V_VALUE, VAULT, h), out(RECOVERY_FEE_BOX, RECOVERY, h),
                                     out(change, WALLET, h), out(FEE, bt.FEE_TREE, h)]})
    elif step == "announce":
        v = box(sys.argv[2])
        assert v["ergoTree"] == VAULT
        w = wallet_box(5_000_000)
        deadline = h + 1 + DELAY + 3
        regs = {"R4": coll(WALLET), "R5": int_c(deadline), "R6": coll(VAULT)}
        save(f"announce-{v['boxId'][:8]}", {"inputs": [inp(v["boxId"]), inp(w["boxId"])], "dataInputs": [],
             "outputs": [out(v["value"], PENDING, h, v["assets"], regs), out(w["value"] - FEE, WALLET, h),
                         out(FEE, bt.FEE_TREE, h)]})
        print("deadline", deadline, "(complete when the next block's height >= it; cancel well before)")
    elif step == "complete":
        p = box(sys.argv[2])
        assert p["ergoTree"] == PENDING
        deadline = json.loads(p["additionalRegisters"]["R5"]["renderedValue"])
        if h + 1 < deadline:
            sys.exit(f"the next block is {h + 1}; the deadline is {deadline}")
        w = wallet_box(5_000_000)
        save(f"complete-{p['boxId'][:8]}", {"inputs": [inp(p["boxId"]), inp(w["boxId"])], "dataInputs": [],
             "outputs": [out(p["value"], WALLET, h, p["assets"]), out(w["value"] - FEE, WALLET, h),
                         out(FEE, bt.FEE_TREE, h)]})
    elif step == "cancel":
        p = box(sys.argv[2])
        assert p["ergoTree"] == PENDING
        deadline = json.loads(p["additionalRegisters"]["R5"]["renderedValue"])
        if h + 1 > deadline - 5:
            sys.exit(f"too close to the deadline ({deadline}) for a cancel well inside the window")
        rec = [b for b in bt.get(f"/boxes/unspent/byErgoTree/{RECOVERY}?limit=10")["items"]]
        if not rec:
            sys.exit("no box at the recovery address")
        r = rec[0]
        save(f"cancel-{p['boxId'][:8]}", {"inputs": [inp(p["boxId"]), inp(r["boxId"])], "dataInputs": [],
             "outputs": [out(p["value"], VAULT, h, p["assets"]), out(r["value"] - FEE, WALLET, h),
                         out(FEE, bt.FEE_TREE, h)]})
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
