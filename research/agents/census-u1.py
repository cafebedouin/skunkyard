#!/usr/bin/env python3
"""U1: what a same-block arbitrageur could have taken on Ergo mainnet, per block, by kind.

Lines (prompts/census-u1.md):
  a  Babel box against an ErgoDEX v1 N2T pool: one transaction, no capital (the positive control, SK-049)
  b  SigmaUSD bank against a pool: two transactions (bank and pool each take their successor at OUTPUTS(0))
  c  pool against pool, same token: two transactions
  d  swaps on ErgoDEX v1 N2T pools, per day, and over 2026-08-13 to 2026-09-12
  e  ERG paid to executors by ErgoDEX order executions

The state used for block h is the state at the start of h (after block h-1): what the builder of h could take
before including anything else. A state persists until one of its boxes is spent, so the same gap can stand
for many blocks; each line therefore reports a lower total (each run of consecutive open blocks counted once,
at its largest profit) and an upper total (each distinct state counted once). Neither multiplies by blocks.

Source: the Ergo Explorer API v1 (ERGO_EXPLORER, default the Cornell mirror; api.ergoplatform.com is not
reachable from the sandbox this was written in). Raw responses are cached under research/agents/census/raw/.
Integer arithmetic for every pool, Babel and bank rule (census/amm.py); floats only in the summary.

usage: census-u1.py [--from H] [--to H] [--json out.json] [--csv-dir DIR] [--lithos lithos.json]
"""
import argparse, bisect, calendar, collections, csv, json, os, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "census"))
import amm as A  # noqa: E402
import explorer as X  # noqa: E402
import trees as T  # noqa: E402

SIGUSD = "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04"
SIGRSV = "003bd19d0187117f130b62e1bcab0939929ff5c7709f843c5c4dd158949285d0"
BANK_NFT = "7d672d1def471720ca5782fd6473e47e796d9ac0c138d9911346f118b2f6d9d9"
ORACLE_NFT = "011d3364de07e5a26f0c4eef0852cddb387039a921b7154ef3cab22c6eda887f"   # bank tree constant 3
LIT = "c1980d829988229516430a47a5eca376060b6ce859616db0936e78ab25cb6de7"
RSN = "8b08cdd5449a9592a9e79711d7d79249d7a03c535d17efaee83e216e80a44c4b"
REEMISSION = "d9a2cc8a09abfaed87afacfbb7daee79a6b26f10c6613fc13d3f3953e5521d1a"
MIN_BOX = 1_000_000        # nanoERG left in a recreated Babel box, and the smallest profit counted (a payable box)
WINDOW = 21_600
D_WINDOW = ("2026-08-13", "2026-09-12")   # [00:00 UTC of the first day, 00:00 UTC of the second)
NAMES = {SIGUSD: "SigUSD", SIGRSV: "SigRSV", RSN: "RSN", LIT: "LIT"}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def reg(box, r):
    v = box.get("additionalRegisters", {}).get(r)
    return None if v is None else v.get("renderedValue")


def asc_offset(base, total, key, target, sep="&"):
    """Smallest offset in an ascending listing whose item has key >= target (limit=1 probes)."""
    lo, hi = 0, total
    while lo < hi:
        m = (lo + hi) // 2
        it = X.get(f"{base}{sep}offset={m}&limit=1")["items"][0]
        if it[key] < target:
            lo = m + 1
        else:
            hi = m
    return lo


def listing(base, start, stop_key, stop, page, sep="&"):
    """Ascending pages from `start` until an item's stop_key exceeds `stop`."""
    out, off = [], start
    while True:
        d = X.get(f"{base}{sep}offset={off}&limit={page}")
        items = d["items"]
        out += items
        off += len(items)
        if not items or items[-1][stop_key] > stop or off >= d["total"]:
            return [x for x in out if x[stop_key] <= stop]


# ---- blocks, rewards, fees -----------------------------------------------------------------------------------

