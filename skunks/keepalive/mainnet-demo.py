#!/usr/bin/env python3
"""KeepAlive on mainnet: the skunkyard test wallet's vault, paid like any address, then kept by others.

The vault is KeepAliveAddress.es at mainnet constants, the devnet-tested tree (kaa-mainnet-G.tree) with the owner
key set to the wallet's (kaa-mainnet-wallet.tree / .address). A lone refresh opens only in the 21,600 blocks before
a box is 1,051,200 blocks old, so on mainnet today the demo uses the path open at any time, the merge, which runs
the same checks (same script, every token kept, value less at most the bounty, fresh creation height, no growth).

  deposit           (signed by the wallet)  mint one demo token into vault box A (0.01 ERG), and pay vault boxes
                                            B (0.01 ERG) and C (0.005 ERG), as any payer would
  merge-keyless     (no signature at all)   merge A and B into one vault box; the boxes pay the 0.001 ERG fee out
                                            of the bounty their script allows (2 x 0.0005): what any stranger can do
  merge-sponsored   (signed by the wallet)  merge that box and C, a wallet box paying the fee: the vault keeps every
                                            nanoERG, the sponsor's case (a project, a wallet service, an archive)

Each writes tx/<step>.json; deposit and merge-sponsored go through skunks/oneshot/scripts/mainnet-sign.mjs;
merge-keyless is checked and, with --submit, posted to the node directly (it spends nothing of the wallet's).

usage: mainnet-demo.py deposit | merge-keyless [--submit] | merge-sponsored
"""
import argparse, importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("bt", HERE.parent / "upkeep" / "mainnet" / "babel-take.py")
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)
NODE = "http://128.253.41.100:9053"
WALLET = (Path.home() / ".config" / "skunkyard" / "mainnet-wallet.address").read_text().strip()
VAULT_TREE = (HERE / "kaa-mainnet-wallet.tree").read_text().strip()
VAULT_ADDR = (HERE / "kaa-mainnet-wallet.address").read_text().strip()
FEE = 1_100_000
KEYLESS_FEE = 1_000_000                    # = the merge bounty for two inputs, min(2 x 500,000, total - largest)
STATE = HERE / "tx" / "mainnet-demo-state.json"


def tip():
    return json.loads(bt.http(NODE + "/info")[1])["fullHeight"]


def coll_byte(s):
    b = s.encode()
    return "0e" + bytes([len(b)]).hex() + b.hex()


def inp(box_id, var0=False):
    return {"boxId": box_id, "spendingProof": {"proofBytes": "", "extension": {"0": "0400"} if var0 else {}}}


def out(value, tree, h, assets=(), regs=None):
    return {"value": value, "ergoTree": tree, "creationHeight": h,
            "assets": [{"tokenId": t, "amount": n} for t, n in assets], "additionalRegisters": regs or {}}


def wallet_box(need):
    boxes = [b for b in bt.get(f"/boxes/unspent/byAddress/{WALLET}?limit=50")["items"] if not b["assets"]]
    boxes.sort(key=lambda b: -b["value"])
    if not boxes or boxes[0]["value"] < need:
        sys.exit("no single wallet box large enough")
    return boxes[0]


def vault_boxes():
    return bt.get(f"/boxes/unspent/byAddress/{VAULT_ADDR}?limit=50")["items"]


def save(name, tx, state=None):
    p = HERE / "tx" / f"mainnet-demo-{name}.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(tx, indent=1))
    if state is not None:
        STATE.write_text(json.dumps(state, indent=1))
    print("wrote", p)


def deposit(a):
    h = tip()
    w = wallet_box(30_000_000)
    token = w["boxId"]                     # a token minted in this transaction takes the first input's id
    a_val, b_val, c_val = 10_000_000, 10_000_000, 5_000_000
    regs = {"R4": coll_byte("skunkyard KeepAlive demo"),
            "R5": coll_byte("Kept from storage rent by anyone: skunkyard skunks/keepalive"), "R6": coll_byte("0")}
    change = w["value"] - a_val - b_val - c_val - FEE
    tx = {"inputs": [inp(w["boxId"])], "dataInputs": [],
          "outputs": [out(a_val, VAULT_TREE, h, [(token, 1)], regs), out(b_val, VAULT_TREE, h),
                      out(c_val, VAULT_TREE, h), out(change, bt.p2pk_tree(WALLET), h), out(FEE, bt.FEE_TREE, h)]}
    save("deposit", tx, {"token": token})
    print("token", token, "vault", VAULT_ADDR[:16] + "...")


def merge_keyless(a):
    h = tip()
    st = json.loads(STATE.read_text())
    vb = vault_boxes()
    A = [b for b in vb if any(t["tokenId"] == st["token"] for t in b["assets"])]
    B = [b for b in vb if not b["assets"] and b["value"] == 10_000_000]
    if len(A) != 1 or len(B) != 1:
        sys.exit(f"expected the token box and the 0.01 ERG box in the vault: {[(b['boxId'][:8], b['value']) for b in vb]}")
    A, B = A[0], B[0]
    total = A["value"] + B["value"]
    bounty = min(2 * 500_000, total - max(A["value"], B["value"]))
    assert bounty == KEYLESS_FEE
    tx = {"inputs": [inp(A["boxId"], True), inp(B["boxId"], True)], "dataInputs": [],
          "outputs": [out(total - KEYLESS_FEE, VAULT_TREE, h, [(st["token"], 1)]), out(KEYLESS_FEE, bt.FEE_TREE, h)]}
    save("merge-keyless", tx)
    code, text = bt.http(NODE + "/transactions/check", tx)
    print("check:", code, text[:300])
    if a.submit and code == 200:
        code, text = bt.http(NODE + "/transactions", tx)
        print("submit:", code, text[:300])


def merge_sponsored(a):
    h = tip()
    st = json.loads(STATE.read_text())
    vb = vault_boxes()
    K = [b for b in vb if any(t["tokenId"] == st["token"] for t in b["assets"])]
    C = [b for b in vb if not b["assets"] and b["value"] == 5_000_000]
    if len(K) != 1 or len(C) != 1:
        sys.exit(f"expected the merged token box and the 0.005 ERG box: {[(b['boxId'][:8], b['value']) for b in vb]}")
    K, C = K[0], C[0]
    w = wallet_box(5_000_000)
    tx = {"inputs": [inp(K["boxId"], True), inp(C["boxId"], True), inp(w["boxId"])], "dataInputs": [],
          "outputs": [out(K["value"] + C["value"], VAULT_TREE, h, [(st["token"], 1)]),
                      out(w["value"] - FEE, bt.p2pk_tree(WALLET), h), out(FEE, bt.FEE_TREE, h)]}
    save("merge-sponsored", tx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["deposit", "merge-keyless", "merge-sponsored"])
    ap.add_argument("--submit", action="store_true")
    a = ap.parse_args()
    {"deposit": deposit, "merge-keyless": merge_keyless, "merge-sponsored": merge_sponsored}[a.step](a)


if __name__ == "__main__":
    main()
