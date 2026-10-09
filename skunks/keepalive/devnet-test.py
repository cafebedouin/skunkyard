#!/usr/bin/env python3
"""KeepAlive vault on a peeryard devnet: every path and attack, judged by the node itself.

Against one mining node with its REST API on --node (peeryard: `rig/devnet.sh up rig/examples/lithos-upkeep.json
keepalive`, then `rig/devnet.sh expose A 9180 keepalive`) and the devnet tree (PERIOD 40, WINDOW 20, BOUNTY
0.002 ERG, SLACK 10). The node's wallet is the owner. Each case is a transaction the node checks
(/transactions/check); ACCEPT cases are then mined where the test needs them.

  1  refresh before the window                         REFUSE
  2  refresh in the window, honest                     ACCEPT (mined)
  3  a successor without the token                     REFUSE
  4  a successor taking bounty + 1                     REFUSE
  5  a successor with another owner                    REFUSE
  6  a successor whose R5 is not the spent box's id    REFUSE
  7  a successor dated SLACK + 1 blocks back           REFUSE
  8  a successor padded with an R6                     REFUSE
  9  two identical vaults refreshed into one output    REFUSE (double satisfaction)
 10  the refreshed box refreshed again at once         REFUSE (window restarted)
 11  the owner spends the refreshed box with its key   ACCEPT (mined)

usage: devnet-test.py [--node http://127.0.0.1:9180] [--tree-file ka-devnet.tree] [--out results.json]
"""
import argparse, json, sys, time, urllib.request

KEY = "hello"
PERIOD, WINDOW, BOUNTY, SLACK = 40, 20, 2_000_000, 10
FEE = 1_000_000
# A valid key nobody holds (the curve generator), for outputs that only need to be well formed
G = "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"


def call(base, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data,
                                 headers={"Content-Type": "application/json", "api_key": KEY})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:600]


def must(base, path, body=None):
    code, out = call(base, path, body)
    if code != 200:
        sys.exit(f"{path}: {code} {out}")
    return out


def height(base):
    return must(base, "/info")["fullHeight"] or 0


def wait_height(base, h):
    while height(base) < h:
        time.sleep(5)


def wait_box(base, box_id, gone=False):
    for _ in range(120):
        code, _ = call(base, f"/utxo/byId/{box_id}")
        if (code == 200) != gone:
            return
        time.sleep(5)
    sys.exit(f"box {box_id} never {'spent' if gone else 'appeared'}")


