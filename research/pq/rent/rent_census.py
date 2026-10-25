#!/usr/bin/env python3
"""Storage rent against the exposed-key stock: value-weighted tables over the whole unspent set.

Reuses census U1c's walk (research/agents/census/utxo.py): /boxes/unspent/stream by 1,536-block ranges through the
explorer mirror, raw responses cached (git-ignored) under research/agents/census/raw/u1c/. Output: out/height.json
(the pinned tip and parameters), out/rent-census.json (every number), out/summary.md (the tables, printed).

Usage: rent_census.py [--workers N] [--no-walk]   (--no-walk summarizes the cached ranges only)
"""
import argparse, json, math, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
CENSUS = os.path.normpath(os.path.join(HERE, "..", "..", "agents", "census"))
sys.path.insert(0, CENSUS)
import explorer as X  # noqa: E402
import utxo as U  # noqa: E402

OUT = os.path.join(HERE, "out")
PERIOD = 1_051_200
YEAR = 262_800
BIG = 1_000_000 * 10**9  # non-P2PK boxes above this are protocol boxes (re-emission, emission); excluded and listed

AGE_BUCKETS = [(0, "<1y"), (1, "1-2y"), (2, "2-3y"), (3, "3-4y"), (4, "4-5y"), (5, ">=5y")]
CYCLE_BUCKETS = [(1, "1 (consumed whole)"), (10, "2-10"), (100, "11-100"), (1000, "101-1000"), (10**12, ">1000")]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def erg(n):
    return n / 10**9


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-walk", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    hp = os.path.join(OUT, "height.json")
    if os.path.exists(hp):
        st = json.load(open(hp))
    else:
        info = X.get("/info", cache=False)
        st = {"height": info["height"], "endpoint": X.EXPLORER, "params": info["params"], "readAt": time.time()}
        json.dump(st, open(hp, "w"), indent=1)
    tip, factor = st["height"], st["params"]["storageFeeFactor"]
    log(f"tip {tip} factor {factor} endpoint {st['endpoint']}")
    ranges = [(lo, min(lo + U.STEP - 1, tip)) for lo in range(0, tip + 1, U.STEP)]
    if not a.no_walk:
        t0 = time.time()
        U.walk(tip, workers=a.workers, log=log)
        log(f"walk done: {len(ranges)} ranges in {time.time() - t0:.0f}s")

    tot = {"boxes": 0, "nanoErg": 0}
    p2pk = {"boxes": 0, "nanoErg": 0}
    age = {k: {"boxes": 0, "nanoErg": 0} for _, k in AGE_BUCKETS}
    cyc = {k: {"boxes": 0, "nanoErg": 0} for _, k in CYCLE_BUCKETS}
    elig = {"boxes": 0, "nanoErg": 0}  # past rent age now
    mat = {"boxes": 0, "nanoErg": 0, "taken": 0, "consumedWhole": 0, "consumedWholeNanoErg": 0}  # reach rent age in 1y
    contracts = {"boxes": 0, "nanoErg": 0}
    protocol = []
    missing = []
    for lo, hi in ranges:
        p = U._range_path(lo, hi)
        if not os.path.exists(p):
            missing.append([lo, hi])
            continue
        _, boxes = U.read_range(p)
        for b in boxes:
            c = U.compact(b)
            v = c["v"]
            tot["boxes"] += 1
            tot["nanoErg"] += v
            if c["th"] != "p2pk":
                if v >= BIG:
                    protocol.append({"id": c["id"], "template": c["th"], "nanoErg": v})
                else:
                    contracts["boxes"] += 1
                    contracts["nanoErg"] += v
                continue
            p2pk["boxes"] += 1
            p2pk["nanoErg"] += v
            years = (tip - c["sh"]) // YEAR
            key = next(k for lim, k in AGE_BUCKETS if years <= lim) if years < 5 else ">=5y"
            age[key]["boxes"] += 1
            age[key]["nanoErg"] += v
            rent = factor * c["size"]
            cycles = 1 if v <= rent else math.ceil(v / rent)
            key = next(k for lim, k in CYCLE_BUCKETS if cycles <= lim)
            cyc[key]["boxes"] += 1
            cyc[key]["nanoErg"] += v
            rent_age = tip - c["ch"]
            if rent_age >= PERIOD:
                elig["boxes"] += 1
                elig["nanoErg"] += v
            if rent_age >= PERIOD - YEAR:
                mat["boxes"] += 1
                mat["nanoErg"] += v
                if v <= rent:
                    mat["taken"] += v
                    mat["consumedWhole"] += 1
                    mat["consumedWholeNanoErg"] += v
                else:
                    mat["taken"] += rent
    nonproto = tot["nanoErg"] - sum(x["nanoErg"] for x in protocol)
    res = {"height": tip, "endpoint": st["endpoint"], "storageFeeFactor": factor, "period": PERIOD, "year": YEAR,
           "missingRanges": missing, "total": tot, "p2pk": p2pk, "contracts": contracts, "protocolBoxes": protocol,
           "nonProtocolNanoErg": nonproto, "p2pkByAge": age, "p2pkByCycles": cyc, "p2pkPastRentAge": elig,
           "p2pkMaturingWithin1y": mat}
    json.dump(res, open(os.path.join(OUT, "rent-census.json"), "w"), indent=1)

    L = []
    L.append(f"# Rent census (height {tip:,}, {st['endpoint']}, storageFeeFactor {factor:,})\n")
    if missing:
        L.append(f"**{len(missing)} ranges missing from the walk; totals are incomplete.**\n")
    L.append(f"Unspent boxes: {tot['boxes']:,}, {erg(tot['nanoErg']):,.1f} ERG. P2PK: {p2pk['boxes']:,} boxes, "
             f"{erg(p2pk['nanoErg']):,.1f} ERG. Contracts: {contracts['boxes']:,} boxes, "
             f"{erg(contracts['nanoErg']):,.1f} ERG. Protocol boxes excluded from non-protocol supply: "
             + ", ".join(f"{x['template'][:12]} {erg(x['nanoErg']):,.1f} ERG" for x in protocol)
             + f". Non-protocol supply: {erg(nonproto):,.1f} ERG.\n")
    L.append("## P2PK ERG by age of the box (settlement height)\n")
    L.append("| age | boxes | ERG | share of P2PK ERG |\n|---|---|---|---|")
    for _, k in AGE_BUCKETS:
        L.append(f"| {k} | {age[k]['boxes']:,} | {erg(age[k]['nanoErg']):,.1f} | {100*age[k]['nanoErg']/p2pk['nanoErg']:.2f}% |")
    L.append("\n## P2PK ERG by rent cycles to exhaustion (4 years per cycle)\n")
    L.append("| cycles | boxes | ERG | share of P2PK ERG |\n|---|---|---|---|")
    for _, k in CYCLE_BUCKETS:
        L.append(f"| {k} | {cyc[k]['boxes']:,} | {erg(cyc[k]['nanoErg']):,.1f} | {100*cyc[k]['nanoErg']/p2pk['nanoErg']:.3f}% |")
    L.append("\n## Rent eligibility (creation height)\n")
    L.append(f"- Past rent age now: {elig['boxes']:,} boxes, {erg(elig['nanoErg']):,.1f} ERG = "
             f"{100*elig['nanoErg']/nonproto:.3f}% of non-protocol supply.")
    L.append(f"- Reaching rent age within 365 days: {mat['boxes']:,} boxes, {erg(mat['nanoErg']):,.1f} ERG; one claim "
             f"on each takes {erg(mat['taken']):,.1f} ERG = {100*mat['taken']/max(mat['nanoErg'],1):.2f}% of that value; "
             f"{mat['consumedWhole']:,} boxes ({erg(mat['consumedWholeNanoErg']):,.1f} ERG) are consumed whole; the rest "
             f"is recreated under the same P2PK tree.")
    txt = "\n".join(L) + "\n"
    open(os.path.join(OUT, "summary.md"), "w").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
