#!/usr/bin/env python3
"""U2: Lithos blocks on mainnet, read from the explorer by the collateral token.

A Lithos block's genesis transaction spends a collateral box (one unit of the collateral token, five
registers) and sits at index 1 of its block with seven outputs. The token's other spends retire
proof-of-spend boxes (one register, four outputs) and are not blocks. Prints each block and the share
over the span from the first Lithos block to the chain tip.

usage: lithos-blocks-mainnet.py [--token <id>] [--json out.json]
"""
import argparse, json, os, sys, time, urllib.request

EXPLORER = os.environ.get("ERGO_EXPLORER", "https://api.ergoplatform.com/api/v1")
COLLAT = "a8a790e784e93ac0e68649181ae3d251e84fb5c741624100e7e945ae1e82dc98"

def get(path):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(EXPLORER + path, timeout=40) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default=COLLAT)
    ap.add_argument("--json")
    a = ap.parse_args()
    items, off = [], 0
    while True:
        d = get(f"/boxes/byTokenId/{a.token}?limit=100&offset={off}")
        items += d.get("items", [])
        off += 100
        if off >= d.get("total", 0):
            break
    one = [b for b in items if any(x["tokenId"] == a.token and x["amount"] == 1 for x in b.get("assets", []))]
    spent = [b for b in one if b.get("spentTransactionId")]
    blocks = []
    for b in spent:
        tx = get(f"/transactions/{b['spentTransactionId']}")
        if tx.get("index") == 1 and len(tx.get("outputs", [])) == 7 and len(b.get("additionalRegisters", {})) == 5:
            blocks.append({"height": tx["inclusionHeight"], "genesisTx": tx["id"], "collateralBox": b["boxId"],
                           "blockId": tx.get("blockId")})
    blocks.sort(key=lambda x: x["height"])
    tip = get("/networkState")["height"]
    first = blocks[0]["height"] if blocks else tip
    span = tip - first + 1
    out = {"readAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tip": tip, "tokenBoxes": len(items),
           "collateralOrProofBoxes": len(one), "spent": len(spent), "lithosBlocks": len(blocks),
           "firstLithosBlock": first, "spanBlocks": span, "share": len(blocks) / span if span else 0.0,
           "blocks": blocks}
    for x in blocks:
        print(f"{x['height']}  genesis {x['genesisTx'][:8]}  collateral {x['collateralBox'][:8]}")
    print(f"Lithos blocks: {len(blocks)} of {span} since {first} (tip {tip}): share {out['share']:.2%}, "
          f"expected wait {span / max(1, len(blocks)):.0f} blocks", file=sys.stderr)
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)

if __name__ == "__main__":
    main()
