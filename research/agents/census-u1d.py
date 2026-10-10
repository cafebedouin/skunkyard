#!/usr/bin/env python3
"""Census U1d (prompts/census-u1d.md): state history from box chains, backtests, DexyGold, Duckpools.

Subcommands, one per line of the prompt:
    q   SigmaUSD history: bank, ERG/USD oracle, SigRSV and SigUSD pools; NAV, RR, discount; the bot's pairs
    r   backtests over q's history
    s   DexyGold: ids from the deployed trees, state history, every keyless action and who ran it
    t   Duckpools: pools, live loans, health, liquidations
    u   the summary table

Explorer: the Cornell mirror (census/explorer.py). Raw responses are cached gzipped under census/raw/ and the
compacted chains under census/out/u1d/ (both git-ignored). Outputs: census/u1d/*.json.
Build and submit nothing: every number here is read or computed, nothing is traded.
"""
import argparse, bisect, gzip, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "census"))
os.environ.setdefault("CENSUS_GZIP", "1")
import amm as A  # noqa: E402
import chain as C  # noqa: E402
import explorer as X  # noqa: E402

OUTD = os.path.join(HERE, "census", "u1d")

SIGUSD = "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04"
SIGRSV = "003bd19d0187117f130b62e1bcab0939929ff5c7709f843c5c4dd158949285d0"
BANK_NFT = "7d672d1def471720ca5782fd6473e47e796d9ac0c138d9911346f118b2f6d9d9"
ORACLE_NFT = "011d3364de07e5a26f0c4eef0852cddb387039a921b7154ef3cab22c6eda887f"
RSV_POOL = "1d5afc59838920bb5ef2a8f9d63825a55b1d48e269d7cecee335d637c3ff5f3f"
USD_POOL = "9916d75132593c8b07fe18bd8d583bda1652eed7565cf41a4738ddd90fc992ec"
BOT = "9fffEXsaT9roF7tKt5GyJUUZfun3NpWrMQ5oMAGGXRYMFK88aJq"
ORACLE_FROM = 891_308          # the last 1,000,000 blocks before tip 1,891,308 (the oracle chain is 286,436 boxes)
TX_FEE = 1_100_000             # 0.0011 ERG per transaction (the SK-049 fee)


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def save(name, obj):
    os.makedirs(OUTD, exist_ok=True)
    with open(os.path.join(OUTD, name), "w") as f:
        json.dump(obj, f, indent=1 if not name.startswith("q-series") else None, separators=None)


def load(name):
    with open(os.path.join(OUTD, name)) as f:
        return json.load(f)


def tok(r, t):
    return next((a for i, (tid, a) in enumerate(r["assets"]) if tid == t), 0)


def r4int(r):
    v = r["regs"].get("R4")
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


class Step:
    """A step function over heights: value at the end of block h = the last point at or before h."""

    def __init__(self, pts):
        pts = sorted(pts, key=lambda p: p[0])
        self.h = [p[0] for p in pts]
        self.v = [p[1] for p in pts]

    def at(self, h):
        i = bisect.bisect_right(self.h, h) - 1
        return self.v[i] if i >= 0 else None

    def last_change(self, h):
        i = bisect.bisect_right(self.h, h) - 1
        return self.h[i] if i >= 0 else None


def chains():
    bank = C.fetch(BANK_NFT)
    rsv = C.fetch(RSV_POOL)
    usd = C.fetch(USD_POOL)
    orc = C.fetch(ORACLE_NFT, from_height=ORACLE_FROM)
    return bank, orc, rsv, usd


def bank_step(rows):
    pts = []
    for r in rows:
        if r["hasNft"] and r["tpl"] == "246e14059ac2":
            pts.append((r["h"], (r["value"], int(r["regs"]["R4"]), int(r["regs"]["R5"]), r["box"])))
    return Step(pts)


