#!/usr/bin/env python3
"""SigUSD buy-and-redeem: buy SigUSD from the ErgoDEX pool, redeem it at the SigmaUSD bank.

The take U1d named and did not test (CENSUS-U1D.md, "buy-and-redeem is open and nobody takes it"). SigUSD
redemption is never locked by the reserve ratio (AgeUSD.scala: only minting SigUSD and redeeming SigRSV are), so the
take is open whenever the pool sells SigUSD below the bank's redeem price, net of the bank's 2% fee, the pool's fee
and two transaction fees.

    backtest   over U1d's committed state series (census/u1d/q-series-*.json), no network
    live       the bank, oracle and pool as they stand now (explorer), and the best take at caps

Each state is priced as U1d's line r prices trades: against the state it meets, with its impact, in the contracts'
integer arithmetic (census/amm.py), one trade per pool state, the next historical state absorbing it. Leg 2 risk:
the two legs are two transactions (the pool and the bank each take their successor at OUTPUTS(0)); the redeem is
also priced at the next oracle value, the case where a refresh lands between the legs.
Build and submit nothing.
"""
import argparse, bisect, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "census"))
import amm as A  # noqa: E402

U1D = os.path.join(HERE, "census", "u1d")
OUT = os.path.join(HERE, "census", "u1d", "sigusd-redeem.json")
TX_FEE = 1_100_000
CAPS = (10 * 10**9, 100 * 10**9, 1000 * 10**9)
YEAR = 262_800

BANK_NFT = "7d672d1def471720ca5782fd6473e47e796d9ac0c138d9911346f118b2f6d9d9"
ORACLE_NFT = "011d3364de07e5a26f0c4eef0852cddb387039a921b7154ef3cab22c6eda887f"
USD_POOL = "9916d75132593c8b07fe18bd8d583bda1652eed7565cf41a4738ddd90fc992ec"
SIGUSD = "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04"


class Step:
    def __init__(self, rows):
        self.h = [r[0] for r in rows]
        self.v = [r[1:] for r in rows]

    def at(self, h):
        i = bisect.bisect_right(self.h, h) - 1
        return self.v[i] if i >= 0 else None

    def after(self, h):
        i = bisect.bisect_right(self.h, h)
        return self.v[i] if i < len(self.v) else None


def load(name):
    with open(os.path.join(U1D, name)) as f:
        return json.load(f)["rows"]


def best(R, sc, rc, r4, X0, Y0, fee, cap, r4_redeem=None):
    """Most profitable buy-from-pool, redeem-at-bank with pool cost <= cap: (units, cost, proceeds, net) or None.
    r4_redeem: price the redeem at another oracle value (the leg-2 risk case)."""
    bank = A.Bank(R, sc, rc, r4)
    dmax = bank.max_units("sc", -1, min(Y0 - 1, sc))
    if dmax <= 0:
        return None
    # cap: the largest d whose pool cost is within cap
    lo, hi = 0, dmax
    while lo < hi:
        m = (lo + hi + 1) // 2
        if A.pool_erg_in_for(X0, Y0, fee, m) <= cap:
            lo = m
        else:
            hi = m - 1
    if lo <= 0:
        return None

    def p(d):
        return -bank.exchange("sc", -d) - A.pool_erg_in_for(X0, Y0, fee, d)
    d, gross = A.argmax_int(p, 1, lo)
    if not d or gross - 2 * TX_FEE <= 0:
        return None
    cost = A.pool_erg_in_for(X0, Y0, fee, d)
    out = {"units": d, "costNanoErg": cost, "proceedsNanoErg": cost + gross, "netNanoErg": gross - 2 * TX_FEE}
    if r4_redeem is not None and r4_redeem != r4:
        b2 = A.Bank(R, sc, rc, r4_redeem)
        e2 = b2.exchange("sc", -d)
        out["netIfRefreshNanoErg"] = None if e2 is None else -e2 - cost - 2 * TX_FEE
    return out


