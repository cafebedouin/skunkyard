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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["1a", "1b"], required=True)
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


if __name__ == "__main__":
    main()
