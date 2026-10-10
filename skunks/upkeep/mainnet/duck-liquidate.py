#!/usr/bin/env python3
"""Duckpools liquidations on the SigUSD-1e lending pool (ERG collateral priced by the ErgoDEX ERG/SigUSD pool).

The loan contract (template db697243, read from the deployed tree; arithmetic from the official liquidator,
duckpools/off-chain-bot token_pools/t_liquidation_susd.py and helpers/platform_functions.py):

    debt     = 1 + borrowUnits * I / 1e8      I: the interest lists folded in the script's order (fold() below)
    c        = loan.value - 5,000,000
    value    = Y*c*fee / ((X + X*2/100)*1000 + c*fee)     X, Y, fee: the R7 ErgoDEX pool
    liquidate when HEIGHT > R9._1 (expired), or R9._2 has been marked, HEIGHT >= R9._2 and value <= debt*R6._1/1000
    borrower = (value - debt) * (1000 - R6._2) / 1000, paid at OUTPUTS(2) to R4's tree when >= 1
    repaid   = value - borrower (>= debt + surplus*penalty/1000), at OUTPUTS(1) to the repayment script, with the
               loan's borrow token

scan       every live loan: debt, value, health, expiry, mark, and whether it can be liquidated now
liquidate  build the liquidation for one loan (no wallet input: nothing to sign); --check with the node, --submit
           inputs:  0 the ErgoDEX pool, 1 the loan;  data inputs: base child, parent, head child
           outputs: 0 pool successor, 1 repayment, 2 borrower (if any), then the take to the wallet, the miner fee
           The take: sell only the least ERG that yields the tokens owed; of the collateral that frees, half goes to
           the wallet and half stays in the pool (the official bot leaves part of its gain to the pool too).
mark       build the mark for an under-threshold loan: a wallet box as the spacer at INPUTS(0) (the script needs a
           box there holding fewer than three tokens), the loan recreated with R9._2 = height + 4; its fee comes
           out of the collateral, as the contract allows (1,000,000). Unsigned: sign with mainnet-sign.mjs.

usage: duck-liquidate.py scan
       duck-liquidate.py liquidate --loan <boxId> [--check] [--submit] [--out f.json]
       duck-liquidate.py mark --loan <boxId> [--out f.json]
"""
import argparse, hashlib, importlib, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
bt = importlib.import_module("babel-take")
NODE = "http://128.253.41.100:9053"
WALLET = Path.home() / ".config" / "skunkyard" / "mainnet-wallet.address"

# SigUSD-1e, from duckpools/off-chain-bot consts.py; every id checked against the live boxes' contract constants
COLLATERAL_TEMPLATE = "db697243"           # explorer (SHA-256) template prefix of the loan contract
CHILD_NFT = "35d6f883bc9b09cec95de38bc3b7c5d01d519b88ad3512bba6643eb5c1090780"    # loan constant 13
PARENT_NFT = "d45bc0077acf66b60e59d24d181e29570955c830399ede244d59d5ff726ad18e"   # loan constant 16
SIGUSD = "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04"       # loan constant 18
REPAYMENT_ADDR = ("r5zW3yf5B6ZghtHxnav9bFnQrebMKQKZQnvbkMwnTuoPp8wyvH9zoykUxkLquJkBUUsZie2Gc3Fs2rUQ2vV9ghvCfYx78bN"
                  "2f2qcb9pFZoysqfuRfQs8w9rVMyDoWQ7qSWajedPzHbXpQaLTWNdJuTsuYN824KaFrrdqauhk7GQoegTmhq9tXDjTnMXXnRUxz"
                  "xdcBjZfJM36XYu2kLf8ZsK3q5A7Mz9N6oa7Gg21qYpSmS4EJcagqDk8kinGmu9i6RYeXDnT6cxyd2w2eBmGy5Nd3JKzvPcy2DV"
                  "Rk9Th1yXhgztKu5dqkN7MW9oxA94eUgR3P2drbn4arGQiYc7")
