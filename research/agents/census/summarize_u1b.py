#!/usr/bin/env python3
"""Tables for CENSUS-U1B.md from census/u1b/*.json. Every number in the report comes from here.

usage: summarize_u1b.py [census/u1b] > census/u1b/summary.md
"""
import collections, csv, json, os, sys

D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "u1b")
E = 1e9


def load(n):
    p = os.path.join(D, n)
    return json.load(open(p)) if os.path.exists(p) else None


def erg(x, k=4):
    return f"{x / E:,.{k}f}"


def table(head, rows):
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")
    print()


def line_f(f):
    print(f"## f. Keyless spends by template ({f['from']:,}..{f['to']:,})\n")
    print(f"Transactions with at least one keyless input: {f['keylessTxs']:,}. Templates with a keyless spend: "
          f"{len(f['templates'])}.\n")
    rows = []
    for t in f["templates"]:
        rows.append([t["templateHash"][:12], t["name"]["name"][:70], f"{t['keylessSpends']:,}", f"{t['keylessTxs']:,}",
                     f"{t['signedSpends']:,}", erg(t["keylessNanoErg"], 2),
                     "" if t["unspentNow"] is None else f"{t['unspentNow']:,}",
                     f"{t['samplesRentAge']}/{t['samplesChecked']}"])
    table(["template", "what (source in the text)", "keyless spends", "txs", "signed spends", "ERG in", "unspent now",
           "rent-age samples"], rows)
    if f.get("neverSpentKeyless"):
        table(["template", "keyless on some path, never spent keyless in the window", "signed spends", "unspent now"],
              [[t["templateHash"][:12], t["name"], t["signedSpends"], t["unspentNow"]] for t in f["neverSpentKeyless"]])
    r = f.get("p2pkRent")
    if r:
        print(f"P2PK inputs with no proof (storage-rent claims): {r['spends']:,} spends in {r['blocks']:,} blocks, "
              f"box value {erg(r['nanoErg'])} ERG.\n")


def line_k(k):
    print(f"## k. Fees on every block ({k['from']:,}..{k['to']:,}, {k['blocks']:,} blocks)\n")
    table(["", "ERG"], [
        ["mean fee per block", erg(k["meanNanoErg"])], ["median", erg(k["medianNanoErg"])],
        ["max", erg(k["maxNanoErg"])], ["U1 sample (every 10th) mean", erg(k["u1SampleMeanNanoErg"])],
        ["U1 sample median", erg(k["u1SampleMedianNanoErg"])], ["reward mean", erg(k["rewardMeanNanoErg"])],
        ["reward + fees per block", erg(k["rewardPlusFeeMeanNanoErg"])], ["total fees", erg(k["totalNanoErg"], 2)]])
    table(["percentile", "ERG"], [[p, erg(v)] for p, v in k["percentiles"].items()])
    table(["fee from ERG", "below ERG", "blocks"],
          [[erg(h["fromNanoErg"]), "∞" if h["belowNanoErg"] >= 10 ** 17 else erg(h["belowNanoErg"]), f"{h['blocks']:,}"]
           for h in k["histogram"]])
    print(f"Blocks with zero fees: {k['zeroFeeBlocks']:,}. Transactions per block: {k['txPerBlockMean']:.2f}.\n")
    table(["top block", "fees ERG", "txs"], [[f"{x['height']:,}", erg(x["feeNanoErg"]), x["txs"]] for x in k["topBlocks"]])


