#!/usr/bin/env python3
"""SK-049 on mainnet: take a Babel box's gap against an ErgoDEX v1 ERG pool in one keyless transaction.

Reads the Babel box and the pool's current box fresh from the explorer, sizes the trade on integers against both
contracts' rules (rounding against us), builds the transaction (no signature: the pool and the Babel box's swap path
need none; the Babel input carries context var 0 = the index of its successor), asks a node to check it without
broadcasting, and submits only with --submit.

    inputs:  0 pool, 1 Babel box
    outputs: 0 pool successor (+dX ERG, -T token), 1 Babel successor (-Y ERG, +T token, R4 R5 copied, R6 = its id),
             2 payout (Y - dX - fee) to --to, 3 miner fee

usage: babel-take.py --babel <boxId> --pool-nft <tokenId> --to <mainnet P2PK address>
                     [--node URL] [--fee 1100000] [--keep 1000000] [--submit] [--out tx.json]
"""
import argparse, hashlib, json, sys, urllib.request

EXPLORER = "https://api.ergoplatform.com/api/v1"
FEE_TREE = ("1005040004000e36100204a00b08cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192"
            "a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac93b1a57304")
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def http(url, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def get(path):
    code, text = http(EXPLORER + path)
    if code != 200:
        sys.exit(f"explorer {path}: {code} {text[:300]}")
    return json.loads(text)


def p2pk_tree(address):
    n = 0
    for c in address:
        n = n * 58 + B58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    body, check = raw[:-4], raw[-4:]
    if hashlib.blake2b(body, digest_size=32).digest()[:4] != check:
        sys.exit("bad address checksum")
    if body[0] != 0x01 or len(body) != 34:
        sys.exit("not a mainnet P2PK address")
    return "0008cd" + body[1:].hex()


def regs(box):
    return {k: v["serializedValue"] for k, v in box["additionalRegisters"].items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--babel", required=True)
    ap.add_argument("--pool-nft", required=True)
    ap.add_argument("--to", required=True)
    ap.add_argument("--node", default="http://128.253.41.100:9053")
    ap.add_argument("--fee", type=int, default=1_100_000)
    ap.add_argument("--keep", type=int, default=1_000_000, help="nanoERG left in the Babel successor")
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--out", default="babel-take-tx.json")
    a = ap.parse_args()

    babel = get(f"/boxes/{a.babel}")
    if babel.get("spentTransactionId"):
        sys.exit(f"Babel box already spent by {babel['spentTransactionId']}")
    pools = get(f"/boxes/unspent/byTokenId/{a.pool_nft}?limit=5")["items"]
    pool = [p for p in pools if p["assets"] and p["assets"][0]["tokenId"] == a.pool_nft]
    if len(pool) != 1:
        sys.exit(f"expected one pool box holding the NFT at token 0, found {len(pool)}")
    pool = pool[0]
    height = get("/networkState")["height"]

    token = babel["assets"][0]["tokenId"]
    held = babel["assets"][0]["amount"]
    bid = int(babel["additionalRegisters"]["R5"]["renderedValue"])
    if pool["assets"][2]["tokenId"] != token:
        sys.exit("the pool's token Y is not the Babel box's token")
    x0, y0 = pool["value"], pool["assets"][2]["amount"]
    fee_num = int(pool["additionalRegisters"]["R4"]["renderedValue"])

    # Pool rule (Pool.sc, dX > 0): y0 * dX * fee >= T * (x0 * 1000 + dX * fee)  =>  dX >= T*x0*1000 / (fee*(y0-T))
    def cost(t):
        return -(-(t * x0 * 1000) // (fee_num * (y0 - t)))

    # Y is bounded by the Babel box's ERG; profit(T) = min(T*bid, cap) - cost(T) is concave, so a ternary search
    # over integers, then a scan of the neighbourhood, finds the best T
    cap = babel["value"] - a.keep
    hi = min(-(-cap // bid), y0 - 1)
    profit = lambda t: min(t * bid, cap) - cost(t)
    lo = 1
    while hi - lo > 4:
        m1, m2 = lo + (hi - lo) // 3, hi - (hi - lo) // 3
        if profit(m1) < profit(m2):
            lo = m1 + 1
        else:
            hi = m2 - 1
    t = max(range(max(1, lo - 4), hi + 5), key=lambda k: profit(k) if 0 < k < y0 else -1)
    y = min(t * bid, cap)
    dx = cost(t)
    assert y0 * dx * fee_num >= t * (x0 * 1000 + dx * fee_num), "pool rule"
    assert (dx - 1) <= 0 or y0 * (dx - 1) * fee_num < t * (x0 * 1000 + (dx - 1) * fee_num), "dX not minimal"
    assert t * bid >= y >= 0, "Babel rule"
    payout = y - dx - a.fee
    if payout <= 0:
        sys.exit(f"no profit: Y {y} dX {dx} fee {a.fee}")

    babel_out_regs = regs(babel)
    babel_out_regs["R6"] = "0e20" + babel["boxId"]
    tx = {
        "inputs": [
            {"boxId": pool["boxId"], "spendingProof": {"proofBytes": "", "extension": {}}},
            {"boxId": babel["boxId"], "spendingProof": {"proofBytes": "", "extension": {"0": "0402"}}},
        ],
        "dataInputs": [],
        "outputs": [
            {"value": x0 + dx, "ergoTree": pool["ergoTree"], "creationHeight": height,
             "assets": [{"tokenId": s["tokenId"], "amount": s["amount"] - (t if i == 2 else 0)}
                        for i, s in enumerate(pool["assets"])],
             "additionalRegisters": regs(pool)},
            {"value": babel["value"] - y, "ergoTree": babel["ergoTree"], "creationHeight": height,
             "assets": [{"tokenId": token, "amount": held + t}], "additionalRegisters": babel_out_regs},
            {"value": payout, "ergoTree": p2pk_tree(a.to), "creationHeight": height, "assets": [],
             "additionalRegisters": {}},
            {"value": a.fee, "ergoTree": FEE_TREE, "creationHeight": height, "assets": [],
             "additionalRegisters": {}},
        ],
    }
    json.dump(tx, open(a.out, "w"), indent=1)
    print(json.dumps({"height": height, "pool": pool["boxId"], "babel": babel["boxId"], "bid": bid,
                      "dX": dx, "T": t, "Y": y, "fee": a.fee, "payout": payout, "to": a.to}, indent=1))

    code, text = http(a.node + "/transactions/check", tx)
    print(f"node check {a.node}: {code} {text[:400]}")
    if code != 200:
        sys.exit(1)
    if a.submit:
        code, text = http(EXPLORER + "/mempool/transactions/submit", tx)
        print(f"submit: {code} {text[:400]}")
        if code != 200:
            sys.exit(1)


if __name__ == "__main__":
    main()
