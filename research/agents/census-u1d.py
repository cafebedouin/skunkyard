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
ORACLE_FROM = 0               # all of it: the three oracle-pool addresses (below) cover 449,441 to the tip
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
    orc = oracle_rows()
    return bank, orc, rsv, usd


# The ERG/USD oracle pool box alternates between two contracts (live epoch, epoch preparation). Its token chain is
# 286,436 boxes and the mirror serves that listing at 10-30 s a page, so the oracle is read by the two addresses
# instead (2-4 s a page), every page of both, and cut to the window. Pages of /boxes/byAddress are not in height
# order; the rows are sorted, and chain.check shows whether the two addresses cover the window.
ORACLE_ADDRESSES = [
    "NTkuk55NdwCXkF1e2nCABxq7bHjtinX3wH13zYPZ6qYT71dCoZBe1gZkh9FAr7GeHo2EpFoibzpNQmoi89atUjKRrhZEYrTapdtXrWU4kq319oY7BEWmtmRU9cMohX69XMuxJjJP5hRM8WQLfFnffbjshhEP3ck9CKVEkFRw1JDYkqVke2JVqoMED5yxLVkScbBUiJJLWq9BSbE1JJmmreNVskmWNxWE6V7ksKPxFMoqh1SVePh3UWAaBgGQRZ7TWf4dTBF5KMVHmRXzmQqEu2Fz2yeSLy23sM3pfqa78VuvoFHnTFXYFFxn3DNttxwq3EU3Zv25SmgrWjLKiZjFcEcqGgH6DJ9FZ1DfucVtTXwyDJutY3ksUBaEStRxoUQyRu4EhDobixL3PUWRcxaRJ8JKA9b64ALErGepRHkAoVmS8DaE6VbroskyMuhkTo7LbrzhTyJbqKurEzoEfhYxus7bMpLTePgKcktgRRyB7MjVxjSpxWzZedvzbjzZaHLZLkWZESk1WtdM25My33wtVLNXiTvficEUbjA23sNd24pv1YQ72nY1aqUHa2",
    "EfS5abyDe4vKFrJ48K5HnwTqa1ksn238bWFPe84bzVvCGvK1h2B7sgWLETtQuWwzVdBaoRZ1Hcz1i9w5sa4bkSPJMrkFSmcpLeKUEseNYQn3x57xGttnWFjXkLsyE7EDQuga6ic28tMpPrVokJ2d8ZHQhjddRgwxMfhcwvVtoTqjLbDc3YKJLAetd2DcaCWJB6XzHCM8ezDFpCWVVrFeu4SYGSoGJbgPDRvEAcJEN4qu1RwsmZ1MzBfWF2jBJLagWqu2GvevuDG5oTtJrkqwCHRaAshfoM2mQnjLBsajjPN426t3aRZVJVRHm8apmZstnh92kYBVMujvLA1BkR2tqTfYLtmX6ChFSMXSYejkkCQoLdog59iD66oEzAZtg9ZowqDCjfT8G8YLVpEkVd23QH2LhFtEie3R4etCuvzCSyC4UmMmLbvrnUg4LfuP6xv6jckLGH8HkNWeTuuqf2UmVCQfhMMndBciTXF2KfrPCrzmDXw",
    # the epoch-preparation contract before 1,460,747 (same template, other constants), found from the breaks
    "EfS5abyDe4vKFrJ48K5HnwTqa1ksn238bWFPe84bzVvCGvK1h2B7sgWLETtQuWwzVdBaoRZ1HcyzddrxLcsoM5YEy4UnqcLqMU1MDca1kLw9xbazAM6Awo9y6UVWTkQcS97mYkhkmx2Tewg3JntMgzfLWz5mACiEJEv7potayvk6awmLWS36sJMfXWgnEfNiqTyXNiPzt466cgot3GLcEsYXxKzLXyJ9EfvXpjzC2abTMzVSf1e17BHre4zZvDoAeTqr4igV3ubv2PtJjntvF2ibrDLmwwAyANEhw1yt8C8fCidkf3MAoPE6T53hX3Eb2mp3Xofmtrn4qVgmhNonnV8ekWZWvBTxYiNP8Vu5nc6RMDBv7P1c5rRc3tnDMRh2dUcDD7USyoB9YcvioMfAZGMNfLjWqgYu9Ygw2FokGBPThyWrKQ5nkLJvief1eQJg4wZXKdXWAR7VxwNftdZjPCHcmwn6ByRHZo9kb4Emv3rjfZE",
]