def line_g(g):
    print(f"## g. Fixed-price offers at tip {g['atTip']:,}\n")
    print("Unspent: " + ", ".join(f"{k} {v}" for k, v in g["unspent"].items()) + f"; N2T pools live {g['n2tPoolsLive']}.\n")
    rows = []
    for r in g["offers"]:
        if "unparsed" in r:
            rows.append([r["kind"], r["boxId"][:8], "", erg(r.get("valueNanoErg", 0)), "", "", "not fillable: " +
                         r["unparsed"].split("(")[1][:45], ""])
            continue
        b = r["best"]
        leg = r["legs"][0]
        if leg["side"] == "lots":
            price = f"{leg['n']} lots (buy {leg['buyLots']}, sell {leg['sellLots']})"
        else:
            price = f"{leg['side']} {leg['price']:,}" + (f"; bid {r['legs'][1]['price']:,}" if len(r["legs"]) > 1 else "")
        mid = r["deepestPoolNanoErgPerUnit"]
        rows.append([r["kind"], r["boxId"][:8], (r["token"] or "")[:8], erg(r["valueNanoErg"]), r["tokensHeld"], price,
                     "-" if mid is None else f"{mid:,.2f}",
                     "-" if not b else f"{erg(b['profitNanoErg'])} ({b['tokens']:,} units, pool {b['poolNft'][:8]})"])
    table(["kind", "box", "token", "ERG", "tokens", "price nanoERG/unit", "pool nanoERG/unit", "best take ERG"], rows)
    s = g["sequential"]
    print(f"Taken in turn (pool updated after each): **{erg(s['totalNanoErg'])} ERG** in {len(s['takes'])} takes; " +
          ", ".join(f"{k[:8]} {erg(v['nanoErg'])} ({v['takes']})" for k, v in s["byToken"].items()) + ".\n")


def dedupe(csvpath):
    """Line h lower total with gaps that share an N2T pool and overlap in blocks counted once (the largest)."""
    runs = collections.defaultdict(list)
    for r in csv.DictReader(open(csvpath)):
        runs[r["pair"]].append(r)
    gaps = []
    for pair, rs in runs.items():
        rs.sort(key=lambda r: int(r["fromHeight"]))
        cur = None
        for r in rs:
            a, b, p = int(r["fromHeight"]), int(r["toHeight"]), int(r["profitNanoErg"])
            pools = {r["buyPoolNft"], r["sellPoolNft"]}
            if cur and a == cur[1] + 1:
                cur = [cur[0], b, max(cur[2], p), cur[3] | pools]
            else:
                if cur:
                    gaps.append(cur)
                cur = [a, b, p, pools]
        if cur:
            gaps.append(cur)
    gaps.sort(key=lambda g: -g[2])
    kept = []
    for g in gaps:
        if any(g[0] <= k[1] and k[0] <= g[1] and g[3] & k[3] for k in kept):
            continue
        kept.append(g)
    return sum(g[2] for g in kept), len(kept), len(gaps)


def line_h(h):
    p = h["t2tPools"]
    ev = collections.Counter()
    for x in p:
        ev.update(x["eventsInWindow"])
    print(f"## h. Token-to-token pools\n")
    print(f"ErgoDEX v1 T2T pools: {len(p)} ({sum(x['unspent'] for x in p)} unspent now), "
          f"{sum(1 for x in p if sum(x['eventsInWindow'].values()))} active in the window, events {dict(ev)}; "
          f"{sum(1 for x in p if x['n2tPoolsX'] and x['n2tPoolsY'])} have an N2T pool on both sides. "
          f"N2T pools: {h['n2tPools']}.\n")
    c = h["cycles"]
    rows = sorted(c.items(), key=lambda kv: -kv[1]["lowerNanoErg"])
    L, Uu = sum(v["lowerNanoErg"] for v in c.values()), sum(v["upperNanoErg"] for v in c.values())
    L10 = sum(v["cap10"]["lowerNanoErg"] for v in c.values())
    out = []
    for k, v in rows:
        if v["lowerNanoErg"] < 0.01 * E:
            continue
        d = v["maxDetail"] or {}
        out.append([k, f"{v['blocksOpen']:,}", v["statesOpen"], erg(v["lowerNanoErg"]), erg(v["upperNanoErg"]),
                    erg(v["maxNanoErg"]), f"{v['maxAt']:,}" if v["maxAt"] else "", erg(d.get("capital", 0)),
                    erg(v["cap10"]["lowerNanoErg"]), d.get("fees", "")])
    table(["A/B : T2T pool", "blocks open", "states", "lower ERG", "upper ERG", "best ERG", "best at", "capital at best",
           "lower, capital ≤ 10 ERG", "fees (buy, T2T, sell)"], out)
    rest = [v for v in c.values() if 0 < v["lowerNanoErg"] < 0.01 * E]
    print(f"{len(rest)} more cycles under 0.01 ERG ({erg(sum(v['lowerNanoErg'] for v in rest))} together); "
          f"{sum(1 for v in c.values() if not v['statesOpen'])} never open.\n")
    dd = dedupe(os.path.join(D, "u1b-h-cycles-states.csv"))
    print(f"**Total: lower {erg(L)} ERG, upper {erg(Uu)} ERG; capital ≤ 10 ERG: lower {erg(L10)}.** "
          f"Gaps sharing an N2T pool in overlapping blocks counted once: **{erg(dd[0])} ERG** "
          f"({dd[1]} of {dd[2]} runs).\n")


