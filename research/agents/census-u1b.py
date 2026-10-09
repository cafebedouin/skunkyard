#!/usr/bin/env python3
"""U1b: every keyless offer a block builder could fill, not only Babel boxes (prompts/census-u1b.md).

Lines, each a subcommand writing census/u1b/<line>.json (and CSVs where a table is long):
  f  inputs spent with no signature in the window, grouped by template hash; unspent boxes now; names
  k  fees on every block of the window (U1 sampled every tenth)
  h  more pools: ErgoDEX v1 token-to-token, and every other pool template found by (f); U1 lines a and c rerun
  g  fixed-price offers: every unspent box of the offer templates in (f), priced, against the pools of (h)
  i  every other kind: hypotheses, counted
  j  takes needing capital, capped at the test wallet's 10 ERG, with the leg risk

Same source and rules as U1 (census-u1.py): the Cornell explorer mirror, raw responses cached under
census/raw/ (git-ignored), integer arithmetic matching each contract, rounding against the taker.

usage: census-u1b.py LINE [--from H] [--to H] [--workers N]
"""
import argparse, collections, importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "census"))
import amm as A  # noqa: E402
import explorer as X  # noqa: E402
import trees as T  # noqa: E402

OUT = os.path.join(HERE, "census", "u1b")
LO, HI = 1_869_418, 1_891_017          # U1's window
RENT_PERIOD = 1_051_200                # blocks (4 years at 2 min); Ergo storage rent, ergo core parameters


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def save(name, obj):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    with open(p, "w") as f:
        json.dump(obj, f, indent=1, default=str, sort_keys=False)
    log(f"wrote {p} ({os.path.getsize(p)} bytes)")
    return p


def load(name):
    with open(os.path.join(OUT, name)) as f:
        return json.load(f)