def backtest(a):
    bank = Step(load("q-series-bank.json"))            # h, R, sc, rc, box
    orc = Step(load("q-series-oracle.json"))            # h, r4
    pool = Step(load("q-series-pool-sigusd.json"))      # h, ergX, tokenY, fee, box
    lo = max(bank.h[0], orc.h[0], pool.h[0])
    tip = max(bank.h[-1], orc.h[-1], pool.h[-1])
    evs = sorted({h for s in (bank, orc, pool) for h in s.h if h >= lo})
    res = {str(c // 10**9): {"takes": 0, "netNanoErg": 0, "netIfRefreshNanoErg": 0, "refreshLosses": 0,
                            "byYear": {}, "list": []} for c in CAPS}
    open_blocks, runs, cur = 0, [], None
    seen_box = set()
    for i, h in enumerate(evs):
        to = evs[i + 1] if i + 1 < len(evs) else tip + 1
        R, sc, rc, _ = bank.at(h)
        (r4,) = orc.at(h)
        X0, Y0, fee, pbox = pool.at(h)
        if not r4 or X0 <= A.POOL_MIN_VALUE or Y0 <= 1:
            cur = None
            continue
        nxt = orc.after(h)
        any_open = False
        for c in CAPS:
            b = best(R, sc, rc, r4, X0, Y0, fee, c, r4_redeem=nxt[0] if nxt else None)
            if not b:
                continue
            any_open = True
            k = str(c // 10**9)
            if (k, pbox) in seen_box:
                continue                     # one trade per pool state
            seen_box.add((k, pbox))
            r = res[k]
            r["takes"] += 1
            r["netNanoErg"] += b["netNanoErg"]
            nr = b.get("netIfRefreshNanoErg", b["netNanoErg"])
            nr = -b["costNanoErg"] if nr is None else nr
            r["netIfRefreshNanoErg"] += min(nr, b["netNanoErg"])
            r["refreshLosses"] += nr < 0
            y = str((h - lo) // YEAR)
            r["byYear"][y] = r["byYear"].get(y, 0) + b["netNanoErg"]
            r["list"].append({"h": h, "poolBox": pbox, **b})
        if any_open:
            open_blocks += to - h
            if cur and cur[1] == h:
                cur[1] = to
            else:
                cur = [h, to]
                runs.append(cur)
        else:
            cur = None
    durs = sorted(b - a_ for a_, b in runs)
    span = tip - lo
    out = {"source": "census/u1d/q-series-*.json (U1d, Cornell mirror, to 1,891,308)", "from": lo, "tip": tip,
           "txFeeNanoErg": TX_FEE, "blocksOpen": open_blocks, "fractionOpen": round(open_blocks / span, 4),
           "episodes": {"n": len(durs), "medianBlocks": durs[len(durs) // 2] if durs else None,
                        "p90Blocks": durs[int(len(durs) * 0.9)] if durs else None, "maxBlocks": durs[-1] if durs else None},
           "lastEpisode": runs[-1] if runs else None, "caps": {}}
    for k, r in res.items():
        last = [t for t in r["list"] if t["h"] > tip - YEAR]
        out["caps"][k] = {"takes": r["takes"], "netErg": round(r["netNanoErg"] / 1e9, 3),
                          "perYearErg": round(r["netNanoErg"] / 1e9 * YEAR / span, 2),
                          "lastYear": {"takes": len(last), "netErg": round(sum(t["netNanoErg"] for t in last) / 1e9, 3)},
                          "netIfEveryRefreshLandsBetweenLegsErg": round(r["netIfRefreshNanoErg"] / 1e9, 3),
                          "takesLosingIfRefreshBetweenLegs": r["refreshLosses"],
                          "byYearErg": {y: round(v / 1e9, 3) for y, v in sorted(r["byYear"].items(), key=lambda x: int(x[0]))},
                          "medianNetErg": round(sorted(t["netNanoErg"] for t in r["list"])[len(r["list"]) // 2] / 1e9, 4) if r["list"] else None,
                          "top": sorted(r["list"], key=lambda t: -t["netNanoErg"])[:5],
                          "last": r["list"][-5:],
                          "takeHeights": [t["h"] for t in r["list"]],
                          "episodeStarts": sorted(a_ for a_, _b in runs)}
    # Lower bound: one take per episode (a contiguous run of open states), at its first state. The per-state sums
    # above count every pool state of an episode as a fresh take, as if the earlier take had not closed the gap;
    # in the history other traders' flow is all that reopens it, so the truth lies between the two.
    starts = {a_ for a_, _b in runs}
    for k, r in res.items():
        ep = [t for t in r["list"] if t["h"] in starts]
        last = [t for t in ep if t["h"] > tip - YEAR]
        out["caps"][k]["perEpisodeLowerBound"] = {
            "takes": len(ep), "netErg": round(sum(t["netNanoErg"] for t in ep) / 1e9, 3),
            "perYearErg": round(sum(t["netNanoErg"] for t in ep) / 1e9 * YEAR / span, 2),
            "lastYear": {"takes": len(last), "netErg": round(sum(t["netNanoErg"] for t in last) / 1e9, 3)},
            "medianNetErg": round(sorted(t["netNanoErg"] for t in ep)[len(ep) // 2] / 1e9, 4) if ep else None,
            "medianCapitalErg": round(sorted(t["costNanoErg"] for t in ep)[len(ep) // 2] / 1e9, 2) if ep else None}
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "caps"}, indent=1))
    for k, v in out["caps"].items():
        print(k, "ERG cap:", json.dumps({kk: vv for kk, vv in v.items() if kk not in ("top", "last")}))


def live(a):
    import explorer as X
    def one(nft):
        b = X.get(f"/boxes/unspent/byTokenId/{nft}?limit=5", cache=False)["items"]
        b = [x for x in b if any(t["tokenId"] == nft for t in x["assets"])]
        assert len(b) == 1, (nft, len(b))
        return b[0]
    bk, oc, pl = one(BANK_NFT), one(ORACLE_NFT), one(USD_POOL)
    R = bk["value"]
    sc = int(bk["additionalRegisters"]["R4"]["renderedValue"])
    rc = int(bk["additionalRegisters"]["R5"]["renderedValue"])
    r4 = int(oc["additionalRegisters"]["R4"]["renderedValue"])
    X0 = pl["value"]
    Y0 = next(t["amount"] for t in pl["assets"] if t["tokenId"] == SIGUSD)
    fee = int(pl["additionalRegisters"]["R4"]["renderedValue"])
    bank = A.Bank(R, sc, rc, r4)
    redeem1 = -bank.exchange("sc", -1)
    buy1 = X0 / Y0 * 1000 / fee
    print(json.dumps({"tip": X.tip(), "bank": bk["boxId"], "oracle": oc["boxId"], "oracleHeight": oc["settlementHeight"],
                      "pool": pl["boxId"], "rr": R * 100 // (sc * bank.rate),
                      "redeemNanoErgPerUnit": redeem1, "poolBuyNanoErgPerUnit": round(buy1),
                      "gapPct": round((redeem1 / buy1 - 1) * 100, 3)}, indent=1))
    for c in CAPS:
        print(c // 10**9, "ERG cap:", best(R, sc, rc, r4, X0, Y0, fee, c))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["backtest", "live"])
    a = p.parse_args()
    {"backtest": backtest, "live": live}[a.mode](a)


if __name__ == "__main__":
    main()