def blocks(lo, hi):
    out = {}
    g = lo - 1
    while g < hi:
        n = min(500, hi - g)
        for b in X.get(f"/blocks/byGlobalIndex/stream?minGix={g}&limit={n}"):
            out[b["height"]] = b
        g += n
    return out


def fee_sample(blk, step):
    """Fees per block on every `step`-th block: the sum of outputs to the fee contract."""
    fees = {}
    for h in sorted(blk):
        if (h - min(blk)) % step:
            continue
        s = X.get(f"/blocks/{blk[h]['id']}")
        txs = s["block"]["blockTransactions"]
        fees[h] = sum(o["value"] for t in txs for o in t["outputs"] if o["ergoTree"] == T.FEE_TREE)
        em = txs[0]["outputs"][1] if len(txs[0]["outputs"]) > 1 else None
        if em is not None and h == min(blk):
            reem = sum(a["amount"] for a in em["assets"] if a["tokenId"] == REEMISSION)
            fees["_reward_check"] = (em["value"], reem)
    return fees


# ---- pools ---------------------------------------------------------------------------------------------------

def pool_state(box):
    a = box["assets"]
    if len(a) != 3 or reg(box, "R4") is None:
        return None
    return {"nft": a[0]["tokenId"], "X": box["value"], "lp": a[1]["amount"], "token": a[2]["tokenId"],
            "Y": a[2]["amount"], "fee": int(reg(box, "R4"))}


def pool_txs(lo_key, hi_key, key):
    base = f"/transactions/byInputsScriptTemplateHash/{T.N2T_POOL_TEMPLATE_HASH}?sortDirection=asc"
    total = X.get(f"{base}&offset=0&limit=1", cache=False)["total"]
    start = asc_offset(base, total, key, lo_key)
    return listing(base, start, key, hi_key, 500)


def pool_events(txs):
    """One event per pool spend: (height, index-in-block, before, after, tx)."""
    ev = []
    for tx in txs:
        for i in tx["inputs"]:
            if T.template_hash(i["ergoTree"]) != T.N2T_POOL_TEMPLATE_HASH:
                continue
            before = pool_state(i)
            if before is None:
                continue
            after = None
            for o in tx["outputs"]:
                s = pool_state(o) if o["ergoTree"] == i["ergoTree"] else None
                if s and s["nft"] == before["nft"]:
                    after = s
                    break
            ev.append((tx["inclusionHeight"], tx["index"], before, after, tx, i.get("outputSettledAt")))
    ev.sort(key=lambda e: (e[0], e[1]))
    return ev


class Timeline:
    """States of one entity; at(h) is the state at the start of block h."""

    def __init__(self):
        self.h, self.s = [], []

    def add(self, h, s):
        self.h.append(h)
        self.s.append(s)

    def at(self, h):
        i = bisect.bisect_left(self.h, h) - 1
        return self.s[i] if i >= 0 else None

    def changes(self, lo, hi):
        return {x + 1 for x in self.h if lo <= x + 1 <= hi}


def pool_timelines(ev, unspent, lo):
    tl = collections.defaultdict(Timeline)
    seen = set()
    for h, _, before, after, _, settled in ev:
        n = before["nft"]
        if n not in seen:
            seen.add(n)
            tl[n].add(settled if settled is not None else lo - 1, before)
        tl[n].add(h, after)
    for b in unspent:
        s = pool_state(b)
        if s and s["nft"] not in seen:
            seen.add(s["nft"])
            tl[s["nft"]].add(b["settlementHeight"], s)
    return tl


# ---- Babel boxes ---------------------------------------------------------------------------------------------