def oracle_rows():
    rows, seen = [], set()
    for addr in ORACLE_ADDRESSES:
        for r in C.fetch(ORACLE_NFT, address=addr):
            if r["hasNft"] and r["h"] >= ORACLE_FROM and r["box"] not in seen:
                seen.add(r["box"])
                rows.append(r)
    rows.sort(key=lambda r: (r["h"], r["gix"]))
    # The address listing pages in an unstable order and misses some boxes (1,502 gaps on the first read). Fill each
    # gap from the transaction that spent the box before it: its output holding the NFT is the missing box, read
    # whole by id. Repeat until the chain is unbroken or no gap can be filled.
    import txs as TX
    for _ in range(8):
        br, _rep = C.check(rows)
        gaps = [b["spent"] for b in br if b["spent"]]
        if not gaps:
            break
        got = TX.fetch(gaps, "oracle-gaps")
        new_ids = []
        for t in got.values():
            for o in (t or {}).get("outputs", []):
                if any(x[0] == ORACLE_NFT for x in o["assets"]) and o["box"] not in seen:
                    new_ids.append(o["box"])
        if not new_ids:
            break
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(4) as ex:
            boxes = list(ex.map(lambda i: X.get(f"/boxes/{i}"), new_ids))
        for b in boxes:
            if b and b["boxId"] not in seen:
                seen.add(b["boxId"])
                rows.append(C.compact(b, ORACLE_NFT))
        rows.sort(key=lambda r: (r["h"], r["gix"]))
    return rows


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
    # the derived per-state series (NAV, RR, prices, discount) is recomputed from these by `series()`; not saved (17 MB)
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
        direction = "mint->pool" if minted > 0 else "pool->redeem"
        pairs.append({"h": h, "coin": coin, "dir": direction, "ergNet": e, "tokensLeft": {k2[:8]: v for k2, v in toks.items()},
                      "unitsMinted": minted, "ergPaidBank": paid, "oracleRefreshAt": lc,
                      "blocksAfterRefresh": h - lc if lc is not None else None, "legs": legs})
    tot = sum(p["ergNet"] for p in pairs)
    offs = sorted(p["blocksAfterRefresh"] for p in pairs if p["blocksAfterRefresh"] is not None)
    return {"txs": len(txs), "kinds": kinds, "pairs": len(pairs), "netNanoErg": tot,
            "byCoin": {f"{c} {d}": {"pairs": sum(1 for p in pairs if p["coin"] == c and p["dir"] == d),
                                    "netNanoErg": sum(p["ergNet"] for p in pairs if p["coin"] == c and p["dir"] == d),
                                    "losing": sum(1 for p in pairs if p["coin"] == c and p["dir"] == d and p["ergNet"] < 0)}
                       for c in ("SigRSV", "SigUSD") for d in ("mint->pool", "pool->redeem")},
            "window1738107to1888826": {"pairs": sum(1 for p in pairs if 1_738_107 <= p["h"] <= 1_888_826),
                                       "netNanoErg": sum(p["ergNet"] for p in pairs if 1_738_107 <= p["h"] <= 1_888_826),
                                       "mintedPaidNanoErg": sum(p["ergPaidBank"] for p in pairs
                                                                if 1_738_107 <= p["h"] <= 1_888_826 and p["dir"] == "mint->pool")},
            "byYear": [{"from": y0, "pairs": sum(1 for p in pairs if y0 <= p["h"] < y0 + 262_800),
                        "netNanoErg": sum(p["ergNet"] for p in pairs if y0 <= p["h"] < y0 + 262_800)}
                       for y0 in range(777_824, 1_891_309, 262_800)],
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


# ---------------------------------------------------------------------------------------------------- line s

DEXY = {   # NFT -> (role, the deployed tree and constant that names it)
    "75d7bfbfa6d165bfda1bad3e3fda891e67ccdcfc7b4410c1790923de2ccc9f7f": ("bank", "extract 898a2b5c const 37; free mint 264e3a22 const 14; intervention b794221f const 22; arbitrage mint 935d720e const 19"),
    "905ecdef97381b92c2f0ea9b516f312bfb18082c61b24b40affa6a55555c77c7": ("LP", "extract 898a2b5c const 21; free mint 264e3a22 const 16; trackers b886e7cf const 6; intervention b794221f const 23"),
    "ff7b7eff3c818f9dc573ca03a723a7f6ed1615bf27980ebd4a6c91986b26f801": ("LP swap", "LP 2cf12e36 const 11"),
    "10b755771f7253cff9727a9ca54bb2867e22b1b236657051c47ea9556c517e10": ("LP mint (deposit)", "LP 2cf12e36 const 12"),
    "471057efea32bf406d529902217844a258d3d6bedfcdcd3cfbab01872cc0b74c": ("LP redeem", "LP 2cf12e36 const 13"),
    "74f906985e763192fc1d8d461e29406c75b7952da3a89dbc83fe1b889971e455": ("free mint", "bank c9162bd0 const 7"),
    "3fefa1e3fef4e7abbdc074a20bdf751675f058e4bcce5cef0b38bb9460be5c6a": ("arbitrage mint", "bank c9162bd0 const 8"),
    "6597acef421c21a6468a2b58017df6577b23f00099d9e0772c0608deabdf6d13": ("intervention", "bank c9162bd0 const 11; LP 2cf12e36 const 16"),
    "26ef992a598eadfddabfd3c51509fb277b075c943b17199407f68c467b9de1ae": ("payout", "bank c9162bd0 const 12"),
    "7a776cf75b8b3a5aac50a36c41531a4d6f1e469d2cbcaa5795a4f5b4c255bf09": ("update", "bank c9162bd0 const 13; extract 898a2b5c const 2; intervention b794221f const 2"),
    "615be55206b1fea6d7d6828c1874621d5a6eb0e318f98a4e08c94a786f947cec": ("extract (to future / release)", "LP 2cf12e36 const 17"),
    "4675c1819c3e22add72b73f4b7e83eb743d45013b4ee2d8a63e215de9bc6f57f": ("tracker 101 (LP above 101%)", "extract 898a2b5c const 28; arbitrage mint 935d720e const 27"),
    "ff5269b5cdd037ea391b7210e28aeae0034ef670b9c4263995fe2a920e8d5a1d": ("tracker 95 (LP below 95%)", "extract 898a2b5c const 32"),
    "854bb70ed735b6c6a65ca80ce1f10bf217552d2be9ac936091a127f8c6480eaa": ("tracker 98 (LP below 98%)", "intervention b794221f const 28"),
    "610735cbf197f9de67b3628129feaa5a52403286859d140be719467c0fb94328": ("buyback (GORT)", "free mint 264e3a22 const 20; payout 8e0385a4 const 7; arbitrage mint 935d720e const 23"),
    "3c45f29a5165b030fdb5eaf5d81f8108f9d8f507b31487dd51f4ae08fe07cf4a": ("gold oracle pool (oracle-core v2)", "extract 898a2b5c const 26; free mint 264e3a22 const 18; intervention b794221f const 26; trackers b886e7cf const 8"),
    "97ad159235d25d05d7efc5863b5d360f89d7d668409502058be3e7aac177b9cb": ("gold oracle refresh", "oracle pool 416babd6 const 2"),
}
DEXYGOLD = "6122f7289e7bb2df2de273e09d4b2756cda6aeb0f40438dc9d257688f45183ad"
INT_MAX = 2147483647
DEXY_LIVE_FROM = 1_528_682     # the LP and bank first stand in their contracts (before: the deployer's wallet)


def dexy_contract_rows(rows):
    return [r for r in rows if r["hasNft"] and r["tpl"] != "af309fa026fd" and not (r.get("tree") or "").startswith("0008cd")]


def line_s(a):
    import txs as TX
    tip = a.tip or X.tip()
    chains_ = {n: C.fetch(n) for n in DEXY}
    ids = []
    for n, (role, src) in DEXY.items():
        rows = chains_[n]
        con = dexy_contract_rows(rows)
        br, rep = C.check(rows)
        tokinfo = X.get(f"/tokens/{n}")
        ids.append({"role": role, "nft": n, "name": tokinfo.get("name") if tokinfo else None,
                    "emission": tokinfo.get("emissionAmount") if tokinfo else None, "boxesEver": len(rows),
                    "contractBoxes": len(con), "contractTemplate": con[-1]["tpl"] if con else None,
                    "firstInContract": con[0]["h"] if con else None, "lastChange": con[-1]["h"] if con else None,
                    "current": con[-1]["box"] if con and not con[-1]["spent"] else None, "chainBreaks": len(br),
                    "fixedBy": src})
    lp = dexy_contract_rows(chains_["905ecdef97381b92c2f0ea9b516f312bfb18082c61b24b40affa6a55555c77c7"])
    bank = dexy_contract_rows(chains_["75d7bfbfa6d165bfda1bad3e3fda891e67ccdcfc7b4410c1790923de2ccc9f7f"])
    orc = [r for r in chains_["3c45f29a5165b030fdb5eaf5d81f8108f9d8f507b31487dd51f4ae08fe07cf4a"] if r["hasNft"] and r4int(r)]
    lp_s = Step([(r["h"], (r["value"], tok(r, DEXYGOLD), r["box"])) for r in lp])
    bank_s = Step([(r["h"], (r["value"], tok(r, DEXYGOLD))) for r in bank])
    o_s = Step([(r["h"], r4int(r)) for r in orc])
    trackers = {}
    for n, thr in (("854bb70ed735b6c6a65ca80ce1f10bf217552d2be9ac936091a127f8c6480eaa", 98),
                   ("ff5269b5cdd037ea391b7210e28aeae0034ef670b9c4263995fe2a920e8d5a1d", 95),
                   ("4675c1819c3e22add72b73f4b7e83eb743d45013b4ee2d8a63e215de9bc6f57f", 101)):
        rows = dexy_contract_rows(chains_[n])
        trackers[thr] = (rows, Step([(r["h"], int(r["regs"]["R7"])) for r in rows]),
                         rows[0]["regs"]["R6"] == "true")

    def lp_ratio(h):
        X0, Y0, _ = lp_s.at(h)
        return (X0 / Y0) / (o_s.at(h) / 1e6) if Y0 else None

    def tracker_cond(thr, h):
        """The tracker script's trigger condition at the states of block h (l9 vs l10, integer)."""
        X0, Y0, _ = lp_s.at(h)
        if not Y0:
            return None
        l9 = X0 // Y0 * 100
        l10 = thr * o_s.at(h) // 1_000_000
        return l9 < l10 if thr < 100 else l9 > l10

    evs = sorted({h for h in lp_s.h + o_s.h if h >= DEXY_LIVE_FROM and h <= tip})
    hist = []
    for i, h in enumerate(evs):
        X0, Y0, _ = lp_s.at(h)
        bR, bT = bank_s.at(h) if bank_s.at(h) else (None, None)
        r4 = o_s.at(h)
        hist.append([h, X0, Y0, r4, bR, 10**13 - bT if bT is not None else None,
                     round((X0 / Y0) / (r4 / 1e6), 5) if Y0 else None])
    save("s-series.json", {"cols": ["h", "lpNanoErg", "lpDexyGold", "oracleR4", "bankNanoErg", "dexyGoldOutsideBank",
                                    "lpOverOracle"], "note": "one row per LP or gold-oracle change from 1,528,682; "
                           "oracle R4 / 1e6 = nanoERG per DexyGold unit, as the contracts read it", "rows": hist})
    seg = [(hist[i][0], hist[i + 1][0] if i + 1 < len(hist) else tip + 1, hist[i]) for i in range(len(hist))]
    ratio_w = [(r[6], b - a) for a, b, r in seg if r[6] is not None]
    # actions: each spend of a contract box of an action NFT; who: the P2PK inputs of the spending transaction
    act_nfts = {"intervention": "6597acef421c21a6468a2b58017df6577b23f00099d9e0772c0608deabdf6d13",
                "tracker 98": "854bb70ed735b6c6a65ca80ce1f10bf217552d2be9ac936091a127f8c6480eaa",
                "tracker 95": "ff5269b5cdd037ea391b7210e28aeae0034ef670b9c4263995fe2a920e8d5a1d",
                "tracker 101": "4675c1819c3e22add72b73f4b7e83eb743d45013b4ee2d8a63e215de9bc6f57f",
                "free mint": "74f906985e763192fc1d8d461e29406c75b7952da3a89dbc83fe1b889971e455",
                "arbitrage mint": "3fefa1e3fef4e7abbdc074a20bdf751675f058e4bcce5cef0b38bb9460be5c6a",
                "LP swap": "ff7b7eff3c818f9dc573ca03a723a7f6ed1615bf27980ebd4a6c91986b26f801",
                "LP mint": "10b755771f7253cff9727a9ca54bb2867e22b1b236657051c47ea9556c517e10",
                "LP redeem": "471057efea32bf406d529902217844a258d3d6bedfcdcd3cfbab01872cc0b74c",
                "payout": "26ef992a598eadfddabfd3c51509fb277b075c943b17199407f68c467b9de1ae",
                "extract": "615be55206b1fea6d7d6828c1874621d5a6eb0e318f98a4e08c94a786f947cec"}
    spends = {}
    for name, n in act_nfts.items():
        rows = dexy_contract_rows(chains_[n])
        spends[name] = [(r, r["spent"]) for r in rows if r["spent"]]
    alltx = TX.fetch(sorted({t for v in spends.values() for _, t in v}), "dexy")
    actions = {}
    for name, v in spends.items():
        lst = []
        for r, t in v:
            tx = alltx.get(t)
            who = sorted({i["addr"] for i in tx["inputs"] if i["addr"] and i["addr"].startswith("9")}) if tx else []
            lst.append({"h": tx["h"] if tx else None, "tx": t, "box": r["box"], "who": who,
                        "regsAfter": None})
        lst.sort(key=lambda x: x["h"] or 0)
        hs = [x["h"] for x in lst if x["h"]]
        gaps = sorted(b2 - a2 for a2, b2 in zip(hs, hs[1:]))
        whoc = {}
        for x in lst:
            for w in x["who"]:
                whoc[w] = whoc.get(w, 0) + 1
        actions[name] = {"runs": len(lst), "first": hs[0] if hs else None, "last": hs[-1] if hs else None,
                         "gapBlocks": {"median": gaps[len(gaps) // 2] if gaps else None, "max": gaps[-1] if gaps else None,
                                       "p90": gaps[int(len(gaps) * 0.9)] if gaps else None},
                         "longestGaps": sorted([{"from": a2, "to": b2, "blocks": b2 - a2} for a2, b2 in zip(hs, hs[1:])],
                                               key=lambda g: -g["blocks"])[:5],
                         "executors": dict(sorted(whoc.items(), key=lambda kv: -kv[1])[:8]), "list": lst}
    # tracker delays: for each trigger (R7 INT_MAX -> h) and reset (h -> INT_MAX), how long after the condition held
    delays = {}
    for thr, (rows, st, _) in trackers.items():
        trig, reset = [], []
        for prev, cur in zip(rows, rows[1:]):
            h = cur["h"]
            was, now = int(prev["regs"]["R7"]), int(cur["regs"]["R7"])
            want = (was == INT_MAX and now != INT_MAX)
            # walk back over the event heights to the first block from which the condition held continuously
            j = bisect.bisect_right(evs, h) - 1
            first = None
            while j >= 0 and evs[j] >= prev["h"]:
                c = tracker_cond(thr, evs[j])
                if c is None or c != want:
                    break
                first = evs[j]
                j -= 1
            if first is None:
                continue
            (trig if want else reset).append((h, h - max(first, prev["h"])))
        delays[thr] = {"triggers": len(trig), "triggerDelay": dur_list([d for _, d in trig]), "resets": len(reset),
                       "resetDelay": dur_list([d for _, d in reset]),
                       "over100": [{"h": h, "kind": k, "blocks": d} for k, lst in (("trigger", trig), ("reset", reset))
                                   for h, d in lst if d > 100]}
    # intervention: valid when tracker 98 has been triggered for more than 20 blocks, LP < 98% of the oracle
    # (integer, as the script), and the intervention box is older than 360 blocks; delay to the run
    t98 = trackers[98][1]
    iv = dexy_contract_rows(chains_[act_nfts["intervention"]])
    iv_delay = []
    for prev, cur in zip(iv, iv[1:]):
        h = cur["h"]
        j = bisect.bisect_right(evs, h) - 1
        first = None
        while j >= 0:
            hh = evs[j]
            X0, Y0, _ = lp_s.at(hh)
            r7 = t98.at(hh)
            ok = Y0 and r7 is not None and r7 != INT_MAX and X0 * 100 < (o_s.at(hh) // 1_000_000) * 98 * Y0
            if not ok:
                break
            first = max(hh, r7 + 21, prev["h"] + 361)
            j -= 1
        if first is not None and first <= h:
            iv_delay.append({"h": h, "validFrom": first, "blocks": h - first})
    # validity windows never acted on: LP below 98% for long with no intervention
    # (the freeze): periods where tracker 98 stayed triggered and no intervention ran
    # mints: DexyGold out of the bank, ERG into the bank and the buyback, against the LP's price before the block
    # (an upper bound on what selling the minted units into the LP could have paid; it ignores the sale's impact)
    BANK = "75d7bfbfa6d165bfda1bad3e3fda891e67ccdcfc7b4410c1790923de2ccc9f7f"
    BUYBACK = "610735cbf197f9de67b3628129feaa5a52403286859d140be719467c0fb94328"
    mint_edges = {}
    for name in ("free mint", "arbitrage mint"):
        rows_ = []
        for x in actions[name]["list"]:
            tx = alltx.get(x["tx"])
            if not tx:
                continue
            bi = [i for i in tx["inputs"] if any(t[0] == BANK for t in i["assets"])]
            bo = [o for o in tx["outputs"] if any(t[0] == BANK for t in o["assets"])]
            yi = [i for i in tx["inputs"] if any(t[0] == BUYBACK for t in i["assets"])]
            yo = [o for o in tx["outputs"] if any(t[0] == BUYBACK for t in o["assets"])]
            if not (bi and bo):
                continue
            units = sum(t[1] for t in bi[0]["assets"] if t[0] == DEXYGOLD) - sum(t[1] for t in bo[0]["assets"] if t[0] == DEXYGOLD)
            paid = bo[0]["value"] - bi[0]["value"] + ((yo[0]["value"] - yi[0]["value"]) if (yi and yo) else 0)
            X0, Y0, _ = lp_s.at(x["h"] - 1)
            rows_.append({"h": x["h"], "units": units, "paidNanoErg": paid, "lpMid": X0 / Y0 if Y0 else None,
                          "edgeUpperNanoErg": int(units * X0 / Y0) - paid if Y0 else None})
        e = [r["edgeUpperNanoErg"] for r in rows_ if r["edgeUpperNanoErg"] is not None]
        mint_edges[name] = {"n": len(rows_), "units": sum(r["units"] for r in rows_),
                            "paidNanoErg": sum(r["paidNanoErg"] for r in rows_),
                            "edgeUpperNanoErg": sum(e), "positive": sum(1 for v in e if v > 0), "list": rows_}
    lp_now = lp[-1]
    out = {"explorer": X.EXPLORER, "tip": tip, "ids": ids,
           "now": {"lpBox": lp_now["box"], "lpNanoErg": lp_now["value"], "lpDexyGold": tok(lp_now, DEXYGOLD),
                   "lpSince": lp_now["h"], "bankNanoErg": bank[-1]["value"], "bankDexyGold": tok(bank[-1], DEXYGOLD),
                   "dexyGoldOutsideBank": 10**13 - tok(bank[-1], DEXYGOLD), "bankSince": bank[-1]["h"],
                   "oracleR4": o_s.v[-1], "oracleAt": o_s.h[-1],
                   "trackers": {thr: rows[-1]["regs"] for thr, (rows, _, _) in trackers.items()}},
           "lpOverOracle": {"percentiles": {k: round(v, 4) for k, v in pct(ratio_w, (1, 10, 25, 50, 75, 90, 99)).items()},
                            "blocksBelow98": sum(w for x, w in ratio_w if x < 0.98),
                            "blocksAbove101": sum(w for x, w in ratio_w if x > 1.01), "blocks": sum(w for _, w in ratio_w)},
           "actions": actions, "trackerDelays": delays, "mintEdges": mint_edges,
           "interventionDelay": {"n": len(iv_delay), "blocks": dur_list([d["blocks"] for d in iv_delay]),
                                 "list": iv_delay}}
    save("s.json", out)
    log(json.dumps({k: v for k, v in out.items() if k not in ("actions", "ids", "interventionDelay")}, indent=1))
    log(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "list"} for k, v in actions.items()}, indent=1))


