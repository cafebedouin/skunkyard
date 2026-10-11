#!/usr/bin/env python3
"""The shared-output theft (part-four finding, a property of every keyless merge in the family), and its fix, judged
by the node.

A keyless merge accepted a successor at its script worth at least the merged total less the bounty, without checking
that the successor was funded by the merged boxes. Any value a third party brings into the address that it does not
fund itself -- a Pending2 completion, a settlement, an order fill -- could cover the successor, freeing the merged
boxes' whole value (total - fee) for the executor, whatever the payout's size V: the executor picks a subset of
boxes worth about V, so no bound on next.value can stop it (boundary probe below).

The fix (part four): the maintenance path requires every input of the transaction to be at this script
(INPUTS.size == mine.size). The only value entering is then the merged boxes' own, so by conservation nothing but
the bounty can leave. The cost is the sponsored merge (a sponsor's fee box is a foreign input); the fee comes from
the bounty, as the keyless mainnet merge and the Lithos job already do. next.value <= total is kept as defence in
depth.

Each row is built against the PRE-FIX tree (git HEAD, no rule) and the POST-FIX tree (the working file).

  1    completion theft, V > total                  PRE ACCEPT (theft)   POST REFUSE (foreign input P)
  1sub subset theft, V < total (executor merges     PRE ACCEPT           POST REFUSE   (the value bound alone would
       only boxes worth about V)                                                        pass this; the input rule refuses)
  1b   K1 carries a token the pending box lacks      PRE REFUSE           POST REFUSE   (tokensKept / foreign input)
  1c   pending box carries the token (tokens no      PRE ACCEPT           POST REFUSE
       protection)
  2    QVault maintenance, V > total                 PRE ACCEPT           POST REFUSE
  3    plain keeper merge, bounty pays the fee       PRE ACCEPT           POST ACCEPT   (no foreign input; take = bounty)
  4    sponsored merge (a sigmaProp(true) fee box)   PRE ACCEPT           POST REFUSE   (the cost of the fix)

usage: devnet-test-shared-output.py
"""
import subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "policy"))
from common import *  # noqa: E402

PREFIX_ES = HERE.parent.parent  # repo root, for git show
DV = {"$PER_INPUTL": "500000L", "$REFRESHL": "2000000L", "$PERIOD": "40", "$WINDOW": "20", "$SLACK": "10"}
PER_INPUT = 500_000
A_VAL = B_VAL = 50_000_000
TOTAL = A_VAL + B_VAL
BOUNTY = min(2 * PER_INPUT, TOTAL - max(A_VAL, B_VAL))   # 1,000,000
V_BIG = 200_000_000
V_SUB = TOTAL - BOUNTY // 2                               # 99,500,000, inside [total-bounty, total]
QDUMMY = {"$QDAY_NFT": "11" * 32, "$PKCOMMIT": "22" * 32, "$PKSEED": "33" * 32, "$BACKSTOP": "1000000"}


def git_head(path):
    return subprocess.run(["git", "show", f"HEAD:{path}"], cwd=str(PREFIX_ES), capture_output=True, text=True,
                          check=True).stdout