REPAYMENT_HASH = "1aae6fb5867d8b46a6b2fede86fd4fb58c9cb630841e23db0ba1c3d2a145c758"  # loan constant 34
UNMARKED = 100_000_000
RESERVE = 5_000_000                        # loan constant 40: c = value - 5,000,000
REPAY_BOX = 2_000_000                      # constants 35 + 36
BORROWER_BOX = 500_000
FEE = 1_100_000
MARK_FEE = 1_000_000                       # constant 32: the loan may shrink by this much when marked


def tree_of(address):
    n = 0
    for ch in address:
        n = n * 58 + bt.B58.index(ch)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    body, check = raw[:-4], raw[-4:]
    if hashlib.blake2b(body, digest_size=32).digest()[:4] != check:
        sys.exit("bad address checksum")
    return body[1:].hex()


def rv(box, r):
    v = box["additionalRegisters"][r]["renderedValue"]
    return v if box["additionalRegisters"][r]["sigmaType"] == "Coll[SByte]" else json.loads(v)


def unspent_by_address(addr):
    out, off = [], 0
    while True:
        page = bt.get(f"/boxes/unspent/byAddress/{addr}?limit=100&offset={off}")
        out += page["items"]
        off += 100
        if off >= page["total"]:
            return out


def interest_boxes(loans):
    """The parent box and every child box, found at the addresses the live loans' data inputs use."""
    tx = bt.get(f"/transactions/{loans[0]['transactionId']}")
    addrs = {d["address"] for d in tx["dataInputs"]}
    boxes = [b for a in addrs for b in unspent_by_address(a)]
    parent = [b for b in boxes if b["assets"] and b["assets"][0]["tokenId"] == PARENT_NFT]
    children = [b for b in boxes if b["assets"] and b["assets"][0]["tokenId"] == CHILD_NFT]
    if len(parent) != 1:
        sys.exit(f"expected one parent interest box, found {len(parent)}")
    return parent[0], children


def child_at(children, i):
    c = [b for b in children if int(rv(b, "R6")) == i]
    if len(c) != 1:
        sys.exit(f"expected one child interest box with R6 = {i}, found {len(c)}")
    return c[0]


def fold(xs, acc):
    for x in xs:
        acc = acc * x // 100_000_000
    return acc


def debt(loan, parent, children):
    """The loan script's debt (its bi24), in the script's order of folds."""
    child_idx, pos = rv(loan, "R5")
    plist = rv(parent, "R4")
    i14 = len(plist)
    base = child_at(children, child_idx)
    l19 = fold(rv(base, "R4")[pos:], 100_000_000)
    if i14 == child_idx:
        I = l19
    else:
        head = child_at(children, i14)
        l23 = fold(rv(head, "R4"), l19)
        I = l23 if i14 == child_idx + 1 else fold(plist[child_idx + 1:i14], l23)
    return 1 + loan["assets"][0]["amount"] * I // 100_000_000, base


def pool_of(loan):
    nft = rv(loan, "R7")
    p = [b for b in bt.get(f"/boxes/unspent/byTokenId/{nft}?limit=5")["items"]
         if b["assets"] and b["assets"][0]["tokenId"] == nft]
    if len(p) != 1 or len(p[0]["assets"]) != 3:
        sys.exit("expected one ErgoDEX pool box holding the loan's R7 NFT")
    return p[0]


def value_of(loan_value, pool):
    X, Y = pool["value"], pool["assets"][2]["amount"]
    fee = int(pool["additionalRegisters"]["R4"]["renderedValue"])
    c = loan_value - RESERVE
    return Y * c * fee // ((X + X * 2 // 100) * 1000 + c * fee), (X, Y, fee, c)


def tip():
    return json.loads(bt.http(NODE + "/info")[1])["fullHeight"]