def line_i(i):
    print(f"## i. Other kinds: unspent boxes at tip {i['atTip']:,}\n")
    rows = []
    for r in i["templates"]:
        extra = ""
        if "maturedNow" in r:
            extra = f"matured {r['maturedNow']} ({erg(r['maturedNanoErg'])} ERG)"
        if "executable" in r:
            ex = [e for e in r["executable"] if e.get("executable")]
            extra = f"executable now {len(ex)}, executor {erg(sum(e['executorNanoErg'] for e in ex))} ERG net of fee"
        rows.append([r["group"], r["name"], r["templateHash"][:8], r["unspent"], erg(r["nanoErg"], 3),
                     r["ageMedianBlocks"] if r["ageMedianBlocks"] is not None else "", extra])
    table(["group", "template", "hash", "unspent", "ERG held", "median age (blocks)", "note"], rows)


def line_j(j):
    print(f"## j. Takes needing capital, capped at {erg(j['capNanoErg'], 0)} ERG, net of "
          f"{erg(j['txFeeNanoErg'])} ERG per transaction\n")
    rows = []
    for k, v in sorted(j["c"].items(), key=lambda kv: -kv[1]["lowerNanoErg"]):
        rows.append(["c pool-pool", k, f"{v['blocksOpen']:,}", erg(v["lowerNanoErg"]), erg(v["upperNanoErg"]),
                     erg(v["maxNanoErg"]), erg((v["maxDetail"] or {}).get("capital", 0)), f"{v['riskShare']:.1%}"])
    for k, v in j["b"].items():
        if v["statesOpen"]:
            rows.append(["b bank-pool", k, f"{v['blocksOpen']:,}", erg(v["lowerNanoErg"]), erg(v["upperNanoErg"]),
                         erg(v["maxNanoErg"]), erg((v["maxDetail"] or {}).get("capital", 0)), f"{v['riskShare']:.1%}"])
    table(["line", "token", "blocks open", "lower ERG (net)", "upper ERG (net)", "best ERG (net)", "capital at best",
           "open blocks where leg 2 moved next block"], rows)
    if j.get("h"):
        hs = sorted(j["h"].items(), key=lambda kv: -kv[1]["cap10"]["lowerNanoErg"])
        table(["triangle (3 txs)", "lower ERG (gross, cap 10)", "best gross", "best net of 3 fees"],
              [[k, erg(v["cap10"]["lowerNanoErg"]), erg(v["cap10"]["maxNanoErg"]), erg(v["net3txBest"])]
               for k, v in hs[:12]])


if __name__ == "__main__":
    print("# U1b summary (generated by census/summarize_u1b.py)\n")
    for n, fn in (("f.json", line_f), ("k.json", line_k), ("g.json", line_g), ("h.json", line_h),
                  ("i.json", line_i), ("j.json", line_j)):
        d = load(n)
        if d:
            fn(d)
