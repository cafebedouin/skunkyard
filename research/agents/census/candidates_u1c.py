#!/usr/bin/env python3
"""U1c line p: unsigned candidate transactions for the keyless takes worth more than their fee.

Builds node-JSON transactions (empty proofs, the context extension each input needs) against the boxes as they
stand at the explorer's current tip, and writes them to census/u1c/candidates/<template>-<n>.json with a sidecar
<...>.meta.json (height, amounts, the rule each amount satisfies). **Builds and submits nothing else**: no node
check, no signature, no broadcast. Every candidate is to be checked by a node (`/transactions/check`) and taken, if
at all, outside this session; until then each is [UNVERIFIED by a node].

Kinds:
  free           OUTPUTS.size == 1 boxes (template e9d13195): all of them into one output; no fee box, so a
                 miner's own block only [inferred]
  machina-grid   Machina grid bids (a68900b6) above their N2T pool: pool at input 0, every grid box of that
                 token after it, one pool swap for all the units; each grid box's successor at the output its
                 context variable 1 names, R6 = its id, context variable 0 = false (the bid side)
  swapsell-v1    ErgoDEX N2T SwapSell v1 orders (36d1944f) executable now: pool at input 0, order at input 1

usage: candidates_u1c.py [--to <mainnet P2PK address>] [--fee 1100000]
"""
import argparse, collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import explorer as X  # noqa: E402
import paths as PA  # noqa: E402
import trees as T  # noqa: E402

OUT = os.path.join(HERE, "u1c", "candidates")
WALLET = "9gnBiuBAy4GgGEk1MZQ5f7aWWuQnyGHNVVF4bvhHKWvecWTNcfc"   # skunkyard mainnet test wallet (README round 1)
FREE = "e9d13195d73d90fde24ade268844724417323260456736559cf89a18a3eb696a"
GRID = "a68900b67ff5d74f74e7907aca83680adfc8ba01c1925430339d9e4c3f5dd0a3"
SWAPSELL_V1 = "36d1944fe6d743312e93541a1daf5592519772310ce924b2ec10e3f9b450e13a"
KEEP = 1_000_000                  # nanoERG left in a recreated offer box (U1b's convention)


def live(th):
    base = f"/boxes/unspent/byErgoTreeTemplateHash/{th}?"
    total = X.get(f"{base}offset=0&limit=1", cache=False)["total"]
    out = []
    for off in range(0, total, 100):
        out += X.get(f"{base}offset={off}&limit=100", cache=False)["items"]
    return out


def pool_by_nft(nft):
    items = X.get(f"/boxes/unspent/byTokenId/{nft}?offset=0&limit=5", cache=False)["items"]
    items = [p for p in items if p["assets"] and p["assets"][0]["tokenId"] == nft
             and T.template_hash(p["ergoTree"]) == T.N2T_POOL_TEMPLATE_HASH]
    if len(items) != 1:
        raise SystemExit(f"pool {nft}: {len(items)} live boxes")
    return items[0]


def p2pk_tree(addr):
    t = T.address_tree(addr)
    assert t and t.startswith("0008cd"), "a mainnet P2PK address"
    return t


def regs(box):
    return {k: v["serializedValue"] for k, v in (box["additionalRegisters"] or {}).items()}


def out_box(value, tree, h, assets=(), registers=None):
    return {"value": value, "ergoTree": tree, "creationHeight": h,
            "assets": [{"tokenId": t, "amount": n} for t, n in assets], "additionalRegisters": registers or {}}


def inp(box, ext=None):
    return {"boxId": box["boxId"], "spendingProof": {"proofBytes": "", "extension": ext or {}}}


def write(name, tx, meta):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name + ".json")
    json.dump(tx, open(p, "w"), indent=1)
    json.dump(meta, open(p[:-5] + ".meta.json", "w"), indent=1)
    print(f"wrote {p}: {json.dumps({k: v for k, v in meta.items() if k in ('kind', 'payoutNanoErg', 'inputs')})}")


def pool_xyf(pool):
    return pool["value"], pool["assets"][2]["amount"], int(pool["additionalRegisters"]["R4"]["renderedValue"])