def oracle_step(rows):
    """Refreshes: the oracle pool box carries the rate in R4 (nanoERG per USD); keep only the changes."""
    pts, last = [], None
    for r in rows:
        if not r["hasNft"]:
            continue
        v = r4int(r)
        if v is None:
            continue
        if v != last:
            pts.append((r["h"], v))
            last = v
    return Step(pts)


def pool_step(rows):
    pts = []
    for r in rows:
        if r["hasNft"] and r["tpl"] == "2dcc7830afe8" and len(r["assets"]) >= 3:
            pts.append((r["h"], (r["value"], r["assets"][2][1], int(r["regs"]["R4"]), r["box"])))
    return Step(pts)


def quotes(R, sc, rc, r4):
    """Bank v0.4 at one state, in the contract's integer arithmetic (census/amm.py Bank)."""
    b = A.Bank(R, sc, rc, r4)
    rr = (R * 100 // (sc * b.rate)) if sc * b.rate else None
    out = {"rr": rr, "nav": b.rc_price(), "scPrice": b.sc_price(), "rate": b.rate}
    for coin in ("sc", "rc"):
        m, d = b.exchange(coin, 1), b.exchange(coin, -1)
        out[coin + "Mint"] = m          # nanoERG paid for one unit, fee included, or None if closed
        out[coin + "Redeem"] = None if d is None else -d
    return out


def runs(seq, pred):
    """seq: [(h_from, h_to_exclusive, row)]; contiguous runs where pred(row). Returns [(from, to, rows)]."""
    out, cur = [], None
    for a, b, r in seq:
        if pred(r):
            if cur and cur[1] == a:
                cur[1] = b
                cur[2].append(r)
            else:
                cur = [a, b, [r]]
                out.append(cur)
        else:
            cur = None
    return out


def pct(xs_w, qs):
    """Weighted percentiles: xs_w = [(x, w)]."""
    xs = sorted(xs_w)
    tot = sum(w for _, w in xs)
    out, acc, i = {}, 0, 0
    for q in qs:
        target = q / 100 * tot
        while i < len(xs) and acc + xs[i][1] < target:
            acc += xs[i][1]
            i += 1
        out[q] = xs[min(i, len(xs) - 1)][0]
    return out


def dur_stats(rs):
    ds = sorted(b - a for a, b, _ in rs)
    if not ds:
        return {"n": 0}
    return {"n": len(ds), "blocksTotal": sum(ds), "min": ds[0], "median": ds[len(ds) // 2], "max": ds[-1],
            "mean": round(sum(ds) / len(ds), 1)}


# ---------------------------------------------------------------------------------------------------- line q

def series(tip):
    bank_rows, orc_rows, rsv_rows, usd_rows = chains()
    checks = {}
    for name, rows in (("bank", bank_rows), ("oracle", orc_rows), ("sigrsvPool", rsv_rows), ("sigusdPool", usd_rows)):
        br, rep = C.check(rows)
        if name == "oracle":
            rep["fromHeight"] = ORACLE_FROM
        rep["breakList"] = br[:20]
        checks[name] = rep
    bank, orc, rsv, usd = bank_step(bank_rows), oracle_step(orc_rows), pool_step(rsv_rows), pool_step(usd_rows)
    lo = max(orc.h[0], bank.h[0], rsv.h[0], usd.h[0])
    evs = sorted({h for s in (bank, orc, rsv, usd) for h in s.h if lo <= h <= tip})
    rows = []
    for i, h in enumerate(evs):
        R, sc, rc, _ = bank.at(h)
        r4 = orc.at(h)
        q = quotes(R, sc, rc, r4)
        X1, Y1, f1, _ = rsv.at(h)
        X2, Y2, f2, _ = usd.at(h)
        rows.append({"h": h, "to": evs[i + 1] if i + 1 < len(evs) else tip + 1, "R": R, "sc": sc, "rc": rc, "r4": r4,
                     "rsvX": X1, "rsvY": Y1, "rsvFee": f1, "usdX": X2, "usdY": Y2, "usdFee": f2, **q})
    return rows, checks, (bank, orc, rsv, usd), lo


def line_q(a):
    tip = a.tip or X.tip()
    rows, checks, (bank, orc, rsv, usd), lo = series(tip)
    log("events", len(rows), "from", lo, "to", tip)
    seg = [(r["h"], r["to"], r) for r in rows]

    def disc(r):
        return r["rsvX"] / r["rsvY"] / r["nav"] - 1

    for r in rows:
        r["disc"] = disc(r)
        r["usdVsRedeem"] = (r["usdX"] / r["usdY"]) / r["scRedeem"] - 1 if r["scRedeem"] else None
        r["usdVsOracle"] = (r["usdX"] / r["usdY"]) / r["rate"] - 1
        r["open400"] = r["scMint"] is not None
    blocks = tip + 1 - lo
    dw = [(r["disc"], r["to"] - r["h"]) for r in rows]
    below = runs(seg, lambda r: r["disc"] < 0)
    eps = []
    for th in (0, -0.02, -0.05, -0.10):
        rs = runs(seg, lambda r, th=th: r["disc"] < th)
        eps.append({"below": th, "blocks": sum(b - x for x, b, _ in rs), "share": sum(b - x for x, b, _ in rs) / blocks,
                    "episodes": dur_stats(rs)})
    ep_rows = [{"from": x, "to": b, "blocks": b - x, "deepest": min(r["disc"] for r in rr),
                "deepestAt": min(rr, key=lambda r: r["disc"])["h"], "rrAtStart": rr[0]["rr"],
                "rrMax": max(r["rr"] for r in rr), "redeemOpened": any(r["rcRedeem"] is not None for r in rr)}
               for x, b, rr in below]
    w400 = runs(seg, lambda r: r["open400"])
    gaps = [w400[i + 1][0] - w400[i][1] for i in range(len(w400) - 1)]
    rcred = runs(seg, lambda r: r["rcRedeem"] is not None)
    rcmint = runs(seg, lambda r: r["rcMint"] is not None)
    uw = [(r["usdVsRedeem"], r["to"] - r["h"]) for r in rows if r["usdVsRedeem"] is not None]
    ow = [(r["usdVsOracle"], r["to"] - r["h"]) for r in rows]
    rrw = [(r["rr"], r["to"] - r["h"]) for r in rows if r["rr"] is not None]
    # yearly view (by 262,800 blocks, ~1 year at 2 min)
    years = []
    for y0 in range(lo, tip + 1, 262_800):
        y1 = min(y0 + 262_800, tip + 1)
        rr_ = [r for r in rows if r["to"] > y0 and r["h"] < y1]
        wsum = lambda pred: sum(min(r["to"], y1) - max(r["h"], y0) for r in rr_ if pred(r))  # noqa: E731
        years.append({"from": y0, "to": y1 - 1, "blocksBelowNav": wsum(lambda r: r["disc"] < 0),
                      "blocksBelow2pct": wsum(lambda r: r["disc"] < -0.02),
                      "blocksAbove2pct": wsum(lambda r: r["disc"] > 0.02),
                      "blocksRR400": wsum(lambda r: r["open400"]),
                      "ergUsdMin": round(1e9 / max(r["r4"] for r in rr_), 4),
                      "ergUsdMax": round(1e9 / min(r["r4"] for r in rr_), 4),
                      "rrMin": min(r["rr"] for r in rr_), "rrMax": max(r["rr"] for r in rr_)})

    def point(h):
        r = rows[bisect.bisect_right([x["h"] for x in rows], h) - 1]
        return {"h": h, "stateFrom": r["h"], "rr": r["rr"], "ergUsd": round(1e9 / r["r4"], 4), "nav": r["nav"],
                "rcMint": r["rcMint"], "rsvPoolPrice": round(r["rsvX"] / r["rsvY"], 1), "rsvDisc": round(r["disc"], 4),
                "usdPoolVsRedeem": round(r["usdVsRedeem"], 4) if r["usdVsRedeem"] is not None else None,
                "usdPoolVsOracle": round(r["usdVsOracle"], 4), "bank": bank.at(h)[3], "rsvPool": rsv.at(h)[3],
                "usdPool": usd.at(h)[3]}

    checkpoints = [point(h) for h in (1_888_825, 1_888_826, 1_891_100) if h <= tip]
    bot = bot_pairs(orc, rsv, usd, bank)
    out = {"explorer": X.EXPLORER, "tip": tip, "from": lo, "blocks": blocks, "events": len(rows),
           "chains": checks, "oracleRefreshesInWindow": sum(1 for h in orc.h if lo <= h <= tip),
           "rsvDiscount": {"percentiles": {k: round(v, 4) for k, v in pct(dw, (1, 5, 10, 25, 50, 75, 90, 95, 99)).items()},
                           "thresholds": eps, "episodesBelowNav": len(ep_rows),
                           "longest": sorted(ep_rows, key=lambda e: -e["blocks"])[:15],
                           "deepest": sorted(ep_rows, key=lambda e: e["deepest"])[:15]},
           "rr400": {"windows": dur_stats(w400), "gaps": {"n": len(gaps), "min": min(gaps, default=None),
                                                         "median": sorted(gaps)[len(gaps) // 2] if gaps else None,
                                                         "max": max(gaps, default=None)},
                     "list": [{"from": x, "to": b, "blocks": b - x} for x, b, _ in w400],
                     "rcRedeemOpen": dur_stats(rcred), "rcMintOpen": dur_stats(rcmint),
                     "rrPercentiles": pct(rrw, (1, 10, 50, 90, 99))},
           "usdPool": {"vsRedeem": {k: round(v, 4) for k, v in pct(uw, (1, 10, 50, 90, 99)).items()},
                       "vsOracle": {k: round(v, 4) for k, v in pct(ow, (1, 10, 50, 90, 99)).items()},
                       "blocksBelowRedeem": sum(w for x, w in uw if x < 0)},
           "years": years, "checkpoints": checkpoints, "bot": bot}
    save("q.json", out)
    # compacted series: one row per state change of each chain, in the window
    save("q-series-bank.json", {"cols": ["h", "R", "sc", "rc", "box"],
                                "rows": [[h, *v] for h, v in zip(bank.h, bank.v)]})
    save("q-series-oracle.json", {"cols": ["h", "r4_nanoErgPerUsd"], "from": ORACLE_FROM,
                                  "rows": [[h, v] for h, v in zip(orc.h, orc.v)]})
    for name, s in (("sigrsv", rsv), ("sigusd", usd)):
        save(f"q-series-pool-{name}.json", {"cols": ["h", "ergX", "tokenY", "fee", "box"],
                                            "rows": [[h, *v] for h, v in zip(s.h, s.v)]})
    save("q-series-derived.json", {"cols": ["h", "rr", "nav", "rcMint", "rcRedeem", "scMint", "scRedeem", "rate",
                                            "rsvDisc", "usdVsRedeem", "usdVsOracle"],
                                   "rows": [[r["h"], r["rr"], r["nav"], r["rcMint"], r["rcRedeem"], r["scMint"],
                                             r["scRedeem"], r["rate"], round(r["disc"], 5),
                                             None if r["usdVsRedeem"] is None else round(r["usdVsRedeem"], 5),
                                             round(r["usdVsOracle"], 5)] for r in rows]})
    log(json.dumps({k: out[k] for k in ("tip", "from", "events", "chains", "checkpoints")}, indent=1))


def bot_pairs(orc, rsv, usd, bank):
    """Every mint-and-sell of the bot: a bank transaction and a pool transaction at the same height."""
    sys.path.insert(0, os.path.join(HERE, "census"))
    import bot as B
    txs = B.fetch()

    def has(io, t):
        return any(x["assets"] and any(a[0] == t for a in x["assets"]) for x in io)

    def net(t):
        e = sum(o["value"] for o in t["outputs"] if o["addr"] == BOT) - sum(i["value"] for i in t["inputs"] if i["addr"] == BOT)
        toks = {}
        for side, s in ((t["outputs"], 1), (t["inputs"], -1)):
            for x in side:
                if x["addr"] == BOT:
                    for tid, amt in x["assets"]:
                        toks[tid] = toks.get(tid, 0) + s * amt
        return e, {k: v for k, v in toks.items() if v}

    kinds = {}
    by_h = {}
    for t in txs:
        k = "bank" if has(t["inputs"], BANK_NFT) else "rsvPool" if has(t["inputs"], RSV_POOL) else \
            "usdPool" if has(t["inputs"], USD_POOL) else "other"
        t["kind"] = k
        kinds[k] = kinds.get(k, 0) + 1
        by_h.setdefault(t["h"], []).append(t)
    pairs = []
    for h, ts in sorted(by_h.items()):
        bk = [t for t in ts if t["kind"] == "bank"]
        pl = [t for t in ts if t["kind"] in ("rsvPool", "usdPool")]
        if not bk or not pl:
            continue
        e, toks = 0, {}
        legs = []
        for t in bk + pl:
            de, dt = net(t)
            e += de
            for k2, v in dt.items():
                toks[k2] = toks.get(k2, 0) + v
            legs.append({"tx": t["id"], "kind": t["kind"], "ergNet": de, "tokens": dt})
        minted = sum(v for lg in legs if lg["kind"] == "bank" for k2, v in lg["tokens"].items() if k2 in (SIGRSV, SIGUSD) and v > 0)
        paid = -sum(lg["ergNet"] for lg in legs if lg["kind"] == "bank")
        lc = orc.last_change(h)
        coin = "SigRSV" if any(lg["kind"] == "rsvPool" for lg in legs) else "SigUSD"
        pairs.append({"h": h, "coin": coin, "ergNet": e, "tokensLeft": {k2[:8]: v for k2, v in toks.items()},
                      "unitsMinted": minted, "ergPaidBank": paid, "oracleRefreshAt": lc,
                      "blocksAfterRefresh": h - lc if lc is not None else None, "legs": legs})
    tot = sum(p["ergNet"] for p in pairs)
    offs = sorted(p["blocksAfterRefresh"] for p in pairs if p["blocksAfterRefresh"] is not None)
    return {"txs": len(txs), "kinds": kinds, "pairs": len(pairs), "netNanoErg": tot,
            "byCoin": {c: {"pairs": sum(1 for p in pairs if p["coin"] == c),
                           "netNanoErg": sum(p["ergNet"] for p in pairs if p["coin"] == c),
                           "paidBankNanoErg": sum(p["ergPaidBank"] for p in pairs if p["coin"] == c)}
                       for c in ("SigRSV", "SigUSD")},
            "firstPair": pairs[0]["h"] if pairs else None, "lastPair": pairs[-1]["h"] if pairs else None,
            "offsetBlocks": {"n": len(offs), "zero": sum(1 for o in offs if o == 0),
                             "le1": sum(1 for o in offs if o <= 1), "median": offs[len(offs) // 2] if offs else None,
                             "max": offs[-1] if offs else None},
            "list": pairs}


# ---------------------------------------------------------------------------------------------------- line t

DUCK_LOAN = "db697243c2c862454a4be4c7cebf5cdb75a9d360e9297cb1543acfb0a32c5bd0"   # collateral (loan) template
DUCK_POOLS = {"93cd1a009168a06a02f5adb09dd9e88a82aca7c43b7818998d7b2b3f9aac856a": "ERG lending pool",
              "0ca1e7802ceefb98d072395b3720e1e68bd18eceacc8935714a587f4ae088b17": "token lending pool"}
SCALE = 100_000_000


def parse_pair(v):
    return [int(x) for x in v.strip("[]()").split(",")]


def parse_list(v):
    v = v.strip("[]")
    return [int(x) for x in v.split(",")] if v else []


def duck_value(Y, X, fee, coll_value):
    """Collateral value in the borrowed token, as the collateral script computes it: the DEX pool's output for the
    collateral (box value less 5,000,000 nanoERG) with the pool's ERG side raised by 2%. Parentheses are not in the
    explorer's decompiled text; this reading is the one every one of the 274 past liquidations satisfies (line t)."""
    c = coll_value - 5_000_000
    if c <= 0:
        return 0
    return Y * c * fee // ((X + X * 2 // 100) * 1000 + c * fee)


def duck_interest(start_idx, start_pos, child_lists, parent_list):
    """The compounded interest factor (x 1e8) the script folds (decompiled lines bi22): the loan's child list from its
    position, then every later child, compressed in the parent's list, then the current child."""
    acc = SCALE
    for x in child_lists[start_idx][start_pos:]:
        acc = acc * x // SCALE
    i14 = len(parent_list)
    if i14 == start_idx:
        return acc
    for x in child_lists.get(i14, []):
        acc = acc * x // SCALE
    if i14 == start_idx + 1:
        return acc
    for x in parent_list[start_idx + 1:i14]:
        acc = acc * x // SCALE
    return acc


def _tree_of(addr):
    import trees as TR
    try:
        return TR.address_tree(addr)
    except Exception:  # noqa: BLE001
        return None


def line_t(a):
    import trees as TR
    import txs as TX
    tip = a.tip or X.tip()
    col = C.fetch(None, template=DUCK_LOAN)
    live_now = X.get(f"/boxes/unspent/byErgoTreeTemplateHash/{DUCK_LOAN}?offset=0&limit=100", cache=False)["items"]
    # pools
    pools = []
    for th, kind in DUCK_POOLS.items():
        for b in X.get(f"/boxes/unspent/byErgoTreeTemplateHash/{th}?offset=0&limit=100", cache=False)["items"]:
            names = [x.get("name") for x in b["assets"]]
            pools.append({"box": b["boxId"], "kind": kind, "template": th[:12], "valueNanoErg": b["value"],
                          "h": b["settlementHeight"],
                          "assets": [[x["tokenId"], x.get("name"), x["amount"]] for x in b["assets"]]})
    # price pools (R7 of each loan) as box chains
    price_nfts = sorted({r["regs"].get("R7") for r in col if r["regs"].get("R7")})
    pchain = {n: C.fetch(n) for n in price_nfts}
    pstep = {n: pool_step(rows) for n, rows in pchain.items()}
    pooltx = {}
    for n, rows in pchain.items():
        for r in rows:
            if r["hasNft"]:
                pooltx[r["tx"]] = n
    # live loans
    loans = []
    by_tree = {}
    for b in live_now:
        by_tree.setdefault(b["ergoTree"], []).append(b)
    for tree, bs in by_tree.items():
        child_nft, parent_nft, debt_tok = (TR.constant_coll_bytes(tree, k) for k in (13, 16, 18))
        childs = X.get(f"/boxes/unspent/byTokenId/{child_nft}?offset=0&limit=100", cache=False)["items"]
        child_lists = {}
        for c in childs:
            regs = {k: v["renderedValue"] for k, v in c["additionalRegisters"].items()}
            if "R6" in regs and "R4" in regs and c["assets"] and c["assets"][0]["tokenId"] == child_nft:
                child_lists[int(regs["R6"])] = parse_list(regs["R4"])
        par = [p for p in X.get(f"/boxes/unspent/byTokenId/{parent_nft}?offset=0&limit=10", cache=False)["items"]
               if p["assets"] and p["assets"][0]["tokenId"] == parent_nft and "R4" in p["additionalRegisters"]]
        parent_list = parse_list(par[0]["additionalRegisters"]["R4"]["renderedValue"]) if par else []
        for b in bs:
            regs = {k: v["renderedValue"] for k, v in b["additionalRegisters"].items()}
            if not b["assets"] or "R5" not in regs:
                loans.append({"box": b["boxId"], "valueNanoErg": b["value"], "note": "no loan registers (dust)"})
                continue
            idx, pos = parse_pair(regs["R5"])
            thr, pen = parse_pair(regs["R6"])
            expiry, mark = parse_pair(regs["R9"])
            borrow = b["assets"][0]["amount"]
            f = duck_interest(idx, pos, child_lists, parent_list) if idx in child_lists else None
            debt = 1 + borrow * f // SCALE if f else None
            pn = regs["R7"]
            X0, Y0, fee, pbox = pstep[pn].at(tip)
            val = duck_value(Y0, X0, fee, b["value"])
            health = val * 1000 / (debt * thr) if debt else None
            loans.append({"box": b["boxId"], "h": b["settlementHeight"], "collateralNanoErg": b["value"],
                          "borrowToken": b["assets"][0]["tokenId"], "borrowUnits": borrow, "debtToken": debt_tok,
                          "interestFactor": f, "debtUnits": debt, "threshold": thr, "penalty": pen,
                          "expiryHeight": expiry, "markHeight": None if mark == 100_000_000 else mark,
                          "pricePool": pn, "pricePoolBox": pbox, "collateralValueUnits": val,
                          "health": round(health, 4) if health else None,
                          "expired": tip > expiry, "liquidatableNow": bool(health and health <= 1) or tip > expiry,
                          "borrower": regs["R4"]})
    real = [l for l in loans if "health" in l and l["health"]]
    within = {str(p): sum(1 for l in real if l["health"] <= 1 + p / 100 and not l["liquidatableNow"]) for p in (5, 10, 25)}
    # past liquidations: a loan box spent by a transaction that also spends its price pool (the pool is INPUTS(0))
    liq = [r for r in col if r["spent"] in pooltx]
    lt = TX.fetch(sorted({r["spent"] for r in liq}), "duck-liq")
    created = {}
    for r in col:
        created.setdefault(r["tx"], []).append(r)
    past = []
    for r in liq:
        t = lt[r["spent"]]
        p_in, c_in, p_out = t["inputs"][0], t["inputs"][1], t["outputs"][0]
        tokid = p_in["assets"][2][0]
        Xp, Yp, fee = p_in["value"], p_in["assets"][2][1], int(p_in["regs"]["R4"])
        dY = Yp - p_out["assets"][2][1]
        bound = duck_value(Yp, Xp, fee, c_in["value"])
        rep = t["outputs"][1]
        rep_units = sum(x[1] for x in rep["assets"] if x[0] == tokid)
        borrower_addr = None
        regs = r["regs"]
        exe_erg, exe_tok, execs, borrower_units = 0, 0, set(), 0
        for o in t["outputs"][2:]:
            if o["addr"] and o["addr"].startswith("2iHkR7CWvD1R4j1yZg5bkeDRQavjAaVPeTDFGGLZduHyfWMuYpmhHocX8GJoaieTx78FntzJbCBVL6rf96ocJoZdmWBL2fci7NqWgAirppPQmZ7fN9V6z13Ay6brPriBKYqLp1bT2Fk4FkFLCfdPpe"):
                continue
            ot = sum(x[1] for x in o["assets"] if x[0] == tokid)
            if any(x[0] for x in o["assets"] if x[0] != tokid):
                continue                       # the liquidator's own NFT box, returned as it came
            if o["addr"] and regs.get("R4") and _tree_of(o["addr"]) == regs["R4"]:
                borrower_units += ot
                continue
            exe_erg += o["value"]
            exe_tok += ot
            execs.add(o["addr"])
        expiry, mark = parse_pair(regs["R9"])
        kind = "expired" if t["h"] > expiry else "undercollateralised"
        price = Xp / Yp
        past.append({"tx": t["id"], "h": t["h"], "pricePool": r["regs"]["R7"], "collateralNanoErg": r["value"],
                     "borrowUnits": r["assets"][0][1] if r["assets"] else 0, "soldUnits": dY, "contractBound": bound,
                     "slackUnits": dY - bound, "repaidUnits": rep_units, "toBorrowerUnits": borrower_units,
                     "executors": sorted(a2 for a2 in execs if a2), "executorNanoErg": exe_erg,
                     "executorUnits": exe_tok, "executorTakeNanoErg": exe_erg + int(exe_tok * price),
                     "kind": kind, "markHeight": None if mark == 100_000_000 else mark,
                     "blocksMarkToLiquidation": None if mark == 100_000_000 else t["h"] - mark,
                     "blocksAfterExpiry": t["h"] - expiry if kind == "expired" else None,
                     "loanBoxCreated": r["h"]})
    # when did each undercollateralised loan become liquidatable: the first price-pool state after the loan box was
    # created whose collateral value fell to the threshold, with the debt taken at its principal (interest ignored,
    # so this height is late by at most the interest's effect [inferred])
    for p in past:
        if p["kind"] != "undercollateralised":
            continue
        s = pstep[p["pricePool"]]
        i0 = bisect.bisect_left(s.h, p["loanBoxCreated"])
        thr = 1400
        first = None
        rr = [x for x in col if x["spent"] == p["tx"]]
        thr = parse_pair(rr[0]["regs"]["R6"])[0] if rr else 1400
        # walk back the loan's own chain to its first box after the last change of borrow amount
        for j in range(max(0, i0 - 1), len(s.h)):
            if s.h[j] > p["h"]:
                break
            Xs, Ys, fs, _ = s.v[j]
            if duck_value(Ys, Xs, fs, p["collateralNanoErg"]) * 1000 <= p["borrowUnits"] * thr:
                first = max(s.h[j], p["loanBoxCreated"])
                break
        p["liquidatableFrom"] = first
        p["blocksLiquidatableToMark"] = (p["markHeight"] - first) if (first and p["markHeight"]) else None
        p["blocksLiquidatableToLiquidation"] = (p["h"] - first) if first else None
    exec_count = {}
    for p in past:
        for e in p["executors"]:
            exec_count[e] = exec_count.get(e, 0) + 1
    takes = sorted(p["executorTakeNanoErg"] for p in past)
    out = {"explorer": X.EXPLORER, "tip": tip, "loanTemplate": DUCK_LOAN, "loanBoxesEver": len(col),
           "pools": pools, "liveLoans": loans, "within": within,
           "liveSummary": {"loans": len(real), "collateralNanoErg": sum(l["collateralNanoErg"] for l in real),
                           "liquidatableNow": sum(1 for l in real if l["liquidatableNow"]),
                           "expired": sum(1 for l in real if l["expired"])},
           "pastLiquidations": {"n": len(past), "first": min(p["h"] for p in past), "last": max(p["h"] for p in past),
                                "byKind": {k: sum(1 for p in past if p["kind"] == k) for k in ("expired", "undercollateralised")},
                                "contractBoundHeldInAll": all(p["slackUnits"] >= 0 for p in past),
                                "executors": exec_count,
                                "executorTakeNanoErg": {"total": sum(takes), "median": takes[len(takes) // 2],
                                                        "max": takes[-1]},
                                "list": sorted(past, key=lambda p: p["h"])}}
    save("t.json", out)
    log(json.dumps({k: out[k] for k in ("liveSummary", "within")}, indent=1),
        json.dumps({k: v for k, v in out["pastLiquidations"].items() if k != "list"}, indent=1))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("line", choices=["q", "r", "s", "t", "u"])
    p.add_argument("--tip", type=int, default=None)
    a = p.parse_args()
    {"q": line_q, "t": line_t}[a.line](a)
    log("requests", X.stats)


if __name__ == "__main__":
    main()
