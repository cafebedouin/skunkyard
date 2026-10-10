#!/usr/bin/env python3
"""KeepAlive receive address on a peeryard devnet: payments to it as to any address, then keyless merges and
refreshes, every path and attack judged by the node (same devnet and rules as devnet-test.py).

Payments, as ordinary wallet sends to the owner's vault address (no registers): P1 0.05 ERG + 1 unit, P2 0.001 ERG
+ 2 units, P3 0.001 ERG + 3 units, D 0.0003 ERG dust with no token.

  1  a lone box refreshed before the window                       REFUSE
  2  a merge that drops one token unit                            REFUSE
  3  a merge taking the bounty + 1                                REFUSE
  4  a merge into another owner's vault                           REFUSE
  5  a refresh whose successor is dated SLACK + 1 back (in the window) REFUSE
  6  P2 and P3 split into two outputs, each its own tokens        REFUSE (double satisfaction)
  7  dust merged with the main box, taking more than the dust     REFUSE (the main box never pays a merge)
  8  dust merged with the main box, taking exactly the dust       ACCEPT (checked only)
  9  P1 + P2 + P3 + D merged, honest                               ACCEPT (mined)
 10  the merged box refreshed alone at once                       REFUSE (window)
 11  the merged box refreshed alone in the window                 ACCEPT (mined)
 12  the owner spends it with its key                             ACCEPT (mined)

usage: devnet-test-address.py [--node http://127.0.0.1:9180] [--out address-results.json]
"""
import argparse, importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("kt", HERE / "devnet-test.py")
kt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kt)
call, must, height, wait_height, wait_tx_outputs = kt.call, kt.must, kt.height, kt.wait_height, kt.wait_tx_outputs
FEE, FEE_TREE, G = kt.FEE, kt.FEE_TREE, kt.G
PERIOD, WINDOW, PER_INPUT, REFRESH, SLACK = 40, 20, 500_000, 2_000_000, 10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", default="http://127.0.0.1:9180")
    ap.add_argument("--out", default="address-results.json")
    a = ap.parse_args()
    base = a.node
    tree = (HERE / "kaa-devnet-owner.tree").read_text().strip()
    other = (HERE / "kaa-devnet-other.tree").read_text().strip()
    vault_addr = (HERE / "kaa-devnet-owner.address").read_text().strip()
    owner_addr = must(base, "/wallet/addresses")[0]
    pk = must(base, f"/utils/addressToRaw/{owner_addr}")["raw"]
    if pk not in tree:
        sys.exit("the compiled vault is not the node wallet's")

    issue = wait_tx_outputs(base, must(base, "/wallet/transaction/send", {"requests": [{
        "address": owner_addr, "ergValue": 1_000_000, "amount": 6, "name": "KAA", "description": "keepalive address test",
        "decimals": 0}], "fee": FEE}))
    token = issue["outputs"][0]["assets"][0]["tokenId"]
    pays = [(50_000_000, 1), (1_000_000, 2), (1_000_000, 3), (300_000, 0)]
    reqs = [{"address": vault_addr, "value": v, "assets": ([{"tokenId": token, "amount": n}] if n else [])}
            for v, n in pays]
    sent = wait_tx_outputs(base, must(base, "/wallet/transaction/send", {"requests": reqs, "fee": FEE}))
    boxes = [o for o in sent["outputs"] if o["ergoTree"] == tree]
    by = {(b["value"], sum(t["amount"] for t in b["assets"])): b for b in boxes}
    p1, p2, p3, d = (by[k] for k in pays)
    print("token", token, "payments", [b["boxId"][:8] for b in (p1, p2, p3, d)], "at", p1["creationHeight"])

    results = []

    def toks(bs):
        out = {}
        for b in bs:
            for t in b["assets"]:
                out[t["tokenId"]] = out.get(t["tokenId"], 0) + t["amount"]
        return [{"tokenId": k, "amount": v} for k, v in out.items()]

    def maintain(ins, h, take, succ_tree=None, drop=0, old=False):
        """Merge (or refresh) `ins` into output 0, the executor taking `take` (fee included)."""
        assets = toks(ins)
        if drop:
            assets[0]["amount"] -= drop
        outs = [{"value": sum(b["value"] for b in ins) - take, "ergoTree": succ_tree or tree,
                 "creationHeight": h - (SLACK + 1 if old else 0), "assets": assets, "additionalRegisters": {}}]
        if drop:
            outs.append({"value": 300_000, "ergoTree": "0008cd" + G, "creationHeight": h,
                         "assets": [{"tokenId": token, "amount": drop}], "additionalRegisters": {}})
            outs[0]["value"] -= 300_000
        rest = take - FEE
        if rest > 0:
            outs.append({"value": rest, "ergoTree": "0008cd" + G, "creationHeight": h, "assets": [],
                         "additionalRegisters": {}})
        outs.append({"value": FEE if rest >= 0 else take, "ergoTree": FEE_TREE, "creationHeight": h, "assets": [],
                     "additionalRegisters": {}})
        return {"inputs": [{"boxId": b["boxId"], "spendingProof": {"proofBytes": "", "extension": {"0": "0400"}}}
                           for b in ins], "dataInputs": [], "outputs": outs}

    def case(n, label, tx, expect, submit=False):
        code, out = call(base, "/transactions/check", tx)
        detail = out if isinstance(out, str) else ""
        got = "ACCEPT" if code == 200 else ("REFUSE" if "should pass verification" in detail else "MALFORMED")
        ok = got == expect
        results.append({"case": n, "label": label, "expect": expect, "got": got, "ok": ok,
                        "detail": (out if isinstance(out, str) else str(out)).replace("\n", " ")[:300]})
        print(f"{n:>2} {label:<60} expect {expect:<6} got {got:<9} {'ok' if ok else 'WRONG'}")
        if not ok and got == "MALFORMED":
            print("    ", detail.replace("\n", " ")[:300])
        return must(base, "/transactions", tx) if submit and code == 200 else None

    h = height(base)
    case(1, "a lone box refreshed before the window", maintain([p1], h, REFRESH), "REFUSE")
    three = [p1, p2, p3]
    b3 = min(3 * PER_INPUT, sum(b["value"] for b in three) - p1["value"])
    case(2, "a merge that drops one token unit", maintain(three, h, b3, drop=1), "REFUSE")
    case(3, "a merge taking the bounty + 1", maintain(three, h, b3 + 1), "REFUSE")
    case(4, "a merge into another owner's vault", maintain(three, h, b3, succ_tree=other), "REFUSE")
    split = maintain([p2], h, 0)
    split["outputs"] = [{"value": p2["value"], "ergoTree": tree, "creationHeight": h, "assets": p2["assets"],
                         "additionalRegisters": {}},
                        {"value": p3["value"], "ergoTree": tree, "creationHeight": h, "assets": p3["assets"],
                         "additionalRegisters": {}}]
    split["inputs"] = [{"boxId": p2["boxId"], "spendingProof": {"proofBytes": "", "extension": {"0": "0400"}}},
                       {"boxId": p3["boxId"], "spendingProof": {"proofBytes": "", "extension": {"0": "0402"}}}]
    case(6, "P2 and P3 split into two outputs, each its own tokens", split, "REFUSE")
    # Dust merged with the main box: the cap is total - largest = the dust's own value. The fee is part of the take,
    # so with 0.0003 ERG of dust and a 0.001 fee the honest shape pays the fee from outside: a second, plain input.
    case(7, "dust merged with the main box, taking more than the dust", maintain([p1, d], h, d["value"] + 1), "REFUSE")
    case(8, "dust merged with the main box, taking exactly the dust", maintain([p1, d], h, d["value"]), "ACCEPT")
    four = [p1, p2, p3, d]
    b4 = min(4 * PER_INPUT, sum(b["value"] for b in four) - p1["value"])
    txid = case(9, "P1 + P2 + P3 + D merged, honest", maintain(four, h, b4), "ACCEPT", submit=True)
    merged = wait_tx_outputs(base, txid)["outputs"][0] if txid else None
    if merged:
        print("merged into", merged["boxId"][:8], "value", merged["value"], "tokens", merged["assets"],
              "created", merged["creationHeight"])
        h = height(base)
        case(10, "the merged box refreshed alone at once", maintain([merged], h, REFRESH), "REFUSE")
        wait_height(base, merged["creationHeight"] + PERIOD - WINDOW)
        h = height(base)
        # Here the box is old enough that a successor SLACK + 1 blocks back still respects consensus (no output older
        # than its newest input, EIP-39), so only the vault's own rule can refuse it
        case(5, "a refresh whose successor is dated SLACK + 1 back", maintain([merged], h, REFRESH, old=True), "REFUSE")
        rid = case(11, "the merged box refreshed alone in the window", maintain([merged], h, REFRESH), "ACCEPT",
                   submit=True)
        fresh = wait_tx_outputs(base, rid)["outputs"][0] if rid else None
        if fresh:
            raw = must(base, f"/utxo/byIdBinary/{fresh['boxId']}")["bytes"]
            h = height(base)
            unsigned = {"inputs": [{"boxId": fresh["boxId"], "extension": {}}], "dataInputs": [],
                        "outputs": [{"value": fresh["value"] - FEE, "ergoTree": "0008cd" + pk, "creationHeight": h,
                                     "assets": fresh["assets"], "additionalRegisters": {}},
                                    {"value": FEE, "ergoTree": FEE_TREE, "creationHeight": h, "assets": [],
                                     "additionalRegisters": {}}]}
            code, signed = call(base, "/wallet/transaction/sign", {"tx": unsigned, "inputsRaw": [raw],
                                                                 "dataInputsRaw": []})
            if code == 200:
                oid = case(12, "the owner spends it with its key", signed, "ACCEPT", submit=True)
                if oid:
                    wait_tx_outputs(base, oid)
            else:
                results.append({"case": 12, "label": "owner spend", "expect": "ACCEPT", "got": "SIGN FAILED",
                                "ok": False, "detail": str(signed)[:300]})
                print("12 owner spend: signing failed", signed)
    json.dump({"tree": tree, "token": token, "payments": [b["boxId"] for b in (p1, p2, p3, d)], "results": results},
              open(a.out, "w"), indent=1)
    bad = [r for r in results if not r["ok"]]
    print("ALL AS EXPECTED" if not bad and len(results) == 12 else f"{len(bad)} UNEXPECTED of {len(results)}")
    sys.exit(1 if bad or len(results) != 12 else 0)


if __name__ == "__main__":
    main()