def pool_cost(x0, y0, fee, t):
    """Least ERG dX into an ErgoDEX v1 N2T pool for t tokens out (Pool.sc:56-60, dX > 0):
    y0 * dX * fee >= t * (x0 * 1000 + dX * fee)."""
    return -(-(t * x0 * 1000) // (fee * (y0 - t)))


def build_free(h, to):
    bx = live(FREE)
    ok = [b for b in bx if PA.parse_constants(b["ergoTreeConstants"]).get(0) == "1" and not b["assets"]]
    if not ok:
        return
    total = sum(b["value"] for b in ok)
    tx = {"inputs": [inp(b) for b in ok], "dataInputs": [], "outputs": [out_box(total, p2pk_tree(to), h)]}
    write(f"{FREE[:12]}-1", tx, {"kind": "free", "height": h, "inputs": len(ok), "boxNanoErg": total,
                                 "payoutNanoErg": total, "minerFeeNanoErg": 0,
                                 "rule": "each input: OUTPUTS.size == 1 (constant 0 = 1 on every box)",
                                 "inclusion": "no fee output: a miner's own block only [inferred]",
                                 "repeating": "one-time (no box of this template was created in the window "
                                              "except as a chained-transaction link)"})


def build_grid(h, to, fee):
    """Bid side of each grid box (decompiled script): with var 0 = false, the successor OUTPUTS(var 1) keeps the
    script, R4, R5 and the token id, R6 = SELF.id, gains l10 > 0 units, and l10 * R5(1) >= SELF.value - its
    value."""
    bx = live(GRID)
    pools_all = collections.defaultdict(list)
    for p in live(T.N2T_POOL_TEMPLATE_HASH):
        if len(p["assets"]) == 3:
            pools_all[p["assets"][2]["tokenId"]].append(p)
    by_tok = collections.defaultdict(list)
    for b in bx:
        tok = T.constant_coll_bytes(b["ergoTree"], 0)
        r5 = (b["additionalRegisters"].get("R5") or {}).get("renderedValue")
        if not r5 or "R6" not in b["additionalRegisters"] or "R4" not in b["additionalRegisters"]:
            continue
        bid = json.loads(r5)[1]
        by_tok[tok].append((b, bid))
    n = 0
    for tok, offers in by_tok.items():
        pools = pools_all.get(tok, [])
        if not pools:
            continue
        pool = max(pools, key=lambda p: p["value"])
        x0, y0, f = pool_xyf(pool)
        # each grid box takes one unit (its whole ERG pays for one unit at these bids); keep the boxes whose
        # one-unit fill pays more than the pool's marginal cost
        offers.sort(key=lambda o: -o[1])
        take, units = [], 0
        for b, bid in offers:
            y = min(bid, b["value"] - KEEP)
            c_before = pool_cost(x0, y0, f, units) if units else 0
            c_after = pool_cost(x0, y0, f, units + 1)
            if y - (c_after - c_before) > 0:
                take.append((b, bid, y))
                units += 1
        if not take:
            continue
        dx = pool_cost(x0, y0, f, units)
        assert y0 * dx * f >= units * (x0 * 1000 + dx * f)
        ins = [inp(pool)]
        outs = [out_box(x0 + dx, pool["ergoTree"], h,
                        [(s["tokenId"], s["amount"] - (units if i == 2 else 0)) for i, s in enumerate(pool["assets"])],
                        regs(pool))]
        got = 0
        for k, (b, bid, y) in enumerate(take):
            held = b["assets"][0]["amount"] if b["assets"] else 0
            r = regs(b)
            r["R6"] = "0e20" + b["boxId"]
            succ_index = 1 + k
            ins.append(inp(b, {"0": "0100", "1": "04" + _zz_vlq(succ_index)}))
            outs.append(out_box(b["value"] - y, b["ergoTree"], h, [(tok, held + 1)], r))
            assert 1 * bid >= y > 0
            got += y
        payout = got - dx - fee
        if payout <= 0:
            continue
        outs.append(out_box(payout, p2pk_tree(to), h))
        outs.append(out_box(fee, T.FEE_TREE, h))
        n += 1
        write(f"{GRID[:12]}-{n}", {"inputs": ins, "dataInputs": [], "outputs": outs},
              {"kind": "machina-grid", "height": h, "token": tok, "pool": pool["boxId"], "poolX": x0, "poolY": y0,
               "poolFeeNum": f, "unitsFromPool": units, "dXNanoErg": dx, "gridBoxes": [b["boxId"] for b, _, _ in take],
               "bids": [bid for _, bid, _ in take], "ergFromGrids": got, "payoutNanoErg": payout,
               "minerFeeNanoErg": fee, "inputs": len(ins),
               "rules": ["pool: y0*dX*fee >= T*(x0*1000 + dX*fee) (ErgoDEX v1 n2t Pool.sc:56-60)",
                         "grid (bid, var 0 = false): units added > 0 and units * R5[1] >= ERG taken; successor at "
                         "OUTPUTS(var 1) with R4, R5 copied, R6 = SELF.id, same script and token"],
               "repeating": "one-time: the bids are stale (R5 bid far above every pool); each fill leaves the "
                            "box unchanged in price, so a box refills only if its owner adds ERG"})


def _zz_vlq(n):
    """Int as a sigma constant body: zig-zag, then VLQ."""
    z = (n << 1) ^ (n >> 31)
    out = bytearray()
    while True:
        b = z & 0x7F
        z >>= 7
        out.append(b | (0x80 if z else 0))
        if not z:
            return out.hex()


def build_swapsell(h, to, fee):
    """ErgoDEX N2T SwapSell v1 (decompiled script, constants of each box): INPUTS(0) the pool (3 tokens, NFT =
    const 8); OUTPUTS(1) pays the redeemer (const 0) q >= MinQuote (const 10) of the quote token (const 9) and
    value >= SELF.value - q*num/den (11, 12) - Base (2); the pool gives at least the fair output:
    poolY * Base * FeeNum(14) <= (q + 1) * (poolX * 1000 + Base * FeeNum) (constants 15..18); fee outputs <= 2,000,000
    (const 22)."""
    n = 0
    for b in live(SWAPSELL_V1):
        c = PA.parse_constants(b["ergoTreeConstants"])
        try:
            nft, quote = PA.const_hex(c[8]), PA.const_hex(c[9])
            min_q, num, den, feenum, base = int(c[10]), int(c[11]), int(c[12]), int(c[14]), int(c[2])
        except (KeyError, ValueError, TypeError):
            continue
        if int(c[17]) != base or int(c[18]) != feenum:
            continue
        txfee = min(fee, int(c[22]))     # the order caps all miner-fee outputs together (constant 22)
        try:
            pool = pool_by_nft(nft)
        except SystemExit:
            continue
        x0, y0, f = pool_xyf(pool)
        if pool["assets"][2]["tokenId"] != quote or f != feenum:
            continue
        q = (y0 * base * f) // (x0 * 1000 + base * f)
        if q < min_q:
            continue
        assert y0 * base * f <= (q + 1) * (x0 * 1000 + base * f)
        ex = min(q * num // den, b["value"] - base)
        payout = ex - txfee
        if payout <= 0:
            continue
        redeemer = c[0]
        if not redeemer.startswith("SigmaProp(ProveDlog"):
            continue
        # the redeemer's tree is the P2PK of the constant's key: read it from the box's tree (constant 0 bytes)
        rtree = _p2pk_from_const0(b["ergoTree"])
        outs = [out_box(x0 + base, pool["ergoTree"], h,
                        [(s["tokenId"], s["amount"] - (q if i == 2 else 0)) for i, s in enumerate(pool["assets"])],
                        regs(pool)),
                out_box(b["value"] - base - ex, rtree, h, [(quote, q)]),
                out_box(payout, p2pk_tree(to), h),
                out_box(txfee, T.FEE_TREE, h)]
        n += 1
        write(f"{SWAPSELL_V1[:12]}-{n}", {"inputs": [inp(pool), inp(b)], "dataInputs": [], "outputs": outs},
              {"kind": "swapsell-v1", "height": h, "order": b["boxId"], "pool": pool["boxId"], "baseNanoErg": base,
               "quote": q, "minQuote": min_q, "executorNanoErg": ex, "payoutNanoErg": payout, "minerFeeNanoErg": txfee,
               "minerFeeCap": int(c[22]), "inputs": 2, "repeating": "per order: executor fees recur as users place orders (U1 e)"})


def _p2pk_from_const0(tree_hex):
    """Constant 0 of a SwapSell v1 tree is the redeemer's SigmaProp (ProveDlog): 08 cd <33-byte key>."""
    b = bytes.fromhex(tree_hex)
    i = 1
    if b[0] & 0x08:
        _, i = T._vlq(b, i)
    _, i = T._vlq(b, i)
    assert b[i] == 0x08 and b[i + 1] == 0xcd, "constant 0 is not a ProveDlog"
    return "0008cd" + b[i + 2:i + 35].hex()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", default=WALLET)
    ap.add_argument("--fee", type=int, default=1_100_000)
    a = ap.parse_args()
    h = X.tip()
    print(f"tip {h}, endpoint {X.EXPLORER}, payout {a.to}")
    build_free(h, a.to)
    build_grid(h, a.to, a.fee)
    build_swapsell(h, a.to, a.fee)


if __name__ == "__main__":
    main()
