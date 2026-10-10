#!/usr/bin/env python3
"""U1c: every keyless spending path on mainnet, read from the scripts (prompts/census-u1c.md).

Lines, each a subcommand writing census/u1c/<line>.json:
  walk  fetch the whole unspent set by inclusion height (census/utxo.py) up to a fixed height H
  l     the template set: per template, unspent count, ERG, value and creation-height distributions
  m     every spending path of every script, classified (census/paths.py)
  n     what each keyless path pays and costs
  o     protocol funds at risk from storage rent
  p     candidates: unsigned transactions in census/u1c/candidates/

Same source and rules as U1b (census-u1b.py): the Cornell explorer mirror, raw responses cached under
census/raw/ (git-ignored), integer arithmetic matching each contract.

usage: census-u1c.py LINE [--height H] [--workers N]
"""
import argparse, collections, gzip, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "census"))
import explorer as X  # noqa: E402
import utxo as U  # noqa: E402

OUT = os.path.join(HERE, "census", "u1c")
WORK = os.path.join(HERE, "census", "out")
RENT_PERIOD = 1_051_200
STATE = os.path.join(OUT, "height.json")


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def save(name, obj, indent=1):
    p = os.path.join(OUT, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(obj, f, indent=indent, default=str)
    log(f"wrote {p} ({os.path.getsize(p)} bytes)")
    return p


def load(name):
    with open(os.path.join(OUT, name)) as f:
        return json.load(f)


def cmd_walk(a):
    if os.path.exists(STATE):
        st = json.load(open(STATE))
    else:
        info = X.get("/info", cache=False)
        st = {"height": info["height"], "endpoint": X.EXPLORER, "params": info["params"], "readAt": time.time()}
        save("height.json", st)
    t0 = time.time()
    ranges = U.walk(st["height"], workers=a.workers, log=log)
    log(f"walk done: {len(ranges)} ranges to {st['height']} in {time.time() - t0:.0f}s")


def ranges_of(h):
    return [(lo, min(lo + U.STEP - 1, h)) for lo in range(0, h + 1, U.STEP)]


def _q(xs, qs=(0, 0.1, 0.25, 0.5, 0.75, 0.9, 1)):
    xs = sorted(xs)
    return [xs[min(len(xs) - 1, int(q * (len(xs) - 1) + 0.5))] for q in qs] if xs else []


def cmd_l(a):
    """One pass over the walked ranges: compact boxes, per-template counts and distributions, and up to three
    sample boxes per template (largest value, oldest, fewest registers) for line m."""
    st = json.load(open(STATE))
    H = st["height"]
    os.makedirs(WORK, exist_ok=True)
    per = collections.defaultdict(lambda: {"boxes": 0, "nanoErg": 0, "values": [], "ch": [], "sizes": [],
                                           "tokens": collections.Counter(), "regsets": collections.Counter()})
    samples = {}
    fetched, n = [], 0
    with gzip.open(os.path.join(WORK, "u1c-utxo.jsonl.gz"), "wt") as f:
        for lo, hi in ranges_of(H):
            p = U._range_path(lo, hi)
            if not os.path.exists(p):
                log(f"missing range {lo}-{hi}")
                continue
            head, boxes = U.read_range(p)
            fetched.append(head["fetchedAt"])
            for b in boxes:
                if not isinstance(b, dict) or "boxId" not in b:
                    continue
                c = U.compact(b)
                f.write(json.dumps(c) + "\n")
                n += 1
                r = per[c["th"]]
                r["boxes"] += 1
                r["nanoErg"] += c["v"]
                r["values"].append(c["v"])
                r["ch"].append(c["ch"])
                r["sizes"].append(c["size"])
                for t, _ in c["tok"]:
                    r["tokens"][t] += 1
                r["regsets"]["".join(c["regs"])] += 1
                if c["th"] == "p2pk":
                    continue
                s = samples.setdefault(c["th"], {})
                full = {k: b[k] for k in ("boxId", "transactionId", "index", "value", "creationHeight",
                                          "settlementHeight", "ergoTree", "ergoTreeConstants", "ergoTreeScript",
                                          "address", "assets", "additionalRegisters")}
                if "maxValue" not in s or b["value"] > s["maxValue"]["value"]:
                    s["maxValue"] = full
                if "oldest" not in s or b["creationHeight"] < s["oldest"]["creationHeight"]:
                    s["oldest"] = full
                if "fewestRegs" not in s or len(b["additionalRegisters"] or {}) < len(s["fewestRegs"]["additionalRegisters"] or {}):
                    s["fewestRegs"] = full
    rows = []
    for th, r in per.items():
        rent_at = [ch + RENT_PERIOD for ch in r["ch"]]
        fee = st["params"]["storageFeeFactor"]
        rows.append({
            "templateHash": th, "boxes": r["boxes"], "nanoErg": r["nanoErg"],
            "valueQuantiles": _q(r["values"]), "creationHeightQuantiles": _q(r["ch"]),
            "sizeQuantiles": _q(r["sizes"]),
            "rentAgeNow": sum(1 for x in rent_at if x <= H),
            "rentAgeIn30d": sum(1 for x in rent_at if H < x <= H + 21_600),
            "rentAgeIn90d": sum(1 for x in rent_at if H < x <= H + 64_800),
            "rentAgeIn365d": sum(1 for x in rent_at if H < x <= H + 262_800),
            "belowOneRentClaim": sum(1 for v, z in zip(r["values"], r["sizes"]) if v < z * fee),
            "tokenIds": len(r["tokens"]), "topTokens": r["tokens"].most_common(3),
            "registerSets": r["regsets"].most_common(4),
        })
    rows.sort(key=lambda x: -x["nanoErg"])
    st.update({"boxes": n, "ranges": len(fetched), "firstRangeRead": min(fetched), "lastRangeRead": max(fetched),
               "templates": len(rows)})
    save("height.json", st)
    with gzip.open(os.path.join(WORK, "u1c-samples.json.gz"), "wt") as f:
        json.dump(samples, f)
    save("l.json", {"height": H, "endpoint": st["endpoint"], "boxes": n, "templates": rows})


def cmd_m(a):
    """Every path of every script: the classifier (census/paths.py) over up to three sample boxes per template;
    per-box unreachability from the registers each path reads with .get."""
    import paths as PA
    import names as NM
    lrows = {r["templateHash"]: r for r in load("l.json")["templates"]}
    H = load("l.json")["height"]
    with gzip.open(os.path.join(WORK, "u1c-samples.json.gz"), "rt") as f:
        samples = json.load(f)
    out = {}
    for th, s in samples.items():
        res = {}
        for which in ("maxValue", "oldest", "fewestRegs"):
            b = s[which]
            if any(b["boxId"] == r["box"] for r in res.values()):
                continue
            an = PA.analyse(b["ergoTreeScript"], b["ergoTreeConstants"], H)
            res[which] = {"box": b["boxId"], "regs": sorted(b["additionalRegisters"] or {}), **an}
        main = res["maxValue"]
        classes = sorted({p["class"] for p in main["paths"]})
        differs = any(sorted({p["class"] for p in r["paths"]}) != classes for r in res.values() if r["parsed"])
        nm = NM.name(th)
        out[th] = {"templateHash": th, "name": nm["name"], "nameHow": nm["how"],
                   "boxes": lrows[th]["boxes"], "nanoErg": lrows[th]["nanoErg"],
                   "parsed": main["parsed"], "error": main["error"], "classes": classes,
                   "classesDifferAcrossSamples": differs,
                   "paths": [dict(p, status="SUSPECTED") for p in main["paths"]],
                   "sampleBox": main["box"], "samples": {k: {kk: v[kk] for kk in
                   ("box", "regs", "parsed", "error")} | {"classes": sorted({p["class"] for p in v["paths"]})}
                   for k, v in res.items()}}
    # per box: a path that reads SELF.Rn.get is unreachable on a box without Rn
    need = {th: [set(p["needsRegisters"]) for p in r["paths"]] for th, r in out.items()}
    unreach = collections.defaultdict(lambda: collections.Counter())
    allpaths_dead = collections.Counter()
    allpaths_dead_erg = collections.Counter()
    with gzip.open(os.path.join(WORK, "u1c-utxo.jsonl.gz"), "rt") as f:
        for line in f:
            c = json.loads(line)
            ps = need.get(c["th"])
            if not ps:
                continue
            have = set(c["regs"])
            dead = [i for i, req in enumerate(ps) if not req <= have]
            for i in dead:
                unreach[c["th"]][i] += 1
            if len(dead) == len(ps):
                allpaths_dead[c["th"]] += 1
                allpaths_dead_erg[c["th"]] += c["v"]
    for th, r in out.items():
        for i, p in enumerate(r["paths"]):
            p["boxesUnreachable"] = unreach[th][i]
        r["boxesWithNoReachablePath"] = allpaths_dead[th]
        r["nanoErgWithNoReachablePath"] = allpaths_dead_erg[th]
    KEYS = {"key", "key (miner)", "key (secret)"}
    scripts = {}
    for th, r in out.items():
        keyless = any(p["class"] not in KEYS for p in r["paths"])
        if keyless or not r["parsed"] or r["error"]:
            scripts[th] = {"script": samples[th]["maxValue"]["ergoTreeScript"],
                           "constants": samples[th]["maxValue"]["ergoTreeConstants"]}
    rows = sorted(out.values(), key=lambda x: -x["nanoErg"])
    save("m.json", {"height": load("l.json")["height"], "templates": rows}, indent=None)
    save("m-scripts.json", {"note": "decompiled script and constants of a sample box, for templates with a "
         "non-key path or no clean parse (key-only scripts omitted; refetch from the sampleBox id)",
         "scripts": scripts}, indent=None)


def traced():
    """Hand traces (census/u1c/traced.json): per template, paths read from the script by hand, CONFIRMED."""
    p = os.path.join(OUT, "traced.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def cmd_o(a):
    """Protocol funds at risk from storage rent: contract boxes worth less than one rent claim (size x the fee
    factor read from the chain), by when they reach rent age; their ERG and tokens; whether a keyless path lets a
    third party preserve them."""
    st = json.load(open(STATE))
    H, fee = st["height"], st["params"]["storageFeeFactor"]
    m = {r["templateHash"]: r for r in load("m.json")["templates"]}
    tr = traced()
    W = {"now": (None, H), "30d": (H, H + 21_600), "90d": (H, H + 64_800), "365d": (H, H + 262_800)}
    per = collections.defaultdict(lambda: {w: {"boxes": 0, "nanoErg": 0, "tokens": collections.Counter()} for w in W})
    allb = collections.Counter()
    with gzip.open(os.path.join(WORK, "u1c-utxo.jsonl.gz"), "rt") as f:
        for line in f:
            c = json.loads(line)
            if c["th"] == "p2pk":
                continue
            allb[c["th"]] += 1
            if c["v"] >= c["size"] * fee:
                continue
            due = c["ch"] + RENT_PERIOD
            for w, (lo, hi) in W.items():
                if (lo is None and due <= hi) or (lo is not None and lo < due <= hi):
                    r = per[c["th"]][w]
                    r["boxes"] += 1
                    r["nanoErg"] += c["v"]
                    for t, n in c["tok"]:
                        r["tokens"][t] += n
    rows = []
    for th, r in per.items():
        if not any(r[w]["boxes"] for w in W):
            continue
        mm = m.get(th, {})
        t = tr.get(th)
        preserve = t.get("preserve") if t else None
        rows.append({"templateHash": th, "name": (t or {}).get("name") or mm.get("name"),
                     "boxesInTemplate": allb[th],
                     **{w: {"boxes": r[w]["boxes"], "nanoErg": r[w]["nanoErg"], "tokenIds": len(r[w]["tokens"]),
                            "topTokens": r[w]["tokens"].most_common(3)} for w in W},
                     "classes": mm.get("classes"), "preserve": preserve,
                     "preserveStatus": "CONFIRMED" if t else "SUSPECTED"})
    rows.sort(key=lambda x: -(x["365d"]["nanoErg"] + x["now"]["nanoErg"]))
    save("o.json", {"height": H, "storageFeeFactor": fee, "templates": rows})


def u1b():
    """census-u1b.py as a module, its outputs redirected to census/u1c/ (its offer and order code is reused)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("census_u1b", os.path.join(HERE, "census-u1b.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.OUT = OUT
    return m


def live_boxes(th, cap=5000):
    """Every unspent box of a template now (not cached: candidates are built on boxes as they stand)."""
    base = f"/boxes/unspent/byErgoTreeTemplateHash/{th}?"
    total = X.get(f"{base}offset=0&limit=1", cache=False)["total"]
    out = []
    for off in range(0, min(total, cap), 100):
        out += X.get(f"{base}offset={off}&limit=100", cache=False)["items"]
    return out


STAKING = ("278ccff223ae2d7debac0626704be6046ade899969970565cf6395793ee84d02",
           "b924a4f735730da5d8dc4cd658ef2308fb520d38510aed08db549be989db2943")
PAIDEIA_MERGE = ("37142e749788b64ad54de21c9fae4269955e214d23dcba961539b26e690b5573",
                 "5b41af39fc2d6a5b27a726c68e739279d0915c438d3c8491ede265345e8dde61")
FREE = "e9d13195d73d90fde24ade268844724417323260456736559cf89a18a3eb696a"
TX_FEE = 1_100_000


def cmd_n(a):
    """What each keyless path pays: takes computed on the live boxes of every template whose keyless path pays
    the executor (from the hand traces), plus U1b's offer (g) and SwapSell v1 order code rerun now."""
    tip = X.tip()
    tr = traced()
    out = {"tip": tip, "endpoint": X.EXPLORER, "takes": []}
    # 1. consolidation bounties (staking incentive): boxes <= 0.1 ERG, no tokens or registers, grouped by tree
    for th in STAKING:
        bx = [b for b in live_boxes(th) if b["value"] <= 100_000_000 and not b["assets"]
              and not b["additionalRegisters"]]
        by = collections.Counter(b["ergoTree"] for b in bx)
        groups = [n for n in by.values() if n >= 2]
        out["takes"].append({"templateHash": th, "kind": "consolidation bounty", "boxes": sum(groups),
                             "trees": len(groups), "executorNanoErg": 500_000 * sum(groups),
                             "note": "0.0005 ERG per merged box; the 0.001 ERG third output pays the fee"})
    # 2. Paideia treasury merge: >= 5 boxes of one exact tree, at most 0.002 ERG per transaction
    for th in PAIDEIA_MERGE:
        bx = live_boxes(th)
        by = collections.Counter(b["ergoTree"] for b in bx)
        mergeable = {t: n for t, n in by.items() if n >= 5}
        # inputs: at most 0.002 ERG taken per transaction; 5+ inputs per transaction
        txs = sum(n // 5 for n in mergeable.values())
        out["takes"].append({"templateHash": th, "kind": "Paideia treasury merge", "boxes": sum(by.values()),
                             "trees": len(by), "treesWith5": len(mergeable), "txs": txs,
                             "executorNanoErg": 2_000_000 * txs, "netOfFeeNanoErg": (2_000_000 - TX_FEE) * txs,
                             "note": "at most 0.002 ERG per transaction, the miner fee paid from it"})
    # 3. Paideia refresh (later): boxes of the Paideia templates 504,000 blocks after creation
    for th, t in tr.items():
        for p in t["paths"]:
            w = p.get("whenRule")
            if p["class"] != "keyless later" or not w or w.get("kind") != "creationPlus":
                continue
            bx = live_boxes(th)
            due = [b["creationHeight"] + w["blocks"] for b in bx]
            out["takes"].append({"templateHash": th, "kind": "refresh bounty (later)", "boxes": len(bx),
                                 "dueNow": sum(1 for d in due if d <= tip),
                                 "dueIn30d": sum(1 for d in due if tip < d <= tip + 21_600),
                                 "firstDue": min(due) if due else None,
                                 "executorNanoErgPerBox": 2_000_000})
    # 4. free boxes: OUTPUTS.size == n
    bx = live_boxes(FREE)
    import paths as PA
    ns = collections.Counter(PA.parse_constants(b["ergoTreeConstants"]).get(0) for b in bx)
    out["takes"].append({"templateHash": FREE, "kind": "free box (one-output transaction)", "boxes": len(bx),
                         "nanoErg": sum(b["value"] for b in bx), "outputsRequired": dict(ns),
                         "boxIds": [b["boxId"] for b in bx],
                         "note": "a one-output transaction carries no fee box: own block only [inferred]"})
    # 5. U1b line g (offers against N2T pools) and SwapSell v1 executor fees, rerun now
    M = u1b()
    M.line_g(a)
    os.replace(os.path.join(OUT, "g.json"), os.path.join(OUT, "n-offers.json"))
    g = load("n-offers.json")
    out["takes"].append({"kind": "fixed-price offers against N2T pools (U1b g rerun)", "atTip": g["atTip"],
                         "unspent": g["unspent"], "takenInTurnNanoErg": g["sequential"]["totalNanoErg"],
                         "takes": g["sequential"]["takes"]})
    ss = M.swapsell_v1(M.unspent_boxes(M.full_hash("36d1944f"))[0])
    out["takes"].append({"kind": "ErgoDEX N2T SwapSell v1 executor fee", "orders": len(ss),
                         "executable": sum(1 for x in ss if x.get("executable")),
                         "executorNanoErg": sum(max(0, x.get("executorNanoErg") or 0) for x in ss
                                                if x.get("executable")), "rows": ss})
    save("n.json", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("line")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    {"walk": cmd_walk, "l": cmd_l, "m": cmd_m, "o": cmd_o, "n": cmd_n}[a.line](a)


if __name__ == "__main__":
    main()