def state(loan, pool, parent, children, height):
    d, base = debt(loan, parent, children)
    v, _ = value_of(loan["value"], pool)
    thr, pen = rv(loan, "R6")
    expiry, mark = rv(loan, "R9")
    under = v <= d * thr // 1000
    can = height + 1 > expiry or (mark != UNMARKED and height + 1 >= mark and under)
    return {"box": loan["boxId"], "collateralErg": loan["value"] / 1e9, "borrowUnits": loan["assets"][0]["amount"],
            "debt": d, "value": v, "health": round(v * 1000 / (d * thr), 4), "threshold": thr, "penalty": pen,
            "expiry": expiry, "blocksToExpiry": expiry - height, "mark": None if mark == UNMARKED else mark,
            "underThreshold": under, "liquidatableNextBlock": can, "base": base}


def loans_now():
    # The loans sit at the SigUSD-1e collateral address; find them through a known live loan's address.
    seed = bt.get("/boxes/9b06f503d99d31f928abe227c458a1cfa585b43fde33eee37fc9ae3716ac0936")
    addr = seed["address"]
    return [b for b in unspent_by_address(addr) if "R9" in b["additionalRegisters"] and b["assets"]]


def scan(a):
    h = tip()
    loans = loans_now()
    parent, children = interest_boxes(loans)
    pools = {}
    print(f"height {h}; {len(loans)} loans; parent interest box from {parent['settlementHeight']}")
    for ln in sorted(loans, key=lambda b: rv(b, "R9")[0]):
        nft = rv(ln, "R7")
        pools.setdefault(nft, pool_of(ln))
        s = state(ln, pools[nft], parent, children, h)
        s.pop("base")
        print(json.dumps(s))


def inp(box_id):
    return {"boxId": box_id, "spendingProof": {"proofBytes": "", "extension": {}}}


def out_box(value, tree, h, assets=(), regs=None):
    return {"value": value, "ergoTree": tree, "creationHeight": h,
            "assets": [{"tokenId": t, "amount": n} for t, n in assets], "additionalRegisters": regs or {}}


def liquidate(a):
    h = tip()
    loan = bt.get(f"/boxes/{a.loan}")
    if loan.get("spentTransactionId"):
        sys.exit("the loan box is spent")
    parent, children = interest_boxes([loan])
    pool = pool_of(loan)
    s = state(loan, pool, parent, children, h)
    if not s["liquidatableNextBlock"] and not a.force:
        sys.exit(f"not liquidatable at {h + 1}: {json.dumps({k: v for k, v in s.items() if k != 'base'})}")
    d, v, pen = s["debt"], s["value"], s["penalty"]
    borrower = (v - d) * (1000 - pen) // 1000 if v > d else 0
    if borrower < 1:
        borrower = 0
    owed = v + 1                                          # tokens the pool must give: repayment + borrower share
    repaid = owed - borrower
    assert borrower == 0 or repaid >= d + (v - d) * pen // 1000
    X, Y, fee, c = value_of(loan["value"], pool)[1]
    # the least ERG that buys `owed` tokens: Y*dX*fee >= owed*(X*1000 + dX*fee)
    sold = -(-(owed * X * 1000) // (fee * (Y - owed)))
    assert Y * sold * fee >= owed * (X * 1000 + sold * fee) and sold <= c
    freed = c - sold
    donated = freed - freed // 2
    take = loan["value"] - sold - donated - REPAY_BOX - (BORROWER_BOX if borrower else 0) - FEE
    wallet = bt.p2pk_tree(WALLET.read_text().strip())
    outs = [out_box(pool["value"] + sold + donated, pool["ergoTree"], h,
                    [(t["tokenId"], t["amount"]) for t in pool["assets"][:2]] + [(SIGUSD, Y - owed)],
                    bt.regs(pool)),
            out_box(REPAY_BOX, tree_of(REPAYMENT_ADDR), h,
                    [(loan["assets"][0]["tokenId"], loan["assets"][0]["amount"]), (SIGUSD, repaid)])]
    if borrower:
        outs.append(out_box(BORROWER_BOX, rv(loan, "R4"), h, [(SIGUSD, borrower)]))
    outs += [out_box(take, wallet, h), out_box(FEE, bt.FEE_TREE, h)]
    assert hashlib.blake2b(bytes.fromhex(outs[1]["ergoTree"]), digest_size=32).hexdigest() == REPAYMENT_HASH
    head = child_at(children, len(rv(parent, "R4")))
    tx = {"inputs": [inp(pool["boxId"]), inp(loan["boxId"])],
          "dataInputs": [{"boxId": s["base"]["boxId"]}, {"boxId": parent["boxId"]}, {"boxId": head["boxId"]}],
          "outputs": outs}
    assert sum(o["value"] for o in outs) == pool["value"] + loan["value"]
    summary = {"height": h, "loan": loan["boxId"], "debt": d, "value": v, "borrowerShare": borrower,
               "repaid": repaid, "soldNanoErg": sold, "leftInPoolNanoErg": donated, "takeNanoErg": take,
               "expired": h + 1 > s["expiry"]}
    print(json.dumps(summary, indent=1))
    out = a.out or f"tx/duck/liquidate-{loan['boxId'][:12]}-{h}.json"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(tx, indent=1))
    print("wrote", out)
    if a.check or a.submit:
        code, text = bt.http(NODE + "/transactions/check", tx)
        print("check:", code, text[:400])
        if a.submit and code == 200:
            code, text = bt.http(NODE + "/transactions", tx)
            print("submit:", code, text[:400])


