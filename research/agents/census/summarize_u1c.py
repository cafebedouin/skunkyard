#!/usr/bin/env python3
"""U1c tables: census/u1c/{l,m,n,o}.json and the candidates -> census/u1c/summary.md (every table of CENSUS-U1C.md,
longer than the report prints)."""
import collections, glob, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "u1c")
KEY = ("key", "key (miner)", "key (secret)")


def load(n):
    return json.load(open(os.path.join(OUT, n)))


def erg(n, d=4):
    return f"{n / 1e9:,.{d}f}"


def main():
    st = load("height.json")
    l, m, o = load("l.json"), load("m.json"), load("o.json")
    tr = load("traced.json") if os.path.exists(os.path.join(OUT, "traced.json")) else {}
    H = st["height"]
    L = []
    w = L.append
    w(f"# U1c summary (height {H:,}, {st['endpoint']})\n")
    rows = l["templates"]
    p2pk = [r for r in rows if r["templateHash"] == "p2pk"]
    contract = [r for r in rows if r["templateHash"] != "p2pk"]
    w(f"Unspent boxes walked: {l['boxes']:,} in {st.get('ranges')} ranges; templates: {len(rows):,} "
      f"({len(contract):,} contract templates + P2PK).")
    if p2pk:
        r = p2pk[0]
        w(f"P2PK: {r['boxes']:,} boxes, {erg(r['nanoErg'], 1)} ERG; at rent age now {r['rentAgeNow']:,}, "
          f"within 30 d {r['rentAgeIn30d']:,}, 90 d {r['rentAgeIn90d']:,}, 365 d {r['rentAgeIn365d']:,}.")
    w(f"Contract boxes: {sum(r['boxes'] for r in contract):,}, {erg(sum(r['nanoErg'] for r in contract), 1)} ERG.\n")

    # line l: top templates by ERG and by boxes
    mm = {r["templateHash"]: r for r in m["templates"]}
    w("## l. Templates by ERG held (top 40)\n")
    w("| template | name | boxes | ERG | value p10 / p50 / p90 (ERG) | created p10 / p50 / p90 | rent age now / 30 d / 365 d |")
    w("|---|---|---|---|---|---|---|")
    for r in contract[:40]:
        v, c = r["valueQuantiles"], r["creationHeightQuantiles"]
        nm = (tr.get(r["templateHash"], {}).get("name") or mm.get(r["templateHash"], {}).get("name") or "")[:60]
        w(f"| `{r['templateHash'][:12]}` | {nm} | {r['boxes']:,} | {erg(r['nanoErg'], 2)} | "
          f"{erg(v[1], 4)} / {erg(v[3], 4)} / {erg(v[5], 4)} | {c[1]:,} / {c[3]:,} / {c[5]:,} | "
          f"{r['rentAgeNow']} / {r['rentAgeIn30d']} / {r['rentAgeIn365d']} |")
    w("")
    w("## l. Templates by box count (top 25)\n")
    w("| template | name | boxes | ERG | below one rent claim | rent age within 365 d |")
    w("|---|---|---|---|---|---|")
    for r in sorted(contract, key=lambda x: -x["boxes"])[:25]:
        nm = (tr.get(r["templateHash"], {}).get("name") or mm.get(r["templateHash"], {}).get("name") or "")[:60]
        w(f"| `{r['templateHash'][:12]}` | {nm} | {r['boxes']:,} | {erg(r['nanoErg'], 2)} | "
          f"{r['belowOneRentClaim']:,} | {r['rentAgeNow'] + r['rentAgeIn365d']:,} |")
    w("")

    # line m: classes
    cls = collections.Counter()
    clsb = collections.Counter()
    clse = collections.Counter()
    unparsed = []
    for r in m["templates"]:
        if not r["parsed"] or (r["error"] and not r["paths"]):
            unparsed.append(r)
            continue
        cs = set(r["classes"])
        top = ("keyless now" if "keyless now" in cs else "keyless later" if "keyless later" in cs else
               "keyless with input" if "keyless with input" in cs else "key only" if cs & set(KEY) else
               "unreachable only" if cs == {"unreachable"} else "no path")
        cls[top] += 1
        clsb[top] += r["boxes"]
        clse[top] += r["nanoErg"]
    w("## m. Templates by their most open path (classifier, SUSPECTED unless traced)\n")
    w("| most open path | templates | boxes | ERG |")
    w("|---|---|---|---|")
    for k in ("keyless now", "keyless later", "keyless with input", "key only", "unreachable only", "no path"):
        w(f"| {k} | {cls[k]:,} | {clsb[k]:,} | {erg(clse[k], 2)} |")
    w(f"| not decompiled or not split | {len(unparsed):,} | {sum(r['boxes'] for r in unparsed):,} | "
      f"{erg(sum(r['nanoErg'] for r in unparsed), 2)} |")
    w("")
    w("Not decompiled or not split into paths:\n")
    w("| template | name | boxes | ERG | why |")
    w("|---|---|---|---|---|")
    for r in sorted(unparsed, key=lambda x: -x["nanoErg"]):
        w(f"| `{r['templateHash'][:12]}` | {r['name'][:50]} | {r['boxes']:,} | {erg(r['nanoErg'], 3)} | "
          f"{(r['error'] or '')[:60]} |")
    w("")
    dead = [r for r in m["templates"] if r.get("boxesWithNoReachablePath")]
    w("Boxes on which every path reads a register the box lacks (unreachable per box, SUSPECTED):\n")
    w("| template | name | boxes | of | ERG |")
    w("|---|---|---|---|---|")
    for r in sorted(dead, key=lambda x: -x["nanoErgWithNoReachablePath"]):
        w(f"| `{r['templateHash'][:12]}` | {r['name'][:50]} | {r['boxesWithNoReachablePath']:,} | {r['boxes']:,} | "
          f"{erg(r['nanoErgWithNoReachablePath'], 3)} |")
    w("")

    # line o
    w("## o. Contract boxes worth less than one rent claim, by when they reach rent age\n")
    w("| template | name | boxes in template | at age now: boxes / ERG | in 30 d | in 90 d | in 365 d | tokens (365 d) | "
      "keyless path to preserve |")
    w("|---|---|---|---|---|---|---|---|---|")
    for r in o["templates"][:60]:
        f = lambda k: f"{r[k]['boxes']:,} / {erg(r[k]['nanoErg'], 3)}"  # noqa: E731
        pres = r["preserve"] or ("none found by the classifier" if r["classes"] and not
                                 (set(r["classes"]) - set(KEY) - {"unreachable"}) else
                                 "classifier: " + ", ".join(c for c in (r["classes"] or []) if c not in KEY))
        w(f"| `{r['templateHash'][:12]}` | {(r['name'] or '')[:40]} | {r['boxesInTemplate']:,} | {f('now')} | "
          f"{f('30d')} | {f('90d')} | {f('365d')} | {r['365d']['tokenIds']} | {pres[:80]} ({r['preserveStatus']}) |")
    w("")
    tot = {k: (sum(r[k]["boxes"] for r in o["templates"]), sum(r[k]["nanoErg"] for r in o["templates"]))
           for k in ("now", "30d", "90d", "365d")}
    w("Totals: " + "; ".join(f"{k} {v[0]:,} boxes {erg(v[1], 2)} ERG" for k, v in tot.items()) + "\n")

    # candidates
    w("## p. Candidates\n")
    w("| file | kind | inputs | payout ERG | height |")
    w("|---|---|---|---|---|")
    for p in sorted(glob.glob(os.path.join(OUT, "candidates", "*.meta.json"))):
        c = json.load(open(p))
        w(f"| `{os.path.basename(p).replace('.meta', '')}` | {c['kind']} | {c['inputs']} | "
          f"{erg(c['payoutNanoErg'], 4)} | {c['height']:,} |")
    open(os.path.join(OUT, "summary.md"), "w").write("\n".join(L) + "\n")
    print(f"wrote {os.path.join(OUT, 'summary.md')}")


if __name__ == "__main__":
    main()