def babel_boxes():
    base = f"/boxes/byErgoTreeTemplateHash/{T.BABEL_TEMPLATE_HASH}?"
    total = X.get(f"{base}offset=0&limit=1", cache=False)["total"]
    boxes = []
    for off in range(0, total, 100):
        boxes += X.get(f"{base}offset={off}&limit=100")["items"]
    sbase = f"/transactions/byInputsScriptTemplateHash/{T.BABEL_TEMPLATE_HASH}?sortDirection=asc"
    stotal = X.get(f"{sbase}&offset=0&limit=1", cache=False)["total"]
    spends = []
    for off in range(0, stotal, 500):
        spends += X.get(f"{sbase}&offset={off}&limit=500")["items"]
    spent_at = {}
    for tx in spends:
        for i in tx["inputs"]:
            spent_at[i["boxId"]] = tx["inclusionHeight"]
    out = []
    for b in boxes:
        tok = T.babel_token(b["ergoTree"])
        r5 = reg(b, "R5")
        if tok is None or r5 is None:
            continue
        out.append({"boxId": b["boxId"], "token": tok, "bid": int(r5), "value": b["value"],
                     "created": b["settlementHeight"], "spent": spent_at.get(b["boxId"]),
                     "spentTx": b.get("spentTransactionId")})
    return out, spends


def babel_live(boxes, h):
    return [b for b in boxes if b["created"] < h and (b["spent"] is None or b["spent"] >= h)]


# ---- segments: profit per block from a state that persists ---------------------------------------------------

def summarize(segs, lo, hi):
    """segs: sorted list of (start, end, profit, detail) covering [lo, hi] for one key."""
    open_ = [s for s in segs if s[2] >= MIN_BOX]
    blocks_open = sum(s[1] - s[0] + 1 for s in open_)
    upper = sum(s[2] for s in open_)
    lower, run_max, prev_end = 0, 0, None
    for s in segs:
        if s[2] >= MIN_BOX:
            if prev_end is not None and s[0] == prev_end + 1 and run_max:
                run_max = max(run_max, s[2])
            else:
                lower += run_max
                run_max = s[2]
        else:
            lower += run_max
            run_max = 0
        prev_end = s[1]
    lower += run_max
    best = max(open_, key=lambda s: s[2], default=None)
    return {"blocksOpen": blocks_open, "statesOpen": len(open_), "lowerNanoErg": lower, "upperNanoErg": upper,
            "maxNanoErg": best[2] if best else 0, "maxAt": best[0] if best else None,
            "maxDetail": best[3] if best else None}


def run_segments(change_pts, lo, hi, evaluate):
    pts = sorted({lo} | {c for c in change_pts if lo <= c <= hi})
    segs = []
    for k, c in enumerate(pts):
        end = pts[k + 1] - 1 if k + 1 < len(pts) else hi
        p, det = evaluate(c)
        segs.append((c, end, p, det))
    return segs


# ---- line (a) ------------------------------------------------------------------------------------------------