def dur_list(xs):
    xs = sorted(xs)
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "min": xs[0], "median": xs[len(xs) // 2], "p90": xs[int(len(xs) * 0.9)], "max": xs[-1]}


# ---------------------------------------------------------------------------------------------------- line r

CAP = 1_000 * 10**9          # capital cap per strategy run (nanoERG)
DEPTH_MIN = 1_000 * 10**9    # every backtest starts at the first state where its pool holds at least 1,000 ERG
SPACING = 7_200              # entries / placements every 7,200 blocks (about 10 days)
OTHER_POOLS = {"RSN": "cadac6db847a715e3577d8f2fbb2edfb2280f20924abf51bf83704a9ddc511b2",
               "rsBTC": "47a811c68e49f6bfa6629602037ee65f8d175ddbc7b64bdb65ad40599b812fd0",
               "rsFIRO": "d86f6508c6b665bf4ba0bd3b56f7090404665b0cef26e5202d91127ed538f47c"}


def buy_to(X0, Y0, fee, target, cash):
    """Largest ERG in (<= cash) such that the pool's price after the swap stays <= target (nanoERG per unit)."""
    lo, hi = 0, cash
    if hi <= 0 or Y0 <= 1:
        return 0, 0
    while hi - lo > 1000:
        m = (lo + hi) // 2
        T = A.pool_tokens_out(X0, Y0, fee, m)
        if T <= 0 or (X0 + m) / (Y0 - T) <= target:
            lo = m
        else:
            hi = m
    T = A.pool_tokens_out(X0, Y0, fee, lo)
    return (lo, T) if T > 0 else (0, 0)


def sell_to(X0, Y0, fee, target, have):
    """Largest token amount (<= have) such that the pool's price after the sale stays >= target."""
    lo, hi = 0, have
    while hi - lo > 1:
        m = (lo + hi) // 2
        out = A.pool_erg_out(X0, Y0, fee, m)
        if (X0 - out) / (Y0 + m) >= target:
            lo = m
        else:
            hi = m
    return lo, A.pool_erg_out(X0, Y0, fee, lo) if lo else 0


def r1_dip(rows, th, tip):
    """SigRSV dip-buy at threshold th (fraction below NAV). Each trade is priced against the pool state it meets
    (impact included, integer pool rule) and at most one trade is made per pool state; the next historical state
    is taken to absorb it (a first version kept my trades in the pool for good, which left the modelled pool
    lifted for years after one buy-and-redeem, an artifact). The bank is taken as historical."""
    cash, held, cost = CAP, 0, 0          # cost: ERG paid for the units still held (the capital tied up)
    offX, offY = 0, 0
    trades, eq, peak, dd = [], [], CAP, 0
    tied_blocks, max_tied, open_from = 0, 0, None
    last_box = last_sold = None
    for r in rows:
        offX, offY = 0, 0
        X0, Y0, fee = r["rsvX"], r["rsvY"], r["rsvFee"]
        if X0 <= A.POOL_MIN_VALUE or Y0 <= 1:
            continue
        mid, nav = X0 / Y0, r["nav"]
        acted = False
        if held:
            b = A.Bank(r["R"], r["sc"], r["rc"], r["r4"])
            n = b.max_units("rc", -1, held) if r["rcRedeem"] is not None else 0
            if n:
                got = -b.exchange("rc", -n) - TX_FEE
                cash += got
                cost -= cost * n // held
                trades.append({"h": r["h"], "side": "redeem", "units": n, "ergNanoErg": got, "nav": nav})
                held -= n
                acted = True
            elif mid > nav and r["rsvBox"] != last_box:
                n, out = sell_to(X0, Y0, fee, nav, held)
                if n and out > TX_FEE:
                    cash += out - TX_FEE
                    cost -= cost * n // held
                    offX -= out
                    offY += n
                    held -= n
                    last_sold = r["rsvBox"]
                    trades.append({"h": r["h"], "side": "sell", "units": n, "ergNanoErg": out - TX_FEE, "nav": nav,
                                   "poolPrice": mid})
                    acted = True
            if held == 0:
                cost = 0
                open_from = None
        budget = min(cash, CAP - cost) - TX_FEE     # profits are set aside: never more than CAP in the position
        if not acted and mid < nav * (1 - th) and budget > 10 * TX_FEE and r["rsvBox"] != last_box \
                and r["rsvBox"] != last_sold:
            dX, T = buy_to(X0, Y0, fee, nav * (1 - th), budget)
            if T > 0:
                cash -= dX + TX_FEE
                cost += dX + TX_FEE
                held += T
                offX += dX
                offY -= T
                last_box = r["rsvBox"]
                trades.append({"h": r["h"], "side": "buy", "units": T, "ergNanoErg": -(dX + TX_FEE), "nav": nav,
                               "poolPrice": mid, "discount": round(mid / nav - 1, 4)})
                if open_from is None:
                    open_from = r["h"]
        X1, Y1 = r["rsvX"] + offX, r["rsvY"] + offY
        mark_pool = A.pool_erg_out(X1, Y1, fee, held) if held else 0
        e = cash + mark_pool
        peak = max(peak, e)
        dd = max(dd, peak - e)
        tied = cost if held else 0
        max_tied = max(max_tied, tied)
        if held:
            tied_blocks += r["to"] - r["h"]
    last = rows[-1]
    nav_mark = held * last["nav"]
    pool_mark = A.pool_erg_out(last["rsvX"] + offX, last["rsvY"] + offY, last["rsvFee"], held) if held else 0
    buys = [t for t in trades if t["side"] == "buy"]
    return {"threshold": th, "trades": len(trades), "buys": len(buys),
            "redeems": sum(1 for t in trades if t["side"] == "redeem"),
            "sells": sum(1 for t in trades if t["side"] == "sell"),
            "netNanoErgMarkedNav": cash + nav_mark - CAP, "netNanoErgMarkedPool": cash + pool_mark - CAP,
            "realisedCashNanoErg": cash - CAP, "openUnits": held, "openMarkedNavNanoErg": nav_mark,
            "maxCapitalTiedNanoErg": max_tied, "blocksWithPosition": tied_blocks, "worstDrawdownNanoErg": dd,
            "trades_": trades}


def r3_exits(rows, levels, tip):
    """A 100-ERG SigRSV position bought from the pool every SPACING blocks, parked in an exit box per trigger."""
    hs = [r["h"] for r in rows]
    out = {}
    trig = {f"ergusd>={L}": (lambda r, L=L: 1e9 / r["r4"] >= L) for L in levels}
    trig["rr>=400 (redeem open)"] = lambda r: r["rcRedeem"] is not None
    trig["pool>=nav+2%"] = lambda r: r["rsvX"] / r["rsvY"] >= r["nav"] * 1.02
    entries = list(range(rows[0]["h"], tip, SPACING))
    for name, f in trig.items():
        res = []
        for e in entries:
            i = bisect.bisect_right(hs, e) - 1
            r0 = rows[i]
            T = A.pool_tokens_out(r0["rsvX"], r0["rsvY"], r0["rsvFee"], 100 * 10**9)
            if T <= 0:
                continue
            if f(r0):                     # an exit set where it would fire at once is not a conditional exit
                res.append({"entry": e, "alreadyTrue": True})
                continue
            fill = None
            for r in rows[i + 1:]:
                if f(r):
                    if r["rcRedeem"] is not None:
                        b = A.Bank(r["R"], r["sc"], r["rc"], r["r4"])
                        n = b.max_units("rc", -1, T)
                        got = -b.exchange("rc", -n) if n else 0
                        rest = A.pool_erg_out(r["rsvX"], r["rsvY"], r["rsvFee"], T - n) if T - n else 0
                        fill = (r["h"], got + rest - 2 * TX_FEE, "bank" if n == T else "bank+pool")
                    else:
                        fill = (r["h"], A.pool_erg_out(r["rsvX"], r["rsvY"], r["rsvFee"], T) - 2 * TX_FEE, "pool")
                    break
            if fill:
                res.append({"entry": e, "fired": fill[0], "wait": fill[0] - e, "ergOut": fill[1], "via": fill[2]})
            else:
                res.append({"entry": e, "fired": None, "markNavNanoErg": T * rows[-1]["nav"]})
        skipped = sum(1 for x in res if x.get("alreadyTrue"))
        res = [x for x in res if not x.get("alreadyTrue")]
        fired = [x for x in res if x["fired"]]
        waits = sorted(x["wait"] for x in fired)
        rets = sorted(x["ergOut"] / 1e11 - 1 for x in fired)
        out[name] = {"entries": len(res), "alreadyTrueAtEntry": skipped, "fired": len(fired), "waitBlocks": dur_list(waits),
                     "returnOn100Erg": {"median": round(rets[len(rets) // 2], 4) if rets else None,
                                        "min": round(rets[0], 4) if rets else None, "max": round(rets[-1], 4) if rets else None},
                     "via": {v: sum(1 for x in fired if x["via"] == v) for v in ("bank", "bank+pool", "pool")},
                     "unfiredMarkNavReturn": round(sum(x["markNavNanoErg"] for x in res if not x["fired"]) /
                                                   (1e11 * max(1, len(res) - len(fired))) - 1, 4) if len(res) > len(fired) else None,
                     "list": res}
    return out


def first_deep(step):
    return next((h for h, v in zip(step.h, step.v) if v[0] >= DEPTH_MIN), None)


def pool_rows(step, lo, tip):
    lo = max(lo, first_deep(step) or lo)
    hs = [h for h in step.h if h <= tip]
    out = []
    for i, h in enumerate(hs):
        X0, Y0, fee, box = step.v[i]
        out.append((h, hs[i + 1] if i + 1 < len(hs) else tip + 1, X0, Y0, fee))
    return [o for o in out if o[1] > lo]


def r4_babel(prow, levels, tip, side="buy"):
    """Standing offers placed every SPACING blocks at `levels` below (buy) or above (sell) the pool's mid price,
    100 ERG each (buy: ERG in the box; sell: tokens bought at placement). A keyless taker fills against the pool when
    it nets at least one transaction fee; repeated takes until the box is empty."""
    hs = [p[0] for p in prow]
    res = {}
    for d in levels:
        boxes = []
        for e in range(max(prow[0][0], hs[0]), tip - SPACING, SPACING):
            i = bisect.bisect_right(hs, e) - 1
            _, _, X0, Y0, fee = prow[i]
            mid = X0 / Y0
            if side == "buy":
                bid = int(mid * (1 - d))
                avail, units, paid, fills = 100 * 10**9, 0, 0, []
                mkt_T = A.pool_tokens_out(X0, Y0, fee, 100 * 10**9)
                for p in prow[i + 1:]:
                    if avail < 10**6:
                        break
                    if p[2] * 1000 / (p[3] * p[4]) >= bid:      # pool's marginal ask above the bid: no take
                        continue
                    t = A.babel_vs_pool(p[2], p[3], p[4], max(bid, 1), avail)
                    if t and t[0] >= TX_FEE:
                        _, dX, T, Y = t
                        avail -= Y
                        units += T
                        paid += Y
                        fills.append({"h": p[0], "units": T, "paid": Y, "poolMid": p[2] / p[3]})
                filled = paid > 0
                p_tip = prow[-1][2] / prow[-1][3]
                owner = units * p_tip + (100 * 10**9 - paid)          # tokens filled + ERG left, at the tip
                market = mkt_T * p_tip                                 # 100 ERG bought at market when placed
                boxes.append({"placed": e, "bid": bid, "mid": mid, "filled": filled,
                              "firstFill": fills[0]["h"] if fills else None, "units": units, "paidNanoErg": paid,
                              "fillShare": paid / 1e11, "gainVsMarketAtTipNanoErg": int(owner - market),
                              "savedPerUnitVsPlacementMid": round(1 - (paid / units) / mid, 4) if units else None,
                              "fillVsPoolMid": round(bid / fills[0]["poolMid"] - 1, 4) if fills else None})
            else:
                ask = int(mid * (1 + d))
                T0 = A.pool_tokens_out(X0, Y0, fee, 100 * 10**9)
                left, got, fills = T0, 0, []
                for p in prow[i + 1:]:
                    if left <= 0:
                        break
                    if p[2] * p[4] / (p[3] * 1000) <= ask:      # pool's marginal bid below the ask: no take
                        continue
                    # taker buys n units from the ask box at `ask` and sells them into the pool
                    def prof(n, p=p):
                        return A.pool_erg_out(p[2], p[3], p[4], n) - n * ask
                    n, v = A.argmax_int(prof, 1, left)
                    if n and v >= TX_FEE:
                        left -= n
                        got += n * ask
                        fills.append({"h": p[0], "units": n, "recv": n * ask, "poolMid": p[2] / p[3]})
                sold = T0 - left
                p_tip = prow[-1][2] / prow[-1][3]
                owner = got + left * p_tip                             # ERG received + tokens left, at the tip
                market = A.pool_erg_out(X0, Y0, fee, T0)              # the same tokens sold at market when placed
                boxes.append({"placed": e, "ask": ask, "mid": mid, "filled": sold > 0,
                              "firstFill": fills[0]["h"] if fills else None, "unitsSold": sold, "receivedNanoErg": got,
                              "fillShare": sold / T0 if T0 else 0, "gainVsMarketAtTipNanoErg": int(owner - market),
                              "fillVsPoolMid": round(ask / fills[0]["poolMid"] - 1, 4) if fills else None})
        f = [b for b in boxes if b["filled"]]
        waits = sorted(b["firstFill"] - b["placed"] for b in f)
        res[str(d)] = {"boxes": len(boxes), "filled": len(f), "fullyFilled": sum(1 for b in f if b["fillShare"] > 0.99),
                       "waitBlocks": dur_list(waits),
                       "medianFillVsPoolMid": sorted(b["fillVsPoolMid"] for b in f)[len(f) // 2] if f else None,
                       "gainVsMarketAtTipNanoErg": sum(b["gainVsMarketAtTipNanoErg"] for b in boxes),
                       "boxesAheadOfMarket": sum(1 for b in boxes if b["gainVsMarketAtTipNanoErg"] > 0),
                       "list": boxes}
    return res


def r5_grid(prow, spacing, tip, levels=5, size=50 * 10**9):
    """Symmetric grid: `levels` bids below and asks above the start price at `spacing`, `size` ERG each. A fill is
    when the pool's marginal price (with its fee) crosses a level by enough that the keyless taker nets a fee; a
    filled bid becomes an ask one level up and vice versa."""
    h0, _, X0, Y0, fee = prow[0]
    P0 = X0 / Y0
    grid = [P0 * (1 + spacing) ** k for k in range(-levels, levels + 1)]
    state = {}                       # level index -> "bid" or "ask" (level 0 is the start: empty)
    cash, units = 0, 0
    for k in range(-levels, 0):
        state[k] = "bid"
        cash += size
    T0 = 0
    for k in range(1, levels + 1):
        state[k] = "ask"
        t = int(size / grid[levels + k])
        units += t
        T0 += t
    start_cost = A.pool_erg_in_for(X0, Y0, fee, T0) if T0 < Y0 else None
    capital = cash + (start_cost or 0)
    fills, round_trips, spread = [], 0, 0
    for h, to, X1, Y1, f1 in prow:
        buy_px = X1 / Y1 * 1000 / f1         # marginal price to buy from the pool
        sell_px = X1 / Y1 * f1 / 1000        # marginal price to sell into the pool
        for k in sorted(state):
            px = grid[levels + k]
            t = int(size / px)
            if state[k] == "bid" and buy_px < px and t * (px - buy_px) >= TX_FEE:
                state[k] = None
                cash -= int(t * px)
                units += t
                if k + 1 <= levels:
                    state[k + 1] = "ask"
                fills.append({"h": h, "level": k, "side": "buy", "units": t, "price": px})
            elif state[k] == "ask" and sell_px > px and t * (sell_px - px) >= TX_FEE and units >= t:
                state[k] = None
                cash += int(t * px)
                units -= t
                if k - 1 >= -levels:
                    state[k - 1] = "bid"
                    round_trips += 1
                    spread += int(t * px) - int(t * grid[levels + k - 1])
                fills.append({"h": h, "level": k, "side": "sell", "units": t, "price": px})
    hl, _, XL, YL, fL = prow[-1]
    mark = cash + (A.pool_erg_out(XL, YL, fL, units) if units else 0) - (levels * size)
    hold_mix = levels * size + (A.pool_erg_out(XL, YL, fL, T0) if T0 else 0)
    return {"spacing": spacing, "from": h0, "startPrice": P0, "endPrice": XL / YL, "capitalNanoErg": capital,
            "fills": len(fills), "roundTrips": round_trips, "realisedSpreadNanoErg": spread,
            "endUnits": units, "startUnits": T0, "endValueNanoErg": mark + levels * size,
            "netVsHoldErgNanoErg": mark + levels * size - capital,
            "netVsHoldMixNanoErg": mark + levels * size - hold_mix, "fills_": fills[:200]}


def line_r(a):
    tip = a.tip or X.tip()
    rows, checks, (bank, orc, rsv, usd), lo = series(tip)
    deep = first_deep(rsv)
    rows = [r for r in rows if r["h"] >= deep]
    for r in rows:
        r["rsvBox"] = rsv.at(r["h"])[3]
    out = {"explorer": X.EXPLORER, "tip": tip, "from": rows[0]["h"], "capNanoErg": CAP, "txFeeNanoErg": TX_FEE,
           "depthMinNanoErg": DEPTH_MIN,
           "rules": "see CENSUS-U1D.md line r"}
    # 1. dip-buy
    d = {}
    for th in (0.02, 0.05, 0.10):
        res = r1_dip(rows, th, tip)
        d[str(th)] = {k: v for k, v in res.items() if k != "trades_"}
        d[str(th)]["tradeList"] = res["trades_"]
    for label, h0 in (("last262800", tip - 262_800), ("last525600", tip - 525_600)):
        sub = [r for r in rows if r["h"] >= h0]
        d[label] = {str(th): {k: v for k, v in r1_dip(sub, th, tip).items() if k != "trades_"} for th in (0.02, 0.05, 0.10)}
    first, last = rows[0], rows[-1]
    T_hold = A.pool_tokens_out(first["rsvX"], first["rsvY"], first["rsvFee"], CAP)
    d["holdSigRSVFromStart"] = {"from": first["h"], "units": T_hold, "markNavNanoErg": T_hold * last["nav"] - CAP,
                                "usdPerErgStart": round(1e9 / first["r4"], 4), "usdPerErgTip": round(1e9 / last["r4"], 4)}
    out["dipBuy"] = d
    # 2. beat the bot
    q = load("q.json")
    pairs = q["bot"]["list"]
    span = (pairs[-1]["h"] - pairs[0]["h"]) if pairs else 1
    gross = [p["ergNet"] + sum(TX_FEE for lg in p["legs"]) for p in pairs]
    fees_paid = []
    out["beatTheBot"] = {"pairs": len(pairs), "botNetNanoErg": sum(p["ergNet"] for p in pairs),
                         "builderNetNanoErg": sum(gross), "spanBlocks": span,
                         "perYearNanoErg": int(sum(gross) * 262_800 / span) if span else None,
                         "shares": {str(s): {"nanoErgAll": int(sum(gross) * s),
                                             "nanoErgPerYear": int(sum(gross) * 262_800 / span * s) if span else None}
                                    for s in (0.015, 0.017, 0.10, 0.30)},
                         "lastYear": {"pairs": sum(1 for p in pairs if p["h"] > tip - 262_800),
                                      "builderNetNanoErg": sum(g for p, g in zip(pairs, gross) if p["h"] > tip - 262_800)},
                         "byYear": q["bot"]["byYear"],
                         "note": "builder net = the bot's net plus the fees it paid (a builder pays itself no fee in "
                                 "its own block); the same pair at the same states, taken first"}
    # 3. conditional exits
    # $4 (SK-051's take-profit) and three levels just above the tip's $0.30, inside the last two years' range
    levels = [4.0, 0.35, 0.50, 0.75]
    recent = [r for r in rows if r["h"] >= tip - 525_600]
    out["exits"] = {"levels": levels, "results": r3_exits(rows, levels, tip),
                    "entriesLast525600": r3_exits(recent, levels, tip),
                    "ergUsdRangeLast525600": [round(min(1e9 / r["r4"] for r in recent), 4),
                                              round(max(1e9 / r["r4"] for r in recent), 4)]}
    # 4. Babel buy offers and the sell mirror; 5. grid
    psteps = {"SigUSD": usd, "SigRSV": rsv}
    for name, n in OTHER_POOLS.items():
        psteps[name] = pool_step(C.fetch(n))
    babel, grid = {}, {}
    for name, st in psteps.items():
        prow = pool_rows(st, lo, tip)
        if len(prow) < 3:
            continue
        babel[name] = {"buy": r4_babel(prow, (0.02, 0.05, 0.10, 0.20), tip, "buy"),
                       "sell": r4_babel(prow, (0.02, 0.05, 0.10, 0.20), tip, "sell"), "from": prow[0][0]}
        if name in ("RSN", "SigUSD", "rsBTC"):
            grid[name] = {str(sp): r5_grid(prow, sp, tip) for sp in (0.02, 0.05, 0.10)}
    out["babel"] = babel
    out["grid"] = grid
    save("r.json", out)
    log(json.dumps({"dipBuy": {k: {kk: vv for kk, vv in v.items() if kk != "tradeList"} for k, v in d.items()},
                    "beatTheBot": out["beatTheBot"]}, indent=1))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("line", choices=["q", "r", "s", "t", "u"])
    p.add_argument("--tip", type=int, default=None)
    a = p.parse_args()
    {"q": line_q, "r": line_r, "s": line_s, "t": line_t}[a.line](a)
    log("requests", X.stats)


if __name__ == "__main__":
    main()
