#!/usr/bin/env python3
"""Experiment 1: one parameterised policy template (PolicyTemplate.es), on the `policy` devnet.

  --stage 1a   compile and size, no spends:
               form A, substitution: each $ON_* replaced by true/false before compiling (13 combinations);
               form B, tree constants: the all-on tree, its switch constants located by flipping one switch at a
                       time and diffing, then each combination made off-chain by rewriting those constants;
               form C, a family: each switched-off block cut from the source (region markers), which is what "a
                       small family of templates" would be (added: form A did not fold, see README);
               one deposit per tree (one token, no registers) for box bytes; KeepAliveAddress.es and QVault.es
               recompiled at their READMEs' constants in the same session.
  --stage 1b   transaction cost per path, with experiment 2's tested two-step block (run after experiment 2).

Writes results.json (cases for 1b; trees and sizes for both) and the *.tree files.
"""
import argparse, hashlib, itertools, json, os, sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from common import *  # noqa: E402

SW = ["HASH", "SIGNAL", "KA", "TWOSTEP", "LIMIT"]
KA_CONST = {"$PER_INPUTL": "500000L", "$REFRESHL": "2000000L", "$PERIOD": "40", "$WINDOW": "20", "$SLACK": "10"}
LIMIT = 100_000_000
DELAY = 15


def combos():
    on = {s: False for s in SW}
    rows = [("owner", dict(on))]
    for s in SW:
        rows.append((f"owner+{s.lower()}", dict(on, **{s: True})))
    allon = {s: True for s in SW}
    rows.append(("all", dict(allon)))
    for s in SW:
        rows.append((f"all-{s.lower()}", dict(allon, **{s: False})))
    rows.append(("qvault-profile", dict(on, HASH=True, SIGNAL=True, KA=True)))
    return rows


def form_a(src, sw):
    return src.replace("//<", "//").replace("//>", "//"), {f"$ON_{s}": ("true" if sw[s] else "false") for s in SW}


def form_c(src, sw):
    lines, outl, skip = src.splitlines(), [], None
    for ln in lines:
        st = ln.strip()
        if st.startswith("//<"):
            name, off = st[3:].split(" ", 1)
            if not sw[name]:
                skip = name
                outl.append("  " + off)
            continue
        if st.startswith("//>"):
            skip = None
            continue
        if skip is None:
            outl.append(ln)
    s = "\n".join(outl)
    return s, {f"$ON_{k}": "true" for k in SW}


def template_hash(t):
    return census_trees.template_hash(t)