def line_a(boxes, tl, lo, hi):
    by_tok = collections.defaultdict(list)
    for b in boxes:
        by_tok[b["token"]].append(b)
    pools_by_tok = collections.defaultdict(list)
    for n, t in tl.items():
        s = t.s[-1] or next((x for x in t.s if x), None)
        if s:
            pools_by_tok[s["token"]].append(n)
    res, rows = {}, []
    for tok, bx in by_tok.items():
        live_any = [b for b in bx if b["created"] <= hi and (b["spent"] is None or b["spent"] >= lo)]
        if not live_any or not pools_by_tok.get(tok):
            continue
        pools = pools_by_tok[tok]
        pts = set()
        for n in pools:
            pts |= tl[n].changes(lo, hi)
        for b in live_any:
            pts.add(b["created"] + 1)
            if b["spent"] is not None:
                pts.add(b["spent"] + 1)

        def ev(h, bx=bx, pools=pools):
            best = (0, None)
            live = [b for b in babel_live(bx, h) if b["value"] - MIN_BOX > 0]
            for n in pools:
                s = tl[n].at(h)
                if not s or s["Y"] <= 1 or s["X"] <= A.POOL_MIN_VALUE:
                    continue
                for b in live:
                    r = A.babel_vs_pool(s["X"], s["Y"], s["fee"], b["bid"], b["value"] - MIN_BOX)
                    if r and r[0] > best[0]:
                        best = (r[0], {"pool": n, "babel": b["boxId"], "bid": b["bid"], "poolX": s["X"],
                                       "poolY": s["Y"], "fee": s["fee"], "X": r[1], "T": r[2], "Y": r[3]})
            # bid and pool price at the best box regardless of profit, for the report
            if best[1] is None and live:
                b = max(live, key=lambda b: b["bid"])
                s = max((tl[n].at(h) for n in pools if tl[n].at(h)), key=lambda s: s["X"], default=None)
                if s:
                    best = (0, {"bid": b["bid"], "poolX": s["X"], "poolY": s["Y"], "fee": s["fee"]})
            return best

        segs = run_segments(pts, lo, hi, ev)
        res[tok] = summarize(segs, lo, hi)
        res[tok]["liveBabelBoxes"] = len(live_any)
        res[tok]["pools"] = len(pools)
        res[tok]["firstState"] = segs[0][3]
        for s in segs:
            if s[2] >= MIN_BOX:
                d = s[3]
                rows += [[h, NAMES.get(tok, tok[:8]), d["pool"], d["bid"], f"{d['poolX'] / d['poolY']:.4f}",
                          d["X"], s[2]] for h in range(s[0], s[1] + 1)]
    return res, rows


def babel_taken(spends, lo, hi):
    """Babel spends that also spend an ErgoDEX v1 pool: the control, done on chain."""
    both = []
    for tx in spends:
        if any(T.template_hash(i["ergoTree"]) == T.N2T_POOL_TEMPLATE_HASH for i in tx["inputs"]):
            both.append((tx["inclusionHeight"], tx["id"]))
    return {"allTime": len(both), "inWindow": sum(1 for h, _ in both if lo <= h <= hi),
            "babelSpendsAllTime": len(spends), "babelSpendsInWindow": sum(1 for t in spends if lo <= t["inclusionHeight"] <= hi),
            "lastBabelSpend": max((t["inclusionHeight"] for t in spends), default=None), "examples": both[-3:]}


# ---- line (b) ------------------------------------------------------------------------------------------------

def nft_timeline(nft, lo, hi):
    base = f"/boxes/byTokenId/{nft}?"
    total = X.get(f"{base}offset=0&limit=1", cache=False)["total"]
    start = max(0, asc_offset(base, total, "settlementHeight", lo, sep="") - 2)
    items = listing(base, start, "settlementHeight", hi, 100, sep="")
    tl = Timeline()
    for b in sorted(items, key=lambda b: (b["settlementHeight"], b["globalIndex"])):
        if any(a["tokenId"] == nft for a in b["assets"]):
            tl.add(b["settlementHeight"], b)
    return tl