def main():
    run = Run("shared-output-theft", HERE, out="results-shared-output.json")
    owner, rec = pk_of(A), pk_of(B)
    stranger = NOBODY_TREE
    true_t, true_addr = compile_tree("{ sigmaProp(true) }", {})

    pend_src = (HERE.parent / "policy" / "2-twostep" / "Pending2.es").read_text()
    pend, pend_addr = compile_tree(pend_src, {"$OWNER": owner, "$RECOVERY": rec})

    kaa_post = compile_tree((HERE / "KeepAliveAddress.es").read_text(), dict(DV, **{"$OWNER": owner}))
    kaa_pre = compile_tree(git_head("skunks/keepalive/KeepAliveAddress.es"), dict(DV, **{"$OWNER": owner}))
    qv_post = compile_tree((HERE.parent / "qvault" / "QVault.es").read_text(), dict(DV, **dict(QDUMMY, **{"$OWNER": owner})))
    qv_pre = compile_tree(git_head("skunks/qvault/QVault.es"), dict(DV, **dict(QDUMMY, **{"$OWNER": owner})))
    run.doc["trees_tested"] = {"kaa_pre_bytes": len(kaa_pre[0]) // 2, "kaa_post_bytes": len(kaa_post[0]) // 2,
                               "qv_pre_bytes": len(qv_pre[0]) // 2, "qv_post_bytes": len(qv_post[0]) // 2,
                               "pending2_bytes": len(pend) // 2}
    run.save()
    tok = issue("SHAREDTOK", 10)

    def mk_pending(dest_tree, value, token_amt=0):
        past = full_height() - 1
        regs = {"R4": coll_bytes(dest_tree), "R5": int_c(past), "R6": coll_bytes(dest_tree)}
        req = {"address": pend_addr, "value": value, "registers": regs}
        if token_amt:
            req["assets"] = [{"tokenId": tok, "amount": token_amt}]
        return at(send([req]), pend)[0]

    def mk_boxes(dest_addr, dest_tree, token_amt_first=0):
        reqs = [{"address": dest_addr, "value": A_VAL}, {"address": dest_addr, "value": B_VAL}]
        if token_amt_first:
            reqs[0]["assets"] = [{"tokenId": tok, "amount": token_amt_first}]
        return at(send(reqs), dest_tree)

    def tlist(amt):
        return [{"tokenId": tok, "amount": amt}] if amt else []

    def theft_tx(P, K1, K2, dest_tree, out0_tokens, V):
        h = full_height()
        out0 = out(V, dest_tree, h, out0_tokens, {"R4": coll_bytes(P["boxId"])})
        take = K1["value"] + K2["value"] + P["value"] - V - FEE
        outs = [out0] + ([out(take, stranger, h)] if take > 0 else []) + [out(FEE, FEE_TREE, h)]
        return {"inputs": [inp(P["boxId"]), inp(K1["boxId"], {"0": "0400"}), inp(K2["boxId"], {"0": "0400"})],
                "dataInputs": [], "outputs": outs}

    trees = {"pre": (kaa_pre[0], kaa_pre[1]), "post": (kaa_post[0], kaa_post[1])}
    qtrees = {"pre": (qv_pre[0], qv_pre[1]), "post": (qv_post[0], qv_post[1])}

    for tag in ("pre", "post"):
        dt, da = trees[tag]
        exp = "ACCEPT" if tag == "pre" else "REFUSE"
        # 1: completion theft, V > total
        P = mk_pending(dt, V_BIG); K1, K2 = mk_boxes(da, dt)
        run.check(f"1-kaa-{tag}", f"KAA completion theft (token-free, V>total) [{tag}-fix]",
                  theft_tx(P, K1, K2, dt, [], V_BIG), exp, V=V_BIG, out1_take=K1["value"] + K2["value"] + P["value"] - V_BIG - FEE)
        # 1sub: subset theft, V inside [total-bounty, total] (the value bound alone would pass this)
        P = mk_pending(dt, V_SUB); K1, K2 = mk_boxes(da, dt)
        run.check(f"1sub-kaa-{tag}", f"KAA subset completion theft (V={V_SUB} in [total-bounty, total]) [{tag}-fix]",
                  theft_tx(P, K1, K2, dt, [], V_SUB), exp, V=V_SUB,
                  note="V <= total, so next.value<=total passes; refused post-fix only by INPUTS.size==mine.size")
        # 1b: K1 carries a token the pending box lacks -> REFUSE on both
        P = mk_pending(dt, V_BIG); K1, K2 = mk_boxes(da, dt, token_amt_first=1)
        run.check(f"1b-kaa-{tag}", f"KAA theft, K1 carries a token the pending box lacks [{tag}-fix]",
                  theft_tx(P, K1, K2, dt, tlist(1), V_BIG), "REFUSE")
        # 1c: pending box carries the token >= merged amount -> tokens do not protect
        P = mk_pending(dt, V_BIG, token_amt=1); K1, K2 = mk_boxes(da, dt, token_amt_first=1)
        run.check(f"1c-kaa-{tag}", f"KAA theft, pending box carries the token (tokens no protection) [{tag}-fix]",
                  theft_tx(P, K1, K2, dt, tlist(1), V_BIG), exp,
                  note="tokens do not protect: out0 carries P's token, satisfying tokensKept and the completion")
        # 2: QVault maintenance, V > total
        qt, qa = qtrees[tag]
        P = mk_pending(qt, V_BIG); K1, K2 = mk_boxes(qa, qt)
        run.check(f"2-qv-{tag}", f"QVault maintenance completion theft (V>total) [{tag}-fix]",
                  theft_tx(P, K1, K2, qt, [], V_BIG), exp)
        # 3: plain keeper merge (no foreign input), bounty pays the fee -> ACCEPT on both
        K1, K2 = mk_boxes(da, dt)
        h = full_height()
        outs = [out(TOTAL - BOUNTY, dt, h)] + ([out(BOUNTY - FEE, stranger, h)] if BOUNTY - FEE > 0 else []) + [out(FEE, FEE_TREE, h)]
        run.check(f"3-kaa-{tag}", f"KAA plain keeper merge, bounty pays the fee [{tag}-fix]",
                  {"inputs": [inp(K1["boxId"], {"0": "0400"}), inp(K2["boxId"], {"0": "0400"})],
                   "dataInputs": [], "outputs": outs}, "ACCEPT",
                  note="no foreign input; INPUTS.size == mine.size; take = bounty")
        # 4: sponsored merge (a sigmaProp(true) fee box as a foreign input) -> PRE ACCEPT, POST REFUSE (cost of the fix)
        K1, K2 = mk_boxes(da, dt)
        W = at(send([{"address": true_addr, "value": 5_000_000}]), true_t)[0]
        h = full_height()
        outs = [out(TOTAL, dt, h), out(W["value"] - FEE, stranger, h), out(FEE, FEE_TREE, h)]
        run.check(f"4-kaa-{tag}", f"KAA sponsored merge (foreign fee box), successor keeps every nanoERG [{tag}-fix]",
                  {"inputs": [inp(K1["boxId"], {"0": "0400"}), inp(K2["boxId"], {"0": "0400"}), inp(W["boxId"])],
                   "dataInputs": [], "outputs": outs}, "ACCEPT" if tag == "pre" else "REFUSE",
                  note="a sponsor's fee box is a foreign input; the fix refuses it (the keyless/Lithos merge pays from the bounty)")

    bad = [c for c in run.doc["cases"] if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED of {len(run.doc['cases'])}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