def u1():
    """census-u1.py as a module (its file name has a dash)."""
    spec = importlib.util.spec_from_file_location("census_u1", os.path.join(HERE, "census-u1.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def unspent_total(th):
    d = X.get(f"/boxes/unspent/byErgoTreeTemplateHash/{th}?offset=0&limit=1", cache=False)
    return d["total"] if d else None


def unspent_boxes(th, cap=5000):
    base = f"/boxes/unspent/byErgoTreeTemplateHash/{th}?"
    total = X.get(f"{base}offset=0&limit=1", cache=False)["total"]
    out = []
    for off in range(0, min(total, cap), 100):
        out += X.get(f"{base}offset={off}&limit=100", cache=False)["items"]
    return out, total


# ---- line f --------------------------------------------------------------------------------------------------

def line_f(a):
    import keyless as K
    import names as N
    X.MIN_INTERVAL = 0.12
    r = K.scan(a.lo, a.hi, a.workers, log)
    # rent claims: what each claim took (box value minus the recreated box) and where it went
    rent = r["rentTxs"]
    # the pass's aggregate (about 25 MB, so in the git-ignored census/out/); (k) reads its fees
    with open(os.path.join(HERE, "census", "out", "scan-raw.json"), "w") as fh:
        json.dump(r, fh)
    rows = []
    for th, t in sorted(r["templates"].items(), key=lambda kv: -kv[1]["keyless"]):
        if t["keyless"] == 0:
            continue
        sample = t["samples"][0]["box"] if t["samples"] else None
        box = X.get(f"/boxes/{sample}") if sample else None
        # storage rent: a box older than RENT_PERIOD may be spent by anyone (the miner) with no proof; a
        # template whose keyless samples are all that old is rent, not a keyless contract path
        ages = []
        for s in t["samples"]:
            b = X.get(f"/boxes/{s['box']}")
            if b:
                ages.append(s["height"] - b["creationHeight"])
        rows.append({"templateHash": th, "keylessSpends": t["keyless"], "keylessTxs": t["txs"],
                     "signedSpends": t["signed"], "keylessNanoErg": t["keylessNanoErg"],
                     "firstKeyless": t["firstKeyless"], "lastKeyless": t["lastKeyless"],
                     "unspentNow": unspent_total(th) if len(th) == 64 else None,
                     "name": N.name(th, t["tree"]), "spentWith": t["with"], "samples": t["samples"][:4],
                     "treeBytes": len(t["tree"]) // 2 if t["tree"] else None,
                     "samplesChecked": len(ages), "samplesRentAge": sum(1 for x in ages if x >= RENT_PERIOD),
                     "script": (box or {}).get("ergoTreeScript", "")[:1500]})
    # templates a source says are keyless on some path but never spent without a key in the window
    seen = {x["templateHash"] for x in rows}
    extra = []
    for th, nm in N.KNOWN_KEYLESS.items():
        if th not in seen:
            extra.append({"templateHash": th, "name": nm, "keylessSpends": 0,
                          "signedSpends": r["templates"].get(th, {}).get("signed", 0),
                          "unspentNow": unspent_total(th)})
    save("f.json", {"from": a.lo, "to": a.hi, "explorer": X.EXPLORER, "keylessTxs": r["keylessTxs"],
                    "templates": rows, "neverSpentKeyless": extra,
                    "rent": {"txs": len(rent), "boxes": sum(x["boxes"] for x in rent),
                             "boxNanoErg": sum(x["boxNanoErg"] for x in rent),
                             "takenNanoErg": sum(x["boxNanoErg"] - x["recreatedNanoErg"] for x in rent),
                             "consumedWhole": sum(x["consumedWhole"] for x in rent),
                             "minerFeeNanoErg": sum(x["paid"].get("fee", 0) for x in rent),
                             "blocks": len({x["height"] for x in rent}),
                             "byMiner": rent_by_miner(rent, r["headers"]),
                             "byThird": rent_by_third(rent, a.lo, a.hi)},
                    "p2pkRent": {"spends": len(r["p2pkKeyless"]),
                                 "nanoErg": sum(x["value"] for x in r["p2pkKeyless"]),
                                 "blocks": len({x["height"] for x in r["p2pkKeyless"]})}, "requests": dict(X.stats)})


def rent_by_miner(rent, hdr):
    """Per block-miner address: blocks mined in the window, blocks carrying rent claims, ERG the claims took."""
    mined = collections.Counter(v["miner"] for v in hdr.values())
    took, blocks, last = collections.Counter(), collections.defaultdict(set), {}
    for x in rent:
        took[x["miner"]] += x["boxNanoErg"] - x["recreatedNanoErg"]
        blocks[x["miner"]].add(x["height"])
        last[x["miner"]] = max(last.get(x["miner"], 0), x["height"])
    return sorted([{"miner": m, "blocksMined": mined[m], "rentBlocks": len(blocks[m]), "takenNanoErg": took[m],
                    "lastRentBlock": last[m]} for m in took], key=lambda d: -d["takenNanoErg"])


def rent_by_third(rent, lo, hi):
    step = (hi - lo + 1) // 3
    out = []
    for k in range(3):
        a, b = lo + k * step, (hi if k == 2 else lo + (k + 1) * step - 1)
        S = [x for x in rent if a <= x["height"] <= b]
        out.append({"from": a, "to": b, "txs": len(S), "takenNanoErg": sum(x["boxNanoErg"] - x["recreatedNanoErg"]
                                                                           for x in S),
                    "miners": len({x["miner"] for x in S})})
    return out


# ---- line k --------------------------------------------------------------------------------------------------

def line_k(a):
    r = json.load(open(os.path.join(HERE, "census", "out", "scan-raw.json")))
    fees = {int(h): v for h, v in r["fees"].items()}
    hs = [h for h in range(a.lo, a.hi + 1)]
    assert all(h in fees for h in hs), "scan-raw.json does not cover the window"
    v = sorted(fees[h] for h in hs)
    n = len(v)
    pct = {p: v[min(n - 1, p * n // 100)] for p in (10, 25, 50, 75, 90, 95, 99)}
    edges = [0, 1_000_000, 1_100_001, 2_000_000, 5_000_000, 10_000_000, 50_000_000, 100_000_000, 1_000_000_000,
             10 ** 18]
    hist = []
    for lo_, hi_ in zip(edges, edges[1:]):
        hist.append({"fromNanoErg": lo_, "belowNanoErg": hi_, "blocks": sum(1 for x in v if lo_ <= x < hi_)})
    u1_sample = [fees[h] for h in hs if (h - a.lo) % 10 == 0]
    rewards = [r["headers"][str(h)]["minerReward"] for h in hs]
    top = sorted(hs, key=lambda h: -fees[h])[:10]
    save("k.json", {"from": a.lo, "to": a.hi, "blocks": n, "meanNanoErg": sum(v) // n,
                    "meanExact": sum(v) / n, "medianNanoErg": v[n // 2], "maxNanoErg": v[-1], "minNanoErg": v[0],
                    "zeroFeeBlocks": sum(1 for x in v if x == 0), "percentiles": pct, "histogram": hist,
                    "totalNanoErg": sum(v), "rewardMeanNanoErg": sum(rewards) // n,
                    "rewardPlusFeeMeanNanoErg": (sum(rewards) + sum(v)) // n,
                    "u1SampleMeanNanoErg": sum(u1_sample) // len(u1_sample),
                    "u1SampleMedianNanoErg": sorted(u1_sample)[len(u1_sample) // 2],
                    "u1SampleBlocks": len(u1_sample),
                    "txPerBlockMean": sum(r["txCount"][str(h)] for h in hs) / n,
                    "topBlocks": [{"height": h, "feeNanoErg": fees[h], "txs": r["txCount"][str(h)]} for h in top]})


# ---- line h --------------------------------------------------------------------------------------------------

T2T_POOL_TEMPLATE_HASH = "3c09deff3b5f49329149d18e02aab675ef6957bf6559a5c7dba817fee883fb3e"   # TokenPoolErgoTree
MIN_BOX = 1_000_000


def t2t_state(box):
    a = box["assets"]
    r4 = (box.get("additionalRegisters", {}).get("R4") or {}).get("renderedValue")
    if len(a) != 4 or r4 is None:
        return None
    return {"nft": a[0]["tokenId"], "erg": box["value"], "lp": a[1]["amount"], "x": a[2]["tokenId"],
            "X": a[2]["amount"], "y": a[3]["tokenId"], "Y": a[3]["amount"], "fee": int(r4)}


def template_timelines(U, th, parse, lo, tip):
    """Timelines (state at the start of each block) of every pool under template th, keyed by pool NFT: every
    transaction spending the template from lo to the tip, plus unspent boxes never spent since lo."""
    base = f"/transactions/byInputsScriptTemplateHash/{th}?sortDirection=asc"
    total = X.get(f"{base}&offset=0&limit=1", cache=False)["total"]
    start = U.asc_offset(base, total, "inclusionHeight", lo)
    txs = U.listing(base, start, "inclusionHeight", tip, 500)
    ev = []
    for tx in txs:
        for i in tx["inputs"]:
            if T.template_hash(i["ergoTree"]) != th:
                continue
            before = parse(i)
            if before is None:
                continue
            after = None
            for o in tx["outputs"]:
                s = parse(o) if o["ergoTree"] == i["ergoTree"] else None
                if s and s["nft"] == before["nft"]:
                    after = s
                    break
            ev.append((tx["inclusionHeight"], tx["index"], before, after, i.get("outputSettledAt"), tx["id"]))
    ev.sort(key=lambda e: (e[0], e[1]))
    tl, seen = collections.defaultdict(U.Timeline), set()
    for h, _, before, after, settled, _ in ev:
        n = before["nft"]
        if n not in seen:
            seen.add(n)
            tl[n].add(settled if settled is not None else lo - 1, before)
        tl[n].add(h, after)
    unspent, _ = unspent_boxes(th)
    for b in unspent:
        s = parse(b)
        if s and s["nft"] not in seen:
            seen.add(s["nft"])
            tl[s["nft"]].add(b["settlementHeight"], s)
    return tl, ev, unspent


def n2t_timelines(U, lo, tip):
    def parse(b):
        s = U.pool_state(b)
        return s and dict(s, x=None)
    return template_timelines(U, T.N2T_POOL_TEMPLATE_HASH, parse, lo, tip)


def ok_n2t(s):
    return s and s["Y"] > 1 and s["X"] > A_POOL_MIN


def line_h(a):
    import routes as R
    global A_POOL_MIN
    U = u1()
    A_POOL_MIN = U.A.POOL_MIN_VALUE
    tip = X.tip()
    ntl, nev, _ = n2t_timelines(U, a.lo, tip)
    ttl, tev, tun = template_timelines(U, T2T_POOL_TEMPLATE_HASH, t2t_state, a.lo, tip)
    log(f"N2T pools {len(ntl)} ({len(nev)} events), T2T pools {len(ttl)} ({len(tev)} events)")
    n2t_by_tok = collections.defaultdict(list)
    for n, t in ntl.items():
        s = next((x for x in reversed(t.s) if x), None)
        if s:
            n2t_by_tok[s["token"]].append(n)
    pools = []
    for n, t in ttl.items():
        s = next((x for x in reversed(t.s) if x), None)
        if not s:
            continue
        evs = [e for e in tev if e[2]["nft"] == n and a.lo <= e[0] <= a.hi]
        kinds = collections.Counter(("swap" if e[3] and e[3]["lp"] == e[2]["lp"] else "lp") for e in evs)
        pools.append({"nft": n, "x": s["x"], "y": s["y"], "X": s["X"], "Y": s["Y"], "erg": s["erg"], "fee": s["fee"],
                      "n2tPoolsX": len(n2t_by_tok.get(s["x"], [])), "n2tPoolsY": len(n2t_by_tok.get(s["y"], [])),
                      "eventsInWindow": dict(kinds), "unspent": any(b["assets"] and b["assets"][0]["tokenId"] == n for b in tun)})
    # triangular cycles ERG -> A -> B -> ERG through one T2T pool and two N2T pools, both directions
    res, rows = {}, []
    for p in pools:
        if not p["n2tPoolsX"] or not p["n2tPoolsY"]:
            continue
        n, ax, ay = p["nft"], n2t_by_tok[p["x"]], n2t_by_tok[p["y"]]
        pts = ttl[n].changes(a.lo, a.hi)
        for m in ax + ay:
            pts |= ntl[m].changes(a.lo, a.hi)

        def ev(h, n=n, ax=ax, ay=ay, cap=None):
            s = ttl[n].at(h)
            if not s or s["X"] <= 1 or s["Y"] <= 1:
                return 0, None
            best = (0, None)
            pt = (s["X"], s["Y"], s["fee"])
            for first, second, a_is_x in ((ax, ay, True), (ay, ax, False)):
                for m1 in first:
                    s1 = ntl[m1].at(h)
                    if not ok_n2t(s1):
                        continue
                    for m3 in second:
                        s3 = ntl[m3].at(h)
                        if not ok_n2t(s3):
                            continue
                        r = R.cycle((s1["X"], s1["Y"], s1["fee"]), pt, a_is_x, (s3["X"], s3["Y"], s3["fee"]),
                                    cap or s1["X"] * 4)
                        if r and r[0] > best[0]:
                            best = (r[0], {"buy": m1, "t2t": n, "sell": m3, "aIsX": a_is_x, "capital": r[1],
                                           "a": r[2], "b": r[3], "ergOut": r[4],
                                           "fees": (s1["fee"], s["fee"], s3["fee"])})
            return best

        segs = U.run_segments(pts, a.lo, a.hi, ev)
        key = f"{p['x'][:8]}/{p['y'][:8]}:{n[:8]}"
        res[key] = U.summarize(segs, a.lo, a.hi)
        caps = sorted(s[3]["capital"] for s in segs if s[2] >= MIN_BOX)
        res[key]["capitalMedianNanoErg"] = caps[len(caps) // 2] if caps else 0
        res[key]["pool"] = p
        # the same, capped at the test wallet (line j reads this)
        segs10 = U.run_segments(pts, a.lo, a.hi, lambda h: ev(h, cap=10 * 10 ** 9))
        res[key]["cap10"] = U.summarize(segs10, a.lo, a.hi)
        for s in segs:
            if s[2] >= MIN_BOX:
                rows.append([s[0], s[1], key, s[3]["buy"], s[3]["sell"], s[3]["aIsX"], s[3]["capital"], s[2]])
    # U1 line c over N2T pools again, for the record of what the larger set adds (nothing new to N2T)
    save("h.json", {"from": a.lo, "to": a.hi, "explorerTip": tip, "t2tTemplateHash": T2T_POOL_TEMPLATE_HASH,
                    "t2tPools": pools, "t2tEventsLoToTip": len(tev), "n2tPools": len(ntl),
                    "cycles": res, "requests": dict(X.stats)})
    U.write_csv(os.path.join(OUT, "u1b-h-cycles-states.csv"),
                ["fromHeight", "toHeight", "pair", "buyPoolNft", "sellPoolNft", "aIsX", "capitalNanoErg",
                 "profitNanoErg"], rows)


# ---- line g --------------------------------------------------------------------------------------------------

OFFERS = {   # template hash -> kind; sources in CENSUS-U1B.md line (g)
    T.BABEL_TEMPLATE_HASH: "babel",
    "66248bc588ed2f5ac4dbab113083ce6982f69958c8bb654c5830e304329f2746": "otg",
    "106e19116fd32130f147661b1b954e76c7605c14e6b11ad0549d60cb87197e20": "kushti",
    "a16dfa919d97be53d3e1ed8ba769d189b96a05e3de9bcbdac6a6ab6f311a5479": "machina-limit",
    "a68900b67ff5d74f74e7907aca83680adfc8ba01c1925430339d9e4c3f5dd0a3": "machina-grid",
}
OFFER_BOXES = []
KEEP = 1_000_000   # nanoERG left in a recreated offer box (the Babel convention; [inferred] enough for each kind)


def parse_offer(kind, b):
    """Normalized offer: list of legs, each ('bid', price, capERG) continuous, ('ask', price, capTokens)
    continuous, or ('lots', [(amount, isBuy, buyTotal, sellTotal)]) discrete; plus the token."""
    reg = lambda r: (b["additionalRegisters"].get(r) or {}).get("renderedValue")  # noqa: E731
    tok0 = b["assets"][0] if b["assets"] else None
    held = tok0["amount"] if tok0 else 0
    if kind == "babel":
        return T.babel_token(b["ergoTree"]), [("bid", int(reg("R5")), b["value"] - KEEP)]
    if kind == "otg":
        o = T.grid_orders(b["additionalRegisters"]["R5"]["serializedValue"])
        return reg("R6"), [("lots", o, b["value"] - KEEP, held)]
    if kind == "kushti":
        if None in (reg("R5"), reg("R6"), reg("R7"), reg("R8")):
            raise ValueError("missing R5..R8: not fillable")
        tok = T.constant_coll_bytes(b["ergoTree"], 8)
        size, price = int(reg("R7")), int(reg("R5"))
        if reg("R6") == "true":    # buy: the box takes exactly R7 tokens, gives at most R7*R5 ERG
            return tok, [("lots", [(size, True, min(size * price, b["value"] - KEEP), 0)], b["value"] - KEEP, held)]
        return tok, [("lots", [(held, False, 0, size * price)], b["value"], held)]   # sell: all its tokens
    if kind == "machina-limit":
        if reg("R6") not in ("true", "false"):
            # the script reads SELF.R6[Boolean].get on every path: a box without R6 cannot be filled
            raise ValueError("no R6[Boolean]: not fillable")
        tok = T.constant_coll_bytes(b["ergoTree"], 0)
        price = int(reg("R5"))
        if reg("R6") == "true":    # sell: tokens out, ERG in >= tokens * R5
            return tok, [("ask", price, held)]
        return tok, [("bid", price, b["value"] - KEEP)]
    if kind == "machina-grid":
        if reg("R5") is None:
            raise ValueError("no R5: not fillable")
        tok = T.constant_coll_bytes(b["ergoTree"], 0)
        ask, bid = json.loads(reg("R5"))
        return tok, [("ask", ask, held), ("bid", bid, b["value"] - KEEP)]
    return None, []


def take_vs_pool(leg, pool):
    """Best one-transaction take of one offer leg against N2T pool (X, Y, fee): (profit, ergIntoPool or
    tokensIntoPool, tokens, detail) or None. Integer rules of census/amm.py; the offer side rounds against the
    taker (it pays at most tokens*price, is paid at least tokens*price)."""
    X0, Y0, fee = pool
    if leg[0] == "bid":
        r = A.babel_vs_pool(X0, Y0, fee, leg[1], leg[2]) if leg[1] > 0 and leg[2] > 0 else None
        return r and (r[0], r[1], r[2], {"side": "bid", "price": leg[1], "ergFromOffer": r[3]})
    if leg[0] == "ask":
        price, cap = leg[1], min(leg[2], 10 ** 15)
        if cap <= 0:
            return None
        f = lambda t: A.pool_erg_out(X0, Y0, fee, t) - t * price  # noqa: E731
        t, p = A.argmax_int(f, 1, cap)
        return (p, t * price, t, {"side": "ask", "price": price, "ergToPool": A.pool_erg_out(X0, Y0, fee, t)}) \
            if t and p > 0 else None
    # discrete lots: the best prefix of the buy lots by unit price (high first), or of the sell lots (low first)
    lots, erg_cap, tok_cap = leg[1], leg[2], leg[3]
    best = None
    buys = sorted([x for x in lots if x[1]], key=lambda x: -x[2] / max(x[0], 1))
    sa = sb = 0
    for k, x in enumerate(buys, 1):
        sa += x[0]; sb += x[2]
        if sb > erg_cap or sa >= Y0:
            break
        p = sb - A.pool_erg_in_for(X0, Y0, fee, sa)
        if p > 0 and (best is None or p > best[0]):
            best = (p, A.pool_erg_in_for(X0, Y0, fee, sa), sa, {"side": "box buys", "lots": k, "ergFromOffer": sb})
    sells = sorted([x for x in lots if not x[1]], key=lambda x: x[3] / max(x[0], 1))
    sa = ss = 0
    for k, x in enumerate(sells, 1):
        sa += x[0]; ss += x[3]
        if sa > tok_cap:
            break
        p = A.pool_erg_out(X0, Y0, fee, sa) - ss
        if p > 0 and (best is None or p > best[0]):
            best = (p, ss, sa, {"side": "box sells", "lots": k, "ergToPool": A.pool_erg_out(X0, Y0, fee, sa)})
    return best


def line_g(a):
    global A
    U = u1()
    A = U.A
    pools, _ = unspent_boxes(T.N2T_POOL_TEMPLATE_HASH)
    by_tok = collections.defaultdict(list)
    for b in pools:
        s = U.pool_state(b)
        if s and s["Y"] > 1 and s["X"] > A.POOL_MIN_VALUE:
            by_tok[s["token"]].append((b["boxId"], s))
    tip = X.tip()
    rows, counts = [], {}
    for th, kind in OFFERS.items():
        boxes, total = unspent_boxes(th)
        OFFER_BOXES.extend(boxes)
        counts[kind] = total
        for b in boxes:
            try:
                tok, legs = parse_offer(kind, b)
            except (TypeError, ValueError, KeyError, AttributeError) as e:   # malformed box (no registers)
                rows.append({"kind": kind, "boxId": b["boxId"], "valueNanoErg": b["value"], "unparsed": repr(e)[:80],
                             "best": None})
                continue
            best = None
            for leg in legs:
                for pid, s in by_tok.get(tok, []):
                    r = take_vs_pool(leg, (s["X"], s["Y"], s["fee"]))
                    if r and (best is None or r[0] > best["profitNanoErg"]):
                        best = {"profitNanoErg": r[0], "in": r[1], "tokens": r[2], "detail": r[3], "poolBox": pid,
                                "poolNft": s["nft"], "poolX": s["X"], "poolY": s["Y"], "poolFee": s["fee"]}
            summ = []
            for leg in legs:
                if leg[0] in ("bid", "ask"):
                    summ.append({"side": leg[0], "price": leg[1], "cap": leg[2]})
                else:
                    lots = leg[1] or []
                    summ.append({"side": "lots", "n": len(lots), "buyLots": sum(1 for x in lots if x[1]),
                                 "sellLots": sum(1 for x in lots if not x[1]),
                                 "bestBuyUnit": max((x[2] / x[0] for x in lots if x[1] and x[0]), default=None),
                                 "bestSellUnit": min((x[3] / x[0] for x in lots if not x[1] and x[0]), default=None)})
            mid = None
            if by_tok.get(tok):
                s = max((s for _, s in by_tok[tok]), key=lambda s: s["X"])
                mid = s["X"] / s["Y"]
            rows.append({"kind": kind, "boxId": b["boxId"], "token": tok, "valueNanoErg": b["value"],
                         "tokensHeld": b["assets"][0]["amount"] if b["assets"] else 0,
                         "created": b["settlementHeight"], "legs": summ, "n2tPools": len(by_tok.get(tok, [])),
                         "deepestPoolNanoErgPerUnit": mid, "best": best})
    rows.sort(key=lambda r: -(r["best"]["profitNanoErg"] if r["best"] else 0))
    seq = sequential(rows, by_tok, U)
    save("g.json", {"atTip": tip, "explorer": X.EXPLORER, "unspent": counts, "n2tPoolsLive": len(pools),
                    "sequential": seq, "offers": rows, "requests": dict(X.stats)})


def sequential(rows, by_tok, U):
    """Every profitable offer taken in turn against the pools as each take leaves them: the best remaining
    (offer, pool) first, the pool state updated by the integer swap, until nothing pays MIN_BOX. Per row a
    separate transaction (each pool takes OUTPUTS(0)); takes on one pool may also share one transaction."""
    pools = {s["nft"]: dict(s, box=pid) for t in by_tok.values() for pid, s in t}
    legs = {}
    for r in rows:
        if r.get("best") is None:
            continue
        b = [x for x in OFFER_BOXES if x["boxId"] == r["boxId"]][0]
        legs[r["boxId"]] = (r["kind"], r["token"], parse_offer(r["kind"], b)[1])
    takes, total = [], 0
    while True:
        best = None
        for bid, (kind, tok, lg) in legs.items():
            for leg in lg:
                for p in (x for x in pools.values() if x["token"] == tok):
                    r = take_vs_pool(leg, (p["X"], p["Y"], p["fee"]))
                    if r and r[0] >= MIN_BOX and (best is None or r[0] > best[0]):
                        best = (r[0], bid, kind, tok, p["nft"], r)
        if best is None:
            break
        p, bid, kind, tok, nft, r = best
        ps = pools[nft]
        if r[3].get("side") in ("bid", "box buys"):
            ps["X"] += r[1]; ps["Y"] -= r[2]
        else:
            ps["X"] -= r[3]["ergToPool"]; ps["Y"] += r[2]
        takes.append({"offerBox": bid, "kind": kind, "token": tok, "poolNft": nft, "profitNanoErg": p,
                      "tokens": r[2], "in": r[1], "detail": r[3]})
        total += p
        del legs[bid]
    by = collections.defaultdict(lambda: [0, 0])
    for t in takes:
        by[t["token"]][0] += t["profitNanoErg"]; by[t["token"]][1] += 1
    return {"totalNanoErg": total, "takes": takes, "byToken": {k: {"nanoErg": v[0], "takes": v[1]}
                                                                 for k, v in by.items()}}


# ---- line i --------------------------------------------------------------------------------------------------

def full_hash(prefix):
    import names as N
    hs = [k for k in N.catalog() if k.startswith(prefix)] + [k for k in N.LABELS if k.startswith(prefix)]
    assert len(set(hs)) == 1, (prefix, hs)
    return hs[0]


# (group, name, template-hash prefix): the unspent boxes of each are counted at the tip; sources in CENSUS-U1B.md
I_TEMPLATES = [
    ("executor", "ErgoDEX N2T SwapSell v1 (nativeFee)", "36d1944f"),
    ("executor", "ErgoDEX N2T SwapBuy v1 (nativeFee)", "be1312f7"),
    ("executor", "ErgoDEX N2T Deposit v1", "ff225395"),
    ("executor", "ErgoDEX N2T Redeem v1", "1f1b05c2"),
    ("executor", "ErgoDEX N2T SwapSell v3 (spfFee)", "e661fcbb"),
    ("executor", "ErgoDEX N2T SwapBuy v3 (spfFee)", "8d1fd21c"),
    ("executor", "ErgoDEX N2T Deposit v3", "bd026b0f"),
    ("executor", "ErgoDEX N2T Redeem v3", "bc3e2c2c"),
    ("executor", "ErgoDEX N2T SwapSell multiAddressV2", "6fae4e76"),
    ("executor", "ErgoDEX N2T SwapBuy multiAddressV2", "84af94fe"),
    ("executor", "ErgoDEX T2T Swap v1", "36f6a018"),
    ("executor", "ErgoDEX T2T Deposit v1", "b51efb4e"),
    ("executor", "ErgoDEX T2T Redeem v1", "4149cdf2"),
    ("executor", "ErgoDEX T2T Swap v3", "9f582375"),
    ("executor", "ErgoDEX T2T Deposit v3", "3c2e8c1c"),
    ("executor", "ErgoDEX T2T Redeem v3", "19aa1949"),
    ("executor", "ErgoDEX T2T Swap v2 (multiAddress)", "d7d4d43a"),
    ("executor", "LithosDex SwapSell order", "b4fd5d9b"),
    ("executor", "LithosDex SwapBuy order", "7122d569"),
    ("executor", "LithosDex Deposit order", "28027ccf"),
    ("executor", "LithosDex Redeem order", "d67c6f6e"),
    ("executor", "Spectrum LM pool (simple, pays execFee)", "f9c22579"),
    ("executor", "Spectrum LM pool self-hosted (managed)", "728bc5b8"),
    ("executor", "Spectrum LM staking bundle / deposit proxy", "e82488a7"),
    ("executor", "Spectrum LM redeem proxy", "f624989a"),
    ("liquidation", "Duckpools collateral (ERG pool)", "5d5dcacf"),
    ("liquidation", "Duckpools collateral (token pools)", "db697243"),
    ("liquidation", "SigmaFi ERG bond", "44830db1"),
    ("bank", "hodlERG bank", "8b5dac35"),
    ("auction", "ErgoAuctionHouse auction", "3d578e5c"),
    ("auction", "SkyHarbor ERG sale", "f9f76671"),
    ("auction", "SkyHarbor SigUSD sale", "8bd9b67b"),
    ("pool", "Dexy LP (SDK n2dexyGOLD, testnet ids)", "2cf12e36"),
    ("pool", "LithosDex liquidity pool", "2de640e3"),
]


def consts(box):
    """The explorer's ergoTreeConstants text as {index: text}."""
    out = {}
    for ln in box.get("ergoTreeConstants", "").split("\n"):
        k, _, v = ln.partition(": ")
        if k.isdigit():
            out[int(k)] = v
    return out


def coll_hex(v):
    return bytes(int(x) & 0xFF for x in v[5:-1].split(",")).hex()


def swapsell_v1(boxes):
    """ErgoDEX N2T SwapSell v1 (ergo-dex contracts/amm/cfmm/v1/n2t/SwapSell.sc:16-54) against its pool now.
    Deployed constants (positions read off the template; checked on every box by type): 8 PoolNFT, 9 QuoteId,
    10 MinQuoteAmount, 11/12 DexFeePerToken num/denom, 14 FeeNum, 17 BaseAmount. The executor gives the pool
    BaseAmount ERG, the redeemer gets quote >= MinQuote at OUTPUTS(1), the executor keeps at most
    quote * num / denom (:34), the miner fee coming out of that."""
    U = u1()
    pools = {}
    for b in unspent_boxes(T.N2T_POOL_TEMPLATE_HASH)[0]:
        s = U.pool_state(b)
        if s:
            pools[s["nft"]] = s
    out = []
    for b in boxes:
        c = consts(b)
        nft, quote_id = coll_hex(c[8]), coll_hex(c[9])
        min_q, num, den, fee, base = int(c[10]), int(c[11]), int(c[12]), int(c[14]), int(c[17])
        p = pools.get(nft)
        if p is None or p["token"] != quote_id:
            out.append({"box": b["boxId"], "valueNanoErg": b["value"], "pool": nft, "status": "pool not live"})
            continue
        q = (p["Y"] * base * fee) // (p["X"] * 1000 + base * fee)
        # the redeemer's ERG must be >= value - q*num/den - base (:34): the executor keeps at most q*num/den
        ex_fee = min(q * num // den, b["value"] - base) - TX_FEE if q >= min_q else 0
        out.append({"box": b["boxId"], "valueNanoErg": b["value"], "baseNanoErg": base, "pool": nft,
                    "minQuote": min_q, "quoteNow": q, "executable": q >= min_q,
                    "shortfallPct": None if q >= min_q else round(100 * (min_q - q) / min_q, 2),
                    "executorNanoErg": ex_fee})
    return out


def line_i(a):
    tip = X.tip()
    rows = []
    for group, name, pre in I_TEMPLATES:
        th = full_hash(pre)
        boxes, total = unspent_boxes(th, cap=3000)
        ages = sorted(tip - b["settlementHeight"] for b in boxes)
        row = {"group": group, "name": name, "templateHash": th, "unspent": total,
               "nanoErg": sum(b["value"] for b in boxes), "fetched": len(boxes),
               "olderThan1Block": sum(1 for x in ages if x > 1), "olderThan720": sum(1 for x in ages if x > 720),
               "ageMedianBlocks": ages[len(ages) // 2] if ages else None,
               "sample": [b["boxId"] for b in boxes[:3]]}
        if pre == "44830db1":   # SigmaFi bond: keyless liquidation to the lender once HEIGHT >= R7
            r7 = [int((b["additionalRegisters"].get("R7") or {}).get("renderedValue") or 0) for b in boxes]
            row["maturedNow"] = sum(1 for x in r7 if 0 < x <= tip)
            row["maturedNanoErg"] = sum(b["value"] for b, x in zip(boxes, r7) if 0 < x <= tip)
        if pre == "36d1944f":
            row["executable"] = swapsell_v1(boxes)
        rows.append(row)
    save("i.json", {"atTip": tip, "explorer": X.EXPLORER, "templates": rows, "requests": dict(X.stats)})


def line_o(a):
    """Line (i), oracle-referenced gaps: SigUSD N2T pools against the ERG/USD oracle pool box (rate = R4 / 100
    nanoERG per SigUSD unit, AgeUSD.scala:43), block-weighted, against each pool's fee."""
    U = u1()
    tip = X.tip()
    ntl, _, _ = n2t_timelines(U, a.lo, tip)
    oracle = U.nft_timeline(U.ORACLE_NFT, a.lo, a.hi)
    pools = [n for n, t in ntl.items() if any(s and s["token"] == U.SIGUSD for s in t.s)]
    res = {}
    for n in pools:
        pts = sorted({a.lo} | ntl[n].changes(a.lo, a.hi) | oracle.changes(a.lo, a.hi))
        gaps, depth = [], []
        for k, c in enumerate(pts):
            end = pts[k + 1] - 1 if k + 1 < len(pts) else a.hi
            s, ob = ntl[n].at(c), oracle.at(c)
            if not s or not ob or s["Y"] <= 1:
                continue
            rate = int(U.reg(ob, "R4")) / 100
            g = (s["X"] / s["Y"]) / rate - 1
            gaps.append((abs(g), end - c + 1, g, s["fee"]))
            depth.append(s["X"])
        if not gaps:
            continue
        tot = sum(w for _, w, _, _ in gaps)
        srt = sorted(gaps)
        acc, med = 0, None
        for g, w, _, _ in srt:
            acc += w
            if acc >= tot / 2:
                med = g
                break
        fee = gaps[-1][3]
        res[n] = {"fee": fee, "blocks": tot, "medianAbsGap": med,
                  "meanAbsGap": sum(g * w for g, w, _, _ in gaps) / tot,
                  "meanSignedGap": sum(sg * w for _, w, sg, _ in gaps) / tot,
                  "blocksPoolAboveOracleBeyondFee": sum(w for _, w, sg, f in gaps if sg > (1000 - f) / 1000),
                  "blocksGapAboveFee": sum(w for g, w, _, _ in gaps if g > (1000 - fee) / 1000),
                  "maxGap": max(g for g, _, _, _ in gaps), "ergDepthMaxNanoErg": max(depth)}
    save("o.json", {"from": a.lo, "to": a.hi, "pools": res, "oracleBoxes": len(oracle.h)})


# ---- line j --------------------------------------------------------------------------------------------------

CAP = 10 * 10 ** 9            # the test wallet, about 10 ERG after the four Babel takes
TX_FEE = 1_100_000            # miner fee per transaction, as the SK-049 takes paid


def moved_next(tl, lo, hi):
    """Blocks h in [lo, hi] where the entity changes in h or h+1: the second leg, sent with the first in block h,
    may land in h or h+1 and find the pool moved."""
    ch = tl.changes(lo, hi + 1)
    return {h for h in range(lo, hi + 1) if h in ch or h + 1 in ch}


def line_j(a):
    import capped as C
    U = u1()
    global A_POOL_MIN
    A_POOL_MIN = U.A.POOL_MIN_VALUE
    tip = X.tip()
    ntl, _, _ = n2t_timelines(U, a.lo, tip)
    by_tok = collections.defaultdict(list)
    for n, t in ntl.items():
        s = next((x for x in reversed(t.s) if x), None)
        if s:
            by_tok[s["token"]].append(n)
    moved = {}

    def mv(n):
        if n not in moved:
            moved[n] = moved_next(ntl[n], a.lo, a.hi)
        return moved[n]

    out = {"c": {}, "b": {}}
    # U1 line c, capped
    for tok, pools in by_tok.items():
        if len(pools) < 2:
            continue
        pts = set()
        for n in pools:
            pts |= ntl[n].changes(a.lo, a.hi)

        def ev(h, pools=pools):
            st = {n: ntl[n].at(h) for n in pools}
            st = {n: s for n, s in st.items() if ok_n2t(s)}
            best = (0, None)
            for x in st:
                for y in st:
                    if x == y:
                        continue
                    r = C.pool_vs_pool((st[x]["X"], st[x]["Y"], st[x]["fee"]), (st[y]["X"], st[y]["Y"], st[y]["fee"]),
                                       CAP)
                    if r and r[0] - 2 * TX_FEE > best[0]:
                        best = (r[0] - 2 * TX_FEE, {"buy": x, "sell": y, "capital": r[1], "T": r[2],
                                                     "gross": r[0], "sellErgForT": r[0] + r[1]})
            return best

        segs = U.run_segments(pts, a.lo, a.hi, ev)
        sm = U.summarize(segs, a.lo, a.hi)
        if not sm["statesOpen"]:
            continue
        open_blocks = [(s, h) for s in segs if s[2] >= MIN_BOX for h in range(s[0], s[1] + 1)]
        risky = sum(1 for s, h in open_blocks if h in mv(s[3]["sell"]))
        sm["openBlocksSellPoolMovedNext"] = risky
        sm["riskShare"] = risky / len(open_blocks)
        out["c"][U.NAMES.get(tok, tok[:8])] = sm
    # U1 line b, capped
    bank, oracle = U.nft_timeline(U.BANK_NFT, a.lo, a.hi), U.nft_timeline(U.ORACLE_NFT, a.lo, a.hi)
    for coin, tok in (("sc", U.SIGUSD), ("rc", U.SIGRSV)):
        pools = by_tok.get(tok, [])
        pts = bank.changes(a.lo, a.hi) | oracle.changes(a.lo, a.hi)
        for n in pools:
            pts |= ntl[n].changes(a.lo, a.hi)

        def ev(h, coin=coin, pools=pools):
            bb, ob = bank.at(h), oracle.at(h)
            if bb is None or ob is None or U.reg(ob, "R4") is None:
                return 0, None
            bk = U.A.Bank(bb["value"], int(U.reg(bb, "R4")), int(U.reg(bb, "R5")), int(U.reg(ob, "R4")))
            best = (0, None)
            for n in pools:
                s = ntl[n].at(h)
                if not ok_n2t(s):
                    continue
                r = C.bank_vs_pool(bk, coin, (s["X"], s["Y"], s["fee"]), CAP)
                if r and r[1] - 2 * TX_FEE > best[0]:
                    best = (r[1] - 2 * TX_FEE, {"pool": n, "dir": r[0], "capital": r[2], "units": r[3], "gross": r[1]})
            return best

        segs = U.run_segments(pts, a.lo, a.hi, ev)
        sm = U.summarize(segs, a.lo, a.hi)
        if sm["statesOpen"]:
            # second leg: the pool for mint->pool, the bank (and its oracle) for pool->redeem
            bmv = moved_next(bank, a.lo, a.hi) | moved_next(oracle, a.lo, a.hi)
            ob = [(s, h) for s in segs if s[2] >= MIN_BOX for h in range(s[0], s[1] + 1)]
            risky = sum(1 for s, h in ob if h in (mv(s[3]["pool"]) if s[3]["dir"] == "mint->pool" else bmv))
            sm["openBlocksSecondLegMovedNext"] = risky
            sm["riskShare"] = risky / len(ob)
        out["b"][coin] = sm
    # line h's triangles, capped there (h.json cycles[*].cap10), net of three fees
    try:
        h = load("h.json")
        out["h"] = {k: {"cap10": v["cap10"], "net3txBest": v["cap10"]["maxNanoErg"] - 3 * TX_FEE}
                    for k, v in h["cycles"].items() if v["cap10"]["statesOpen"]}
    except FileNotFoundError:
        out["h"] = None
    save("j.json", {"from": a.lo, "to": a.hi, "capNanoErg": CAP, "txFeeNanoErg": TX_FEE, **out,
                    "requests": dict(X.stats)})


def line_jnow(a):
    """Line (j) at the tip: every capital take open now, capped at CAP, net of its transactions' fees, with the
    boxes, the legs, and what is left after leg 1 if leg 2 fails (the token held and its value sold back into
    the pool leg 1 bought from, after leg 1)."""
    import capped as C
    import routes as R
    U = u1()
    global A_POOL_MIN
    A_POOL_MIN = U.A.POOL_MIN_VALUE
    tip = X.tip()
    n2t = {}
    for b in unspent_boxes(T.N2T_POOL_TEMPLATE_HASH)[0]:
        s = U.pool_state(b)
        if ok_n2t(s):
            n2t[s["nft"]] = dict(s, box=b["boxId"])
    by_tok = collections.defaultdict(list)
    for s in n2t.values():
        by_tok[s["token"]].append(s)
    takes = []
    for tok, ps in by_tok.items():
        for x in ps:
            for y in ps:
                if x is y:
                    continue
                r = C.pool_vs_pool((x["X"], x["Y"], x["fee"]), (y["X"], y["Y"], y["fee"]), CAP)
                if not r or r[0] - 2 * TX_FEE <= 0:
                    continue
                p, cap, t = r
                back = A.pool_erg_out(x["X"] + cap, x["Y"] - t, x["fee"], t)
                takes.append({"line": "c pool-pool", "token": tok, "txs": 2, "netNanoErg": p - 2 * TX_FEE,
                              "capitalNanoErg": cap, "legs": [
                                  {"tx": 1, "pool": x["box"], "nft": x["nft"], "ergIn": cap, "tokensOut": t},
                                  {"tx": 2, "pool": y["box"], "nft": y["nft"], "tokensIn": t, "ergOut": p + cap}],
                              "ifLeg2Fails": {"held": t, "token": tok, "sellBackNanoErg": back,
                                              "lossIfSoldBackNanoErg": cap + TX_FEE - back}})
    # bank against pool
    bank = X.get(f"/boxes/unspent/byTokenId/{U.BANK_NFT}?offset=0&limit=1", cache=False)["items"][0]
    orc = X.get(f"/boxes/unspent/byTokenId/{U.ORACLE_NFT}?offset=0&limit=1", cache=False)["items"][0]
    bk = A.Bank(bank["value"], int(U.reg(bank, "R4")), int(U.reg(bank, "R5")), int(U.reg(orc, "R4")))
    for coin, tok in (("sc", U.SIGUSD), ("rc", U.SIGRSV)):
        for s in by_tok.get(tok, []):
            r = C.bank_vs_pool(bk, coin, (s["X"], s["Y"], s["fee"]), CAP)
            if r and r[1] - 2 * TX_FEE > 0:
                takes.append({"line": "b bank-pool", "token": tok, "txs": 2, "netNanoErg": r[1] - 2 * TX_FEE,
                              "capitalNanoErg": r[2], "direction": r[0], "units": r[3], "pool": s["box"],
                              "bankBox": bank["boxId"], "oracleBox": orc["boxId"]})
    # triangles through T2T pools
    for b in unspent_boxes(T2T_POOL_TEMPLATE_HASH)[0]:
        s = t2t_state(b)
        if not s or s["X"] <= 1 or s["Y"] <= 1:
            continue
        for first, second, a_is_x in ((s["x"], s["y"], True), (s["y"], s["x"], False)):
            for p1 in by_tok.get(first, []):
                for p3 in by_tok.get(second, []):
                    r = R.cycle((p1["X"], p1["Y"], p1["fee"]), (s["X"], s["Y"], s["fee"]), a_is_x,
                                (p3["X"], p3["Y"], p3["fee"]), CAP)
                    if not r or r[0] - 3 * TX_FEE <= 0:
                        continue
                    p, x, ta, tb, out = r
                    back = A.pool_erg_out(p1["X"] + x, p1["Y"] - ta, p1["fee"], ta)
                    takes.append({"line": "h triangle", "token": f"{first}/{second}", "txs": 3,
                                  "netNanoErg": p - 3 * TX_FEE, "capitalNanoErg": x, "legs": [
                                      {"tx": 1, "pool": p1["box"], "ergIn": x, "tokensOut": ta},
                                      {"tx": 2, "pool": b["boxId"], "t2t": s["nft"], "tokensIn": ta, "tokensOut": tb},
                                      {"tx": 3, "pool": p3["box"], "tokensIn": tb, "ergOut": out}],
                                  "ifLeg2Fails": {"held": ta, "token": first, "sellBackNanoErg": back,
                                                  "lossIfSoldBackNanoErg": x + TX_FEE - back}})
    takes.sort(key=lambda t: -t["netNanoErg"])
    save("jnow.json", {"atTip": tip, "capNanoErg": CAP, "txFeeNanoErg": TX_FEE, "takes": takes,
                       "requests": dict(X.stats)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("line")
    ap.add_argument("--from", dest="lo", type=int, default=LO)
    ap.add_argument("--to", dest="hi", type=int, default=HI)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    log(f"U1b line {a.line}, window {a.lo}..{a.hi}, {X.EXPLORER}, {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    globals()[f"line_{a.line}"](a)


if __name__ == "__main__":
    main()