def line_b(tl, lo, hi):
    bank, oracle = nft_timeline(BANK_NFT, lo, hi), nft_timeline(ORACLE_NFT, lo, hi)
    tree_ok = bank.s and "0e20" + ORACLE_NFT in bank.s[-1]["ergoTree"]
    res, rows = {}, []
    for coin, tok in (("sc", SIGUSD), ("rc", SIGRSV)):
        pools = [n for n, t in tl.items() if any(s and s["token"] == tok for s in t.s)]
        pts = bank.changes(lo, hi) | oracle.changes(lo, hi)
        for n in pools:
            pts |= tl[n].changes(lo, hi)

        def ev(h, coin=coin, pools=pools):
            bb, ob = bank.at(h), oracle.at(h)
            if bb is None or ob is None or reg(ob, "R4") is None:
                return 0, None
            bk = A.Bank(bb["value"], int(reg(bb, "R4")), int(reg(bb, "R5")), int(reg(ob, "R4")))
            best = (0, None)
            for n in pools:
                s = tl[n].at(h)
                if not s or s["Y"] <= 1 or s["X"] <= A.POOL_MIN_VALUE:
                    continue
                r = A.bank_vs_pool(bk, coin, (s["X"], s["Y"], s["fee"]))
                if r and r[1] > best[0]:
                    best = (r[1], {"pool": n, "dir": r[0], "capital": r[2], "units": r[3],
                                   "bankPrice": bk.sc_price() if coin == "sc" else bk.rc_price(),
                                   "poolPrice": f"{s['X'] / s['Y']:.2f}", "fee": s["fee"],
                                   "rrPct": (bk.R * 100 // (bk.sc * bk.rate)) if bk.sc * bk.rate else None})
            return best

        segs = run_segments(pts, lo, hi, ev)
        res[coin] = summarize(segs, lo, hi)
        res[coin]["pools"] = len(pools)
        res[coin]["statesEvaluated"] = len(segs)
        caps = [s[3]["capital"] for s in segs if s[2] >= MIN_BOX]
        res[coin]["capitalMaxNanoErg"] = max(caps, default=0)
        res[coin]["capitalMedianNanoErg"] = sorted(caps)[len(caps) // 2] if caps else 0
        dirs = collections.Counter(s[3]["dir"] for s in segs if s[2] >= MIN_BOX)
        res[coin]["directions"] = dict(dirs)
        for s in segs:
            if s[2] >= MIN_BOX:
                d = s[3]
                rows += [[h, NAMES[tok], d["pool"], d["dir"], d["bankPrice"], d["poolPrice"], d["rrPct"],
                          d["capital"], s[2]] for h in range(s[0], s[1] + 1)]
    rr = []
    for h in (lo, hi):
        bb, ob = bank.at(h), oracle.at(h)
        bk = A.Bank(bb["value"], int(reg(bb, "R4")), int(reg(bb, "R5")), int(reg(ob, "R4")))
        rr.append({"height": h, "reserveNanoErg": bk.R, "scCirc": bk.sc, "rcCirc": bk.rc, "rate": bk.rate,
                   "rrPct": bk.R * 100 // (bk.sc * bk.rate) if bk.sc * bk.rate else None,
                   "scPrice": bk.sc_price(), "rcPrice": bk.rc_price()})
    return res, rows, {"bankBoxesInWindow": len([x for x in bank.h if lo <= x <= hi]),
                       "oracleBoxesInWindow": len([x for x in oracle.h if lo <= x <= hi]),
                       "bankTreeHasOracleNft": bool(tree_ok), "bankAt": rr}


# ---- line (c) ------------------------------------------------------------------------------------------------

def line_c(tl, lo, hi):
    by_tok = collections.defaultdict(list)
    for n, t in tl.items():
        s = next((x for x in reversed(t.s) if x), None)
        if s:
            by_tok[s["token"]].append(n)
    res, rows, rsn = {}, [], None
    for tok, pools in by_tok.items():
        if len(pools) < 2:
            continue
        pts = set()
        for n in pools:
            pts |= tl[n].changes(lo, hi)

        def ev(h, pools=pools):
            st = {n: tl[n].at(h) for n in pools}
            st = {n: s for n, s in st.items() if s and s["Y"] > 1 and s["X"] > A.POOL_MIN_VALUE}
            best = (0, None)
            for a in st:
                for b in st:
                    if a == b:
                        continue
                    sa, sb = st[a], st[b]
                    r = A.pool_vs_pool((sa["X"], sa["Y"], sa["fee"]), (sb["X"], sb["Y"], sb["fee"]))
                    if r and r[0] > best[0]:
                        best = (r[0], {"buy": a, "sell": b, "capital": r[1], "T": r[2],
                                       "fees": (sa["fee"], sb["fee"])})
            return best

        segs = run_segments(pts, lo, hi, ev)
        res[tok] = summarize(segs, lo, hi)
        res[tok]["pools"] = len(pools)
        caps = [s[3]["capital"] for s in segs if s[2] >= MIN_BOX]
        res[tok]["capitalMedianNanoErg"] = sorted(caps)[len(caps) // 2] if caps else 0
        res[tok]["capitalMaxNanoErg"] = max(caps, default=0)
        for s in segs:
            if s[2] >= MIN_BOX:
                d = s[3]
                rows += [[h, NAMES.get(tok, tok[:8]), d["buy"], d["sell"], d["fees"][0], d["fees"][1],
                          d["capital"], s[2]] for h in range(s[0], s[1] + 1)]
        if tok == RSN:
            rsn = rsn_gap(tl, pools, pts, lo, hi)
    return res, rows, rsn


def rsn_gap(tl, pools, pts, lo, hi):
    """Mid-price gap between the two deepest RSN pools, weighted by blocks, against their combined fee."""
    deep = sorted(pools, key=lambda n: -max((s["X"] for s in tl[n].s if s), default=0))[:2]
    ps = sorted({lo} | {c for c in pts if lo <= c <= hi})
    gaps = []
    for k, c in enumerate(ps):
        end = ps[k + 1] - 1 if k + 1 < len(ps) else hi
        a, b = tl[deep[0]].at(c), tl[deep[1]].at(c)
        if not a or not b:
            continue
        pa, pb = a["X"] / a["Y"], b["X"] / b["Y"]
        gaps.append((max(pa, pb) / min(pa, pb) - 1, end - c + 1, (a["fee"], b["fee"])))
    tot = sum(w for _, w, _ in gaps)
    srt = sorted(gaps)
    acc, med = 0, None
    for g, w, _ in srt:
        acc += w
        if acc >= tot / 2:
            med = g
            break
    fees = gaps[-1][2] if gaps else None
    comb = (2000 - fees[0] - fees[1]) / 1000 if fees else None
    return {"pools": deep, "fees": fees, "combinedFee": comb, "medianGap": med,
            "meanGap": sum(g * w for g, w, _ in gaps) / tot if tot else None,
            "maxGap": max((g for g, _, _ in gaps), default=None),
            "blocksGapAboveCombinedFee": sum(w for g, w, _ in gaps if comb is not None and g > comb), "blocks": tot}


# ---- lines (d) and (e) ---------------------------------------------------------------------------------------

def classify(before, after):
    if after is None:
        return "other"
    if after["lp"] != before["lp"]:
        return "deposit" if after["lp"] < before["lp"] else "redeem"
    dx, dy = after["X"] - before["X"], after["Y"] - before["Y"]
    return "swap" if dx * dy < 0 else "other"


def executor_fee(tx):
    """ERG an executor took from an order execution: P2PK outputs other than the order's redeemer, net of
    P2PK inputs of the same addresses. Inferred classification: an order is a non-pool, non-P2PK input that
    names a redeemer key (ProveDlog constant)."""
    orders = [i for i in tx["inputs"] if not i["ergoTree"].startswith("0008cd")
              and T.template_hash(i["ergoTree"]) != T.N2T_POOL_TEMPLATE_HASH]
    if not orders:
        return None
    redeemers = set()
    for o in orders:
        k = o["ergoTree"].find("08cd")
        if k >= 0:
            redeemers.add("0008cd" + o["ergoTree"][k + 4:k + 70])
    outs = collections.Counter()
    for o in tx["outputs"]:
        if o["ergoTree"].startswith("0008cd") and o["ergoTree"] not in redeemers:
            outs[o["ergoTree"]] += o["value"]
    ins = sum(i["value"] for i in tx["inputs"] if i["ergoTree"] in outs)
    return max(0, sum(outs.values()) - ins)


def day(ts_ms):
    return time.strftime("%Y-%m-%d", time.gmtime(ts_ms / 1000))


def line_de(ev, lo, hi):
    per_day = collections.defaultdict(collections.Counter)
    tot = collections.Counter()
    ex_fee, ex_n, seen = 0, 0, set()
    for h, _, before, after, tx, _ in ev:
        if not lo <= h <= hi:
            continue
        k = classify(before, after)
        is_order = executor_fee(tx) is not None
        tot[k] += 1
        per_day[day(tx["timestamp"])][k] += 1
        if k == "swap":
            tot["swap_order" if is_order else "swap_direct"] += 1
            per_day[day(tx["timestamp"])]["swap_order" if is_order else "swap_direct"] += 1
        if is_order and tx["id"] not in seen:
            seen.add(tx["id"])
            ex_fee += executor_fee(tx)
            ex_n += 1
    return dict(tot), {d: dict(c) for d, c in sorted(per_day.items())}, {"orderTxs": ex_n, "executorNanoErg": ex_fee}


def d_window(ev_d, t0, t1):
    tot = collections.Counter()
    for h, _, before, after, tx, _ in ev_d:
        if t0 <= tx["timestamp"] < t1:
            k = classify(before, after)
            tot[k] += 1
            if k == "swap":
                tot["swap_order" if executor_fee(tx) is not None else "swap_direct"] += 1
    return dict(tot)


# ---- main ----------------------------------------------------------------------------------------------------

def write_csv(path, head, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)
    return os.path.getsize(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="lo", type=int)
    ap.add_argument("--to", dest="hi", type=int)
    ap.add_argument("--json")
    ap.add_argument("--csv-dir")
    ap.add_argument("--lithos", help="output of lithos-blocks-mainnet.py --json, read at the window's end")
    ap.add_argument("--fee-step", type=int, default=10, help="read fees on every n-th block")
    a = ap.parse_args()
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tip = X.tip()
    hi = a.hi or tip
    lo = a.lo or hi - WINDOW + 1
    log(f"window {lo}..{hi} ({hi - lo + 1} blocks), explorer tip {tip}, {X.EXPLORER}")

    blk = blocks(lo, hi)
    log(f"blocks {len(blk)}")
    fees = fee_sample(blk, a.fee_step)
    reward_check = fees.pop("_reward_check", None)
    log(f"fee sample {len(fees)} blocks")

    ev = pool_events(pool_txs(lo, tip, "inclusionHeight"))
    unspent = []
    base = f"/boxes/unspent/byErgoTreeTemplateHash/{T.N2T_POOL_TEMPLATE_HASH}?"
    total = X.get(f"{base}offset=0&limit=1", cache=False)["total"]
    for off in range(0, total, 100):
        unspent += X.get(f"{base}offset={off}&limit=100")["items"]
    tl = pool_timelines(ev, unspent, lo)
    log(f"pool events {len(ev)}, pools {len(tl)}")

    boxes, spends = babel_boxes()
    log(f"babel boxes {len(boxes)}, spends {len(spends)}")
    ra, rows_a = line_a(boxes, tl, lo, hi)
    taken = babel_taken(spends, lo, hi)
    log("line a done")
    rb, rows_b, bank_info = line_b(tl, lo, hi)
    log("line b done")
    rc, rows_c, rsn = line_c(tl, lo, hi)
    log("line c done")
    de_tot, de_day, ex = line_de(ev, lo, hi)

    t0 = calendar.timegm(time.strptime(D_WINDOW[0], "%Y-%m-%d")) * 1000
    t1 = calendar.timegm(time.strptime(D_WINDOW[1], "%Y-%m-%d")) * 1000
    ev_d = pool_events(pool_txs(t0, t1, "timestamp"))
    d_tot = d_window(ev_d, t0, t1)
    d_heights = [e[0] for e in ev_d if t0 <= e[4]["timestamp"] < t1]

    lit = X.get(f"/boxes/unspent/byTokenId/{LIT}?offset=0&limit=100")
    ld_pools = []
    for off in range(0, lit["total"], 100):
        for b in X.get(f"/boxes/unspent/byTokenId/{LIT}?offset={off}&limit=100")["items"]:
            if len(b["assets"]) == 3 and all(f"R{k}" in b["additionalRegisters"] for k in range(4, 9)) \
                    and b["assets"][1]["tokenId"] == LIT:
                ld_pools.append({"boxId": b["boxId"], "nft": b["assets"][0]["tokenId"], "valueNanoErg": b["value"],
                                 "lit": b["assets"][1]["amount"], "R5": reg(b, "R5"), "R6": reg(b, "R6"),
                                 "settlementHeight": b["settlementHeight"]})
    lit_on_ergodex = sum(1 for t in tl.values() if any(s and s["token"] == LIT for s in t.s))

    lith = None
    if a.lithos:
        lj = json.load(open(a.lithos))
        lith = {"share": lj["share"], "lithosBlocks": lj["lithosBlocks"], "firstLithosBlock": lj["firstLithosBlock"],
                "tip": lj["tip"], "readAt": lj["readAt"],
                "inWindow": sum(1 for b in lj["blocks"] if lo <= b["height"] <= hi)}

    n = hi - lo + 1
    rewards = [blk[h]["minerReward"] for h in blk]
    out = {
        "startedAt": started, "explorer": X.EXPLORER, "explorerTipAtStart": tip, "from": lo, "to": hi, "blocks": n,
        "firstBlockTime": blk[lo]["timestamp"], "lastBlockTime": blk[hi]["timestamp"],
        "minBoxNanoErg": MIN_BOX,
        "rewardNanoErgPerBlockMean": sum(rewards) // len(rewards), "rewardDistinct": sorted(set(rewards)),
        "rewardBoxCheck": reward_check,
        "feeSampleBlocks": len(fees), "feeSampleStep": a.fee_step,
        "feeNanoErgPerBlockMean": sum(fees.values()) // len(fees),
        "feeNanoErgPerBlockMedian": sorted(fees.values())[len(fees) // 2],
        "poolEventsLoToTip": len(ev), "poolsTracked": len(tl),
        "a": ra, "aTakenOnChain": taken,
        "b": rb, "bBank": bank_info,
        "c": rc, "cRSN": rsn,
        "d": de_tot, "dPerDay": de_day,
        "dWindow": {"from": D_WINDOW[0], "to": D_WINDOW[1], "heights": [min(d_heights, default=None),
                                                                      max(d_heights, default=None)], **d_tot},
        "e": ex,
        "lithosDex": {"pools": ld_pools, "litPoolsOnErgoDexV1": lit_on_ergodex},
        "lithos": lith, "requests": dict(X.stats),
    }
    if a.csv_dir:
        os.makedirs(a.csv_dir, exist_ok=True)
        sizes = {
            "a": write_csv(os.path.join(a.csv_dir, "u1-a-babel.csv"),
                           ["height", "token", "poolNft", "bidNanoErgPerUnit", "poolNanoErgPerUnit", "xNanoErg",
                            "profitNanoErg"], rows_a),
            "b": write_csv(os.path.join(a.csv_dir, "u1-b-bank.csv"),
                           ["height", "coin", "poolNft", "direction", "bankPriceNanoErg", "poolNanoErgPerUnit",
                            "reserveRatioPct", "capitalNanoErg", "profitNanoErg"], rows_b),
            "c": write_csv(os.path.join(a.csv_dir, "u1-c-pools.csv"),
                           ["height", "token", "buyPoolNft", "sellPoolNft", "buyFee", "sellFee", "capitalNanoErg",
                            "profitNanoErg"], rows_c),
            "d": write_csv(os.path.join(a.csv_dir, "u1-d-per-day.csv"),
                           ["day", "swap", "swap_direct", "swap_order", "deposit", "redeem", "other"],
                           [[d] + [c.get(k, 0) for k in ("swap", "swap_direct", "swap_order", "deposit", "redeem",
                                                          "other")] for d, c in de_day.items()]),
        }
        out["csvBytes"] = sizes
    s = json.dumps(out, indent=1, default=str)
    if a.json:
        open(a.json, "w").write(s)
    print(s)
    log(f"requests: {X.stats}")


if __name__ == "__main__":
    main()
