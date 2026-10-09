#!/usr/bin/env python3
"""A direct swap on an ErgoDEX v1 ERG pool, funded from the skunkyard mainnet test wallet; unsigned (sign with
skunks/oneshot/scripts/mainnet-sign.mjs, which checks and caps it).

    inputs:  0 pool (no signature), then wallet boxes (signed by mainnet-sign.mjs)
    outputs: 0 pool successor, 1 wallet (change, plus any tokens bought, minus any sold), 2 miner fee

--buy-erg X     put X nanoERG into the pool for its token (the most the pool rule allows)
--sell-tokens T put T token units into the pool for ERG (the most the pool rule allows)
--sell-all      sell every unit of the pool's token the wallet holds
--keep N        with a sale, never take the pool below N nanoERG (default 500000; a box needs a minimum value)

usage: swap.py --pool-nft <id> (--buy-erg X | --sell-tokens T | --sell-all) [--keep 500000] [--fee 1100000]
               [--out unsigned.json]
"""
import argparse, importlib, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
bt = importlib.import_module("babel-take")
WALLET = Path.home() / ".config" / "skunkyard" / "mainnet-wallet.address"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool-nft", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--buy-erg", type=int)
    g.add_argument("--sell-tokens", type=int)
    g.add_argument("--sell-all", action="store_true")
    ap.add_argument("--keep", type=int, default=500_000)
    ap.add_argument("--fee", type=int, default=1_100_000)
    ap.add_argument("--out", default="swap-unsigned.json")
    a = ap.parse_args()

    addr = WALLET.read_text().strip()
    wtree = bt.p2pk_tree(addr)
    pool = [p for p in bt.get(f"/boxes/unspent/byTokenId/{a.pool_nft}?limit=5")["items"]
            if p["assets"] and p["assets"][0]["tokenId"] == a.pool_nft]
    if len(pool) != 1 or len(pool[0]["assets"]) != 3:
        sys.exit("expected one ERG pool box holding the NFT at token 0")
    pool = pool[0]
    x0, tok, y0 = pool["value"], pool["assets"][2]["tokenId"], pool["assets"][2]["amount"]
    f = int(pool["additionalRegisters"]["R4"]["renderedValue"])
    wboxes = bt.get(f"/boxes/unspent/byAddress/{addr}?limit=100")["items"]
    held = sum(t["amount"] for b in wboxes for t in b["assets"] if t["tokenId"] == tok)

    if a.buy_erg:
        dx = a.buy_erg
        dy = -((y0 * dx * f) // (x0 * 1000 + dx * f))          # tokens out (negative)
        assert y0 * dx * f >= -dy * (x0 * 1000 + dx * f)
    else:
        t = held if a.sell_all else a.sell_tokens
        if t <= 0 or t > held:
            sys.exit(f"the wallet holds {held} of the token; cannot sell {t}")
        out = (x0 * t * f) // (y0 * 1000 + t * f)
        out = min(out, x0 - a.keep)
        dx, dy = -out, t
        assert x0 * dy * f >= out * (y0 * 1000 + dy * f)
    if dx <= -x0 or y0 + dy <= 0:
        sys.exit("the swap would empty the pool")

    # Fund from wallet boxes: largest first until ERG need and token need are met
    need_erg = max(dx, 0) + a.fee + 1_000_000                  # keep a minimum change box
    need_tok = max(dy, 0)
    pick, have_erg, have_tok = [], 0, 0
    for b in sorted(wboxes, key=lambda b: (-sum(t["amount"] for t in b["assets"] if t["tokenId"] == tok), -b["value"])):
        if have_erg >= need_erg and have_tok >= need_tok:
            break
        pick.append(b)
        have_erg += b["value"]
        have_tok += sum(t["amount"] for t in b["assets"] if t["tokenId"] == tok)
    if have_erg < need_erg or have_tok < need_tok:
        sys.exit("the wallet cannot fund this swap")

    height = bt.get("/networkState")["height"]
    change_tokens = {}
    for b in pick:
        for t in b["assets"]:
            change_tokens[t["tokenId"]] = change_tokens.get(t["tokenId"], 0) + t["amount"]
    change_tokens[tok] = change_tokens.get(tok, 0) - dy
    tx = {
        "inputs": [{"boxId": pool["boxId"], "spendingProof": {"proofBytes": "", "extension": {}}}] +
                  [{"boxId": b["boxId"], "spendingProof": {"proofBytes": "", "extension": {}}} for b in pick],
        "dataInputs": [],
        "outputs": [
            {"value": x0 + dx, "ergoTree": pool["ergoTree"], "creationHeight": height,
             "assets": [pool["assets"][0], pool["assets"][1], {"tokenId": tok, "amount": y0 + dy}],
             "additionalRegisters": {k: v["serializedValue"] for k, v in pool["additionalRegisters"].items()}},
            {"value": have_erg - dx - a.fee, "ergoTree": wtree, "creationHeight": height,
             "assets": [{"tokenId": k, "amount": v} for k, v in change_tokens.items() if v > 0],
             "additionalRegisters": {}},
            {"value": a.fee, "ergoTree": bt.FEE_TREE, "creationHeight": height, "assets": [],
             "additionalRegisters": {}},
        ],
    }
    for o in tx["outputs"]:
        o["assets"] = [{"tokenId": t["tokenId"], "amount": t["amount"]} for t in o["assets"]]
    json.dump(tx, open(a.out, "w"), indent=1)
    print(json.dumps({"pool": pool["boxId"], "token": tok, "fee": f, "x0": x0, "y0": y0, "dErgToPool": dx,
                      "dTokensToPool": dy, "walletNetErg": -dx - a.fee, "out": a.out}, indent=1))


if __name__ == "__main__":
    main()