def stage_1a(run, consts):
    src = (HERE / "PolicyTemplate.es").read_text()
    out = {"A": {}, "C": {}}
    for name, sw in combos():
        for form, fn in (("A", form_a), ("C", form_c)):
            s, subs = fn(src, sw)
            try:
                t, addr = compile_tree(s, {**consts, **subs})
            except CompileError as e:
                out[form][name] = {"error": str(e)[:400]}
                print(form, name, "COMPILE ERROR", str(e)[:200])
                continue
            out[form][name] = {"tree": t, "address": addr, "tree_bytes": len(t) // 2, "switches": sw,
                               "template_hash": template_hash(t)}
            print(form, f"{name:<16}", len(t) // 2, "B", template_hash(t)[:12])
    # form B: locate the switch constants in the all-on tree
    allon = out["A"]["all"]["tree"]
    cs = constants(allon)
    pos = {}
    for s in SW:
        flipped = compile_tree(*[(x[0], {**consts, **x[1]}) for x in [form_a(src, {k: (k != s) for k in SW})]][0])[0]
        cf = constants(flipped)
        diff = [i for i, (a, b) in enumerate(zip(cs, cf)) if a[3] != b[3]]
        same_len = len(flipped) == len(allon)
        rest_same = same_len and all(allon[2 * i:2 * i + 2] == flipped[2 * i:2 * i + 2]
                                     for i in range(len(allon) // 2)
                                     if not any(cs[d][1] <= i < cs[d][2] for d in diff))
        pos[s] = {"constant_indices": diff, "same_length": same_len, "only_that_constant_differs": rest_same}
        print("switch", s, pos[s])
    formb = {"tree_bytes": len(allon) // 2, "constants": len(cs), "switch_positions": pos,
             "boolean_constants": sum(1 for c in cs if c[0] == ("p", 1))}
    # rewrite each combination off-chain and compare with form A's compile of it
    rewrites = {}
    for name, sw in combos():
        t = bytearray.fromhex(allon)
        for s in SW:
            for ci in pos[s]["constant_indices"]:
                _, st, en, val = cs[ci]
                t[en - 1] = 1 if sw[s] else 0
        rewrites[name] = {"equals_form_A_compile": t.hex() == out["A"][name].get("tree"),
                          "template_hash": template_hash(t.hex())}
    formb["rewrites"] = rewrites
    return out, formb


def stage_1b():
    """Cost per path. Every compared pair has the same transaction shape. Forms A and B are one tree (1a), so the two
    pair kinds are: switched-off (form A "all" vs "all - X") and absent (form C "all" vs "all - X")."""
    run = Run("1b-template-cost", HERE)
    owner, oracle = pk_of(A), pk_of(A, 1)
    seed = os.urandom(32).hex()
    commit = wots("commit", seed, "32", "16")["commitment"]
    qnft = issue("QDAY-1B")
    qtree, qaddr = compile_tree((HERE.parent.parent / "qvault" / "QDay.es").read_text(), {"$ORACLE": oracle})
    flag = at(send([{"address": qaddr, "value": 10_000_000, "assets": [{"tokenId": qnft, "amount": 1}],
                     "registers": {"R4": FALSE}}]), qtree)[0]
    pend = compile_tree((HERE.parent / "2-twostep" / "Pending.es").read_text(),
                        {"$OWNER": owner, "$RECOVERY": pk_of(B)})[0]
    start = full_height()
    consts = {"$OWNER": owner, "$PKCOMMIT": commit, "$QDAY_NFT": qnft, "$BACKSTOP": str(start + 1_000_000),
              "$PENDING_TREE": pend, "$DELAY": str(DELAY), "$LIMITL": f"{LIMIT}L", **KA_CONST}
    src = (HERE / "PolicyTemplate.es").read_text()
    allon = {s: True for s in SW}
    names = {"A-all": ("A", allon)}
    for x in ("hash", "ka", "signal", "twostep"):
        names[f"A-all-{x}"] = ("A", dict(allon, **{x.upper(): False}))
        names[f"C-all-{x}"] = ("C", dict(allon, **{x.upper(): False}))
    trees = {}
    for nm, (form, sw) in names.items():
        s, subs = (form_a if form == "A" else form_c)(src, sw)
        trees[nm] = compile_tree(s, {**consts, **subs})
    S = 300_000_000
    need = {nm: 4 for nm in trees}
    boxes = {nm: [] for nm in trees}
    reqs = [(nm, {"address": trees[nm][1], "value": S}) for nm in trees for _ in range(need[nm])]
    for i in range(0, len(reqs), 12):
        chunk = reqs[i:i + 12]
        dep = send([r for _, r in chunk])
        used = set()
        for nm, _ in chunk:
            o = [o for o in at(dep, trees[nm][0]) if o["boxId"] not in used][0]
            used.add(o["boxId"])
            boxes[nm].append(o)
    for nm in trees:
        run.tree(nm, trees[nm][0], trees[nm][1], boxes[nm][0]["boxId"])
    dest = "0008cd" + pk_of(A, 2)

    def owner_outs(nm, b, h):
        t = trees[nm][0]
        return [out(LIMIT, pend, h, [], {"R4": coll_bytes(dest), "R5": int_c(h + 1 + DELAY + 2),
                                         "R6": coll_bytes(t)}),
                out(b["value"] - LIMIT, t, h)]

    def owner(n, label, nm, expect, data, sibling=None, submit=True, **kw):
        b = boxes[nm].pop()
        h = full_height()
        return run.key_spend(n, label, A, [b["boxId"]], [data["boxId"]], owner_outs(nm, b, h), expect, sibling,
                             submit=submit, cost=submit, tree=nm, **kw)

    def hashk(n, label, nm, expect, sibling=None, submit=True, **kw):
        b = boxes[nm].pop()
        h = full_height()
        outs = [out(b["value"], NOBODY_TREE, h)]
        sig = wots_sign(seed, b["boxId"], outs)
        return run.check(n, label, {"inputs": [inp(b["boxId"], {"1": coll_bytes(sig)})], "dataInputs": [],
                                    "outputs": outs}, expect, sibling, submit=submit, cost=submit, tree=nm, **kw)

    def maint(n, label, nm, expect, sibling=None, submit=True, **kw):
        b1, b2 = boxes[nm].pop(), boxes[nm].pop()
        h = full_height()
        bounty = min(2 * 500_000, min(b1["value"], b2["value"]))
        outs = [out(b1["value"] + b2["value"] - bounty, trees[nm][0], h), out(bounty, FEE_TREE, h)]
        return run.check(n, label, {"inputs": [inp(b1["boxId"], {"0": "0400"}), inp(b2["boxId"], {"0": "0400"})],
                                    "dataInputs": [], "outputs": outs}, expect, sibling, submit=submit, cost=submit,
                         tree=nm, **kw)

    # negatives first (checked, not submitted), each before its sibling consumes boxes of that tree
    hashk(1, "hash key on A-all-hash (switch off)", "A-all-hash", "REFUSE", sibling=10, submit=False)
    hashk(2, "hash key on C-all-hash (block absent)", "C-all-hash", "REFUSE", sibling=10, submit=False)
    maint(3, "maintenance on A-all-ka (switch off)", "A-all-ka", "REFUSE", sibling=20, submit=False)
    maint(4, "maintenance on C-all-ka (block absent)", "C-all-ka", "REFUSE", sibling=20, submit=False)
    # honest paths, mined, cost from the mempool
    owner(5, "owner path on A-all (signal + two-step + limit exercised)", "A-all", "ACCEPT", flag)
    owner(6, "owner path on A-all-hash (switched off: hash key)", "A-all-hash", "ACCEPT", flag)
    owner(7, "owner path on A-all-ka (switched off: KeepAlive)", "A-all-ka", "ACCEPT", flag)
    owner(8, "owner path on C-all-hash (absent: hash key)", "C-all-hash", "ACCEPT", flag)
    owner(9, "owner path on C-all-ka (absent: KeepAlive)", "C-all-ka", "ACCEPT", flag)
    hashk(10, "hash-key path on A-all", "A-all", "ACCEPT")
    hashk(11, "hash-key path on A-all-signal (switched off: signal)", "A-all-signal", "ACCEPT")
    hashk(12, "hash-key path on C-all-signal (absent: signal)", "C-all-signal", "ACCEPT")
    maint(20, "maintenance merge on A-all", "A-all", "ACCEPT")
    maint(21, "maintenance merge on A-all-twostep (switched off: two-step)", "A-all-twostep", "ACCEPT")
    maint(22, "maintenance merge on C-all-twostep (absent: two-step)", "C-all-twostep", "ACCEPT")
    # the signal gate: flip the flag (oracle key, A's second key), then an owner spend with the true flag
    h = full_height()
    flipped = run.key_spend("30.a", "the oracle flips the flag false -> true", A, [flag["boxId"]], [],
                            [out(flag["value"], qtree, h, flag["assets"], {"R4": TRUE})], "ACCEPT", submit=True)
    tflag = at(flipped, qtree)[0]
    owner(31, "owner spend with a TRUE flag on A-all (gate on)", "A-all", "REFUSE", tflag, sibling=32, submit=False)
    owner(32, "owner spend with a TRUE flag on A-all-signal (gate off)", "A-all-signal", "ACCEPT", tflag,
          submit=False)
    pairs = []
    cost = {c["n"]: c["cost"] for c in run.doc["cases"]}
    for path, base_n, others in (("owner", 5, [(6, "switched-off", "hash"), (7, "switched-off", "KeepAlive"),
                                               (8, "absent", "hash"), (9, "absent", "KeepAlive")]),
                                 ("hash key", 10, [(11, "switched-off", "signal"), (12, "absent", "signal")]),
                                 ("maintenance", 20, [(21, "switched-off", "two-step"), (22, "absent", "two-step")])):
        for n, kind, x in others:
            pairs.append({"path": path, "kind": kind, "X": x, "all_on": cost[base_n], "without_X": cost[n],
                          "delta": None if None in (cost[base_n], cost[n]) else cost[base_n] - cost[n]})
    run.doc["pairs"] = pairs
    run.save()
    for p in pairs:
        print(p)


def stage_1b_gate():
    """Continuation of 1b after a harness bug: rows 31-32 needed boxes on A-all and A-all-signal and the first run had
    deposited too few (IndexError at row 31). Fresh deposits to the same trees, the flipped flag box from row 30.a,
    then the pair table."""
    run = Run("1b-template-cost", HERE)
    run.doc = json.loads(run.path.read_text())
    run.bug(31, "too few boxes deposited on A-all (4, all used by rows 5, 10, 20): IndexError at row 31",
            "--stage 1b-gate deposits fresh boxes on A-all and A-all-signal and runs rows 31-32")
    trees = {t["name"]: (open(HERE / f"{t['name']}.tree").read().strip(), t["address"]) for t in run.doc["trees"]}
    flip_tx = [c for c in run.doc["cases"] if c["n"] == "30.a"][0]["tx_id"]
    ftx = must(A, f"/blockchain/transaction/byId/{flip_tx}")
    tflag = ftx["outputs"][0]
    owner = pk_of(A)
    pend = compile_tree((HERE.parent / "2-twostep" / "Pending.es").read_text(),
                        {"$OWNER": owner, "$RECOVERY": pk_of(B)})[0]
    S = 300_000_000
    dep = send([{"address": trees[n][1], "value": S} for n in ("A-all", "A-all-signal")])
    bx = {n: at(dep, trees[n][0])[0] for n in ("A-all", "A-all-signal")}
    dest = "0008cd" + pk_of(A, 2)
    for n, nm, expect, sib in ((31, "A-all", "REFUSE", 32), (32, "A-all-signal", "ACCEPT", None)):
        b = bx[nm]
        h = full_height()
        outs = [out(LIMIT, pend, h, [], {"R4": coll_bytes(dest), "R5": int_c(h + 1 + DELAY + 2),
                                         "R6": coll_bytes(trees[nm][0])}), out(b["value"] - LIMIT, trees[nm][0], h)]
        run.key_spend(n, f"owner spend with a TRUE flag on {nm} ({'gate on' if n == 31 else 'gate off'})", A,
                      [b["boxId"]], [tflag["boxId"]], outs, expect, sib, tree=nm)
    pairs = []
    cost = {c["n"]: c["cost"] for c in run.doc["cases"]}
    for path, base_n, others in (("owner", 5, [(6, "switched-off", "hash"), (7, "switched-off", "KeepAlive"),
                                               (8, "absent", "hash"), (9, "absent", "KeepAlive")]),
                                 ("hash key", 10, [(11, "switched-off", "signal"), (12, "absent", "signal")]),
                                 ("maintenance", 20, [(21, "switched-off", "two-step"), (22, "absent", "two-step")])):
        for n, kind, x in others:
            pairs.append({"path": path, "kind": kind, "X": x, "all_on": cost[base_n], "without_X": cost[n],
                          "delta": None if None in (cost[base_n], cost[n]) else cost[base_n] - cost[n]})
    run.doc["pairs"] = pairs
    run.save()
    for p in pairs:
        print(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["1a", "1b", "1b-gate"], required=True)
    a = ap.parse_args()
    if a.stage == "1a":
        run = Run("1a-template-compile", HERE, "results-1a.json")
        owner = pk_of(A)
        seed = os.urandom(32).hex()
        commit = wots("commit", seed, "32", "16")["commitment"]
        qnft = issue("QDAY-1")
        pend = compile_tree((HERE.parent / "2-twostep" / "Pending.es").read_text(),
                            {"$OWNER": owner, "$RECOVERY": pk_of(B)})[0]
        start = full_height()
        consts = {"$OWNER": owner, "$PKCOMMIT": commit, "$QDAY_NFT": qnft, "$BACKSTOP": str(start + 1_000_000),
                  "$PENDING_TREE": pend, "$DELAY": str(DELAY), "$LIMITL": f"{LIMIT}L", **KA_CONST}
        out, formb = stage_1a(run, consts)
        # references, same compiler, the READMEs' constants
        root = HERE.parent.parent
        kaa = compile_tree((root / "keepalive" / "KeepAliveAddress.es").read_text(), {"$OWNER": owner, **KA_CONST})
        qv = compile_tree((root / "qvault" / "QVault.es").read_text(), {
            "$OWNER": owner, "$QDAY_NFT": qnft, "$BACKSTOP": str(start + 1_000_000), "$PKCOMMIT": commit, **KA_CONST})
        ref = {"KeepAliveAddress": kaa, "QVault": qv}
        # deposits: one per tree, one token unit each, no registers
        tok = issue("POLICY-1A", 100)
        targets = [(f"A-{n}", v) for n, v in out["A"].items() if "tree" in v] + \
                  [(f"C-{n}", v) for n, v in out["C"].items() if "tree" in v] + \
                  [(n, {"tree": t, "address": ad}) for n, (t, ad) in ref.items()]
        seen, boxes = {}, {}
        for i in range(0, len(targets), 10):
            chunk = targets[i:i + 10]
            dep = send([{"address": v["address"], "value": 10_000_000, "assets": [{"tokenId": tok, "amount": 1}]}
                        for _, v in chunk])
            for nm, v in chunk:
                cand = [o for o in dep["outputs"] if o["ergoTree"] == v["tree"] and o["boxId"] not in seen]
                boxes[nm] = cand[0]["boxId"]
                seen[cand[0]["boxId"]] = nm
        for nm, v in targets:
            run.tree(nm, v["tree"], v["address"], boxes[nm],
                     extra={"template_hash": template_hash(v["tree"]), "switches": v.get("switches")})
        run.doc["form_B"] = formb
        run.doc["constants"] = {k: v for k, v in consts.items() if k not in ("$PENDING_TREE",)}
        run.doc["pending_tree_bytes"] = len(pend) // 2
        run.doc["compile_errors"] = {f"{f}-{n}": v["error"] for f in out for n, v in out[f].items() if "error" in v}
        run.save()
        print(json.dumps({"form_B": {k: v for k, v in formb.items() if k != "rewrites"}}, indent=1))
        print("rewrites equal to form A:", sum(r["equals_form_A_compile"] for r in formb["rewrites"].values()),
              "of", len(formb["rewrites"]))
    elif a.stage == "1b":
        stage_1b()
    else:
        stage_1b_gate()


if __name__ == "__main__":
    main()