def wait_tx_outputs(base, tx_id):
    for _ in range(120):
        code, tx = call(base, f"/blockchain/transaction/byId/{tx_id}")
        if code == 200:
            return tx
        time.sleep(5)
    sys.exit(f"transaction {tx_id} never mined")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", default="http://127.0.0.1:9180")
    ap.add_argument("--tree-file", required=True)
    ap.add_argument("--out", default="devnet-results.json")
    a = ap.parse_args()
    base, tree = a.node, open(a.tree_file).read().strip()
    vault_addr = must(base, "/utils/ergoTreeToAddress/" + tree)["address"]

    # The owner: the node's wallet key
    while must(base, "/wallet/balances")["balance"] < 2_000_000_000:
        print("waiting for the wallet to mature rewards…"); time.sleep(10)
    owner_addr = must(base, "/wallet/addresses")[0]
    pk = must(base, f"/utils/addressToRaw/{owner_addr}")["raw"]
    owner_reg = "08cd" + pk
    owner_tree = "0008cd" + pk

    # A token, then three vaults: A with 1 unit, and B, C with 5 units each (identical, for the double-satisfaction case)
    tx_id = must(base, "/wallet/transaction/send", {"requests": [{"address": owner_addr, "ergValue": 1_000_000,
                 "amount": 11, "name": "KA", "description": "keepalive test", "decimals": 0}], "fee": FEE})
    issue = wait_tx_outputs(base, tx_id)
    token = issue["outputs"][0]["assets"][0]["tokenId"]
    print("token", token)
    reqs = [{"address": vault_addr, "value": 50_000_000, "assets": [{"tokenId": token, "amount": n}],
             "registers": {"R4": owner_reg}} for n in (1, 5, 5)]
    dep = wait_tx_outputs(base, must(base, "/wallet/transaction/send", {"requests": reqs, "fee": FEE}))
    vaults = [o for o in dep["outputs"] if o["ergoTree"] == tree]
    va, vb, vc = vaults
    created = va["creationHeight"]
    print("vaults", va["boxId"][:8], vb["boxId"][:8], vc["boxId"][:8], "created", created)

    results = []

    def refresh(box, h, **bad):
        """One refresh of `box` at height h, honest unless a fault is named."""
        regs = {"R4": owner_reg, "R5": "0e20" + box["boxId"]}
        if "owner" in bad:
            regs["R4"] = "08cd" + G
        if "r5" in bad:
            regs["R5"] = "0e20" + "22" * 32
        if "pad" in bad:
            regs["R6"] = "0e" + "40" + "33" * 64
        assets = [] if "notoken" in bad else box["assets"]
        take = BOUNTY + (1 if "greedy" in bad else 0)
        succ = {"value": box["value"] - take, "ergoTree": tree, "creationHeight": h - (SLACK + 1 if "old" in bad else 0),
                "assets": [{"tokenId": t["tokenId"], "amount": t["amount"]} for t in assets], "additionalRegisters": regs}
        outs = [succ]
        if "notoken" in bad:
            outs.append({"value": 1_000_000, "ergoTree": "0008cd" + G, "creationHeight": h,
                         "assets": [{"tokenId": t["tokenId"], "amount": t["amount"]} for t in box["assets"]],
                         "additionalRegisters": {}})
        bounty_out = take - FEE - (1_000_000 if "notoken" in bad else 0)
        if bounty_out > 0:
            outs.append({"value": bounty_out, "ergoTree": "0008cd" + G, "creationHeight": h, "assets": [],
                         "additionalRegisters": {}})
        outs.append({"value": FEE, "ergoTree": FEE_TREE, "creationHeight": h, "assets": [], "additionalRegisters": {}})
        return {"inputs": [{"boxId": box["boxId"], "spendingProof": {"proofBytes": "", "extension": {"0": "0400"}}}],
                "dataInputs": [], "outputs": outs}

    def case(n, label, tx, expect, submit=False):
        code, out = call(base, "/transactions/check", tx)
        detail = out if isinstance(out, str) else ""
        # A refusal counts only if the vault's script refused: anything else (a malformed transaction) proves nothing
        got = "ACCEPT" if code == 200 else ("REFUSE" if "should pass verification" in detail else "MALFORMED")
        ok = got == expect
        results.append({"case": n, "label": label, "expect": expect, "got": got, "ok": ok,
                        "detail": detail.replace("\n", " ")[:300]})
        print(f"{n:>2} {label:<48} expect {expect:<6} got {got:<6} {'ok' if ok else 'WRONG'}")
        if submit and code == 200:
            return must(base, "/transactions", tx)
        return None

    h = height(base)
    case(1, "refresh before the window", refresh(va, h), "REFUSE")
    wait_height(base, created + PERIOD - WINDOW)
    h = height(base)
    for n, label, bad in [(3, "a successor without the token", "notoken"),
                          (4, "a successor taking bounty + 1", "greedy"),
                          (5, "a successor with another owner", "owner"),
                          (6, "a successor whose R5 is not the spent box's id", "r5"),
                          (7, "a successor dated SLACK + 1 blocks back", "old"),
                          (8, "a successor padded with an R6", "pad")]:
        case(n, label, refresh(va, h, **{bad: True}), "REFUSE")
    # Double satisfaction: B and C point at one output that names B
    two = refresh(vb, h)
    two["inputs"].append({"boxId": vc["boxId"], "spendingProof": {"proofBytes": "", "extension": {"0": "0400"}}})
    # C's value and tokens go to the attacker; B's honest successor at output 0 is meant to satisfy C as well
    two["outputs"].insert(1, {"value": vc["value"], "ergoTree": "0008cd" + G, "creationHeight": h,
                              "assets": [{"tokenId": t["tokenId"], "amount": t["amount"]} for t in vc["assets"]],
                              "additionalRegisters": {}})
    case(9, "two identical vaults refreshed into one output", two, "REFUSE")
    txid = case(2, "refresh in the window, honest", refresh(va, h), "ACCEPT", submit=True)
    mined = wait_tx_outputs(base, txid)
    va2 = mined["outputs"][0]
    print("refreshed", va["boxId"][:8], "->", va2["boxId"][:8], "created", va2["creationHeight"],
          "R5", va2["additionalRegisters"].get("R5", "")[:12])
    h = height(base)
    case(10, "the refreshed box refreshed again at once", refresh(va2, h), "REFUSE")

    # The owner spends the refreshed box: the node's wallet signs (it holds the owner key)
    raw = must(base, f"/utxo/byIdBinary/{va2['boxId']}")["bytes"]
    unsigned = {"inputs": [{"boxId": va2["boxId"], "extension": {}}], "dataInputs": [],
                "outputs": [{"value": va2["value"] - FEE, "ergoTree": owner_tree, "creationHeight": h,
                             "assets": [{"tokenId": t["tokenId"], "amount": t["amount"]} for t in va2["assets"]],
                             "additionalRegisters": {}},
                            {"value": FEE, "ergoTree": FEE_TREE, "creationHeight": h, "assets": [],
                             "additionalRegisters": {}}]}
    code, signed = call(base, "/wallet/transaction/sign", {"tx": unsigned, "inputsRaw": [raw], "dataInputsRaw": []})
    if code != 200:
        results.append({"case": 11, "label": "owner spend", "expect": "ACCEPT", "got": "SIGN FAILED", "ok": False,
                        "detail": str(signed)[:300]})
        print("11 owner spend: signing failed", signed)
    else:
        oid = case(11, "the owner spends the refreshed box with its key", signed, "ACCEPT", submit=True)
        wait_tx_outputs(base, oid)
    json.dump({"tree": tree, "token": token, "vaults": [va["boxId"], vb["boxId"], vc["boxId"]],
               "refreshed": va2["boxId"], "results": results}, open(a.out, "w"), indent=1)
    bad = [r for r in results if not r["ok"]]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")
    sys.exit(1 if bad else 0)


FEE_TREE = ("1005040004000e36100204a00b08cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192"
            "a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac93b1a57304")

if __name__ == "__main__":
    main()