def encode_long_pair(x, y):
    def vlq(n):
        n = (n << 1) ^ (n >> 63)                 # zigzag
        out = bytearray()
        while True:
            b = n & 0x7F
            n >>= 7
            out.append(b | (0x80 if n else 0))
            if not n:
                return bytes(out)
    return "59" + (vlq(x) + vlq(y)).hex()


def mark(a):
    h = tip()
    loan = bt.get(f"/boxes/{a.loan}")
    parent, children = interest_boxes([loan])
    pool = pool_of(loan)
    s = state(loan, pool, parent, children, h)
    if not s["underThreshold"] or s["mark"] is not None:
        sys.exit(f"nothing to mark: {json.dumps({k: v for k, v in s.items() if k != 'base'})}")
    expiry, _ = rv(loan, "R9")
    assert encode_long_pair(expiry, UNMARKED) == loan["additionalRegisters"]["R9"]["serializedValue"]
    addr = WALLET.read_text().strip()
    spacer = [b for b in bt.get(f"/boxes/unspent/byAddress/{addr}?limit=50")["items"] if len(b["assets"]) < 3][0]
    regs = bt.regs(loan)
    regs["R9"] = encode_long_pair(expiry, h + 4)
    head = child_at(children, len(rv(parent, "R4")))
    outs = [out_box(loan["value"] - MARK_FEE, loan["ergoTree"], h,
                    [(t["tokenId"], t["amount"]) for t in loan["assets"]], regs),
            out_box(spacer["value"], spacer["ergoTree"], h, [(t["tokenId"], t["amount"]) for t in spacer["assets"]]),
            out_box(MARK_FEE, bt.FEE_TREE, h)]
    tx = {"inputs": [inp(spacer["boxId"]), inp(loan["boxId"])],
          "dataInputs": [{"boxId": s["base"]["boxId"]}, {"boxId": parent["boxId"]}, {"boxId": head["boxId"]},
                         {"boxId": pool["boxId"]}],
          "outputs": outs}
    out = a.out or f"tx/duck/mark-{loan['boxId'][:12]}-{h}.json"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(tx, indent=1))
    print("wrote", out, "(unsigned: sign with mainnet-sign.mjs)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scan")
    p = sub.add_parser("liquidate")
    p.add_argument("--loan", required=True)
    p.add_argument("--check", action="store_true")
    p.add_argument("--submit", action="store_true")
    p.add_argument("--force", action="store_true", help="build even if not liquidatable (for a node check)")
    p.add_argument("--out")
    p = sub.add_parser("mark")
    p.add_argument("--loan", required=True)
    p.add_argument("--out")
    a = ap.parse_args()
    {"scan": scan, "liquidate": liquidate, "mark": mark}[a.cmd](a)


if __name__ == "__main__":
    main()
