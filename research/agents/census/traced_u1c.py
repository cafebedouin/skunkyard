#!/usr/bin/env python3
"""U1c hand traces: the scripts read by hand, path by path (CONFIRMED = traced through the decompiled script of a
live box with its constants substituted; each quote is the path's condition in one line).

Keys are template-hash prefixes, resolved against census/u1c/m.json. Classes as in census/paths.py:
key, key (miner), key (secret), keyless now, keyless later, keyless with input, unreachable.
`take` describes what an executor receives on a keyless path (line n); `preserve` says whether a third party can
keep the boxes from storage rent (line o).

usage: traced_u1c.py   (writes census/u1c/traced.json)
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))

T = {}


def t(prefix, name, paths, verdict, preserve=None, take=None, source="decompiled script (explorer), read by hand"):
    T[prefix] = {"name": name, "source": source, "paths": [dict(p, status="CONFIRMED") for p in paths],
                 "verdict": verdict, "preserve": preserve, "take": take}


def P(cls, cond, executor=None, **kw):
    d = {"class": cls, "condition": cond}
    if executor:
        d["executor"] = executor
    d.update(kw)
    return d


# ---- staking incentive (U1b: "rent only"; UPKEEP.md "U1b checked") --------------------------------------------
_STAKE = [
    P("keyless now", "SELF.value <= 0.1 ERG && OUTPUTS.size == 3 && OUTPUTS(0) same script, value > SELF.value && "
      "OUTPUTS(1).value == 0.0005 ERG * (inputs of this script) && OUTPUTS(2).value == 0.001 ERG",
      "0.0005 ERG per merged box (OUTPUTS(1), any script); OUTPUTS(2) 0.001 ERG any script (the miner fee)"),
    P("keyless with input", "INPUTS(0) holds the staking state NFT, INPUTS(2) the stake token, SELF last input, "
      "OUTPUTS(4) same script >= SELF.value - 0.005 ERG ...: the staking setup's own compound/emit step",
      "nothing beyond the protocol's fixed fee outputs; needs the setup's state box"),
]
t("278ccff223ae", "ErgoPad-style staking incentive (NETA and others), older version", _STAKE + [
    P("keyless with input", "INPUTS(0) holds the stake-state token, SELF last input, every input a stake box ...: "
      "staking emission", None)],
  "consolidation bounty applies only to boxes of at most 0.1 ERG; every such box was merged on 2026-10-09; the "
  "merged boxes hold more than 0.1 ERG, so no keyless take stands until new small boxes are created",
  preserve="yes, while a box holds <= 0.1 ERG (consolidation); larger boxes are spent by the setup's own steps")
t("b924a4f73573", "ErgoPad-style staking incentive, newer version (stake NFT b682ad9e)", _STAKE,
  "as 278ccff2: all small boxes merged on 2026-10-09", preserve="yes, while a box holds <= 0.1 ERG")

# ---- free / dead -------------------------------------------------------------------------------------------------
t("e9d13195d73d", "OUTPUTS.size == n (n = 1 in every box read)", [
    P("keyless now", "OUTPUTS.size == 1", "the whole box: a one-output transaction sends it anywhere; no fee box "
      "fits, so only a miner can include it for free [inferred: nodes drop zero-fee transactions]")],
  "free box, own block only", preserve="yes (anyone may respend it)",
  take={"kind": "free", "outputs": 1})
t("75bee19d7f17", "data records 'flowlens:forensic:immutable:v2' (R4 tag, R5..R9 JSON)", [
    P("unreachable", "HEIGHT < 0 && SELF.R4 == 'flowlens:forensic:immutable:v2'")],
  "no input satisfies HEIGHT < 0: unspendable by design (immutable records); every box is worth less than one "
  "rent claim (0.0004 ERG, 262 to 983 bytes), so storage rent consumes each four years after creation",
  preserve="no")

# ---- EIP-31 Babel -------------------------------------------------------------------------------------------------
t("4e83fa68ef3e", "EIP-31 Babel fee box", [
    P("keyless now", "getVar[Int](0).isDefined && OUTPUTS(v0) same script, token, R4, R5 copied, R6 = SELF.id && "
      "tokens added * R5 >= ERG taken", "the spread against a pool selling the token below R5 (U1b g)"),
    P("key", "R4[SigmaProp].get (the owner)")],
  "standing bid; a take exists only when a pool sells the token below the bid (line n checks every box)",
  preserve="no (a fill or the owner's key)", source="eips eip-0031.md:57-87; decompiled script")

# ---- protocol plumbing read in this census ------------------------------------------------------------------------
t("c9162bd02adb", "USE (Dexy) bank: useBankNFT, USE", [
    P("keyless with input", "OUTPUTS(1) same script, NFT and token kept && INPUTS(0) holds one of four action NFTs "
      "(mint, intervention, ... ) or INPUTS(2) the fifth", "nothing: the action contracts set the amounts")],
  "protocol plumbing; spent only beside its own action boxes", preserve="value far above rent")
t("ab9e9b2ad4ac", "AVL-tree payout ledger, ERG (token f0f3581e at INPUTS(0))", [
    P("keyless with input", "INPUTS(0) holds token f0f3581e && OUTPUTS(0).value == INPUTS(0).value + sum(var 0 "
      "amounts) && OUTPUTS(0).R4 digest == INPUTS(0).R4 updated by var 0 with proof var 1")],
  "deposits into a ledger box held by its operator's NFT box; no executor reward", preserve="value above rent")
t("a88b7bcf9de8", "AVL-tree payout ledger, ergopad (same design, ERG and token columns)", [
    P("keyless with input", "INPUTS(0) holds the ledger token && OUTPUTS(0) value and token(1) grow by var 0 "
      "amounts && R4 digest updated")],
  "as ab9e9b2a", preserve="value above rent")
t("f2aa6b79b4b3", "GORT buyback (buybackNFT, GORT)", [
    P("keyless with input", "var 0 == 0 && INPUTS(0) holds a pool NFT d1c9e206 && OUTPUTS(1) same script gains "
      "GORT && ERG out <= pool price * GORT in: the buyback swap"),
    P("keyless now", "var 0 == 1 && OUTPUTS(2) same script, same tokens, value > SELF.value",
      "nothing: a top-up (donation) path"),
    P("keyless with input", "var 0 not 0 or 1 && INPUTS(0) holds 3c45f29a && ...: a token return to its source")],
  "protocol plumbing; the keyless-now path only adds ERG", preserve="value above rent")
t("8b1e2b8137db", "DORT buyback (dortBuyback, DORT)", [
    P("keyless with input", "var 0 == 0 && INPUTS(0) holds pool NFT 35bc7189 && OUTPUTS(1) same script, R4 = "
      "SELF.id, gains DORT, ERG out bounded by the pool"),
    P("keyless now", "var 0 == 1 && OUTPUTS(2) same script and tokens, value > SELF.value, R4 = SELF.id",
      "nothing: a top-up path"),
    P("keyless with input", "var 0 not 0 or 1 && INPUTS(0) holds 6a2b821b && ...")],
  "as GORT buyback", preserve="value above rent")
t("b38309cece95", "Lithos emission config (LITHOS-EMCONFIG)", [
    P("keyless with input", "the inputs hold at least 3 units of token 519b9fde && OUTPUTS(0).tokens(0) == "
      "SELF.tokens(0)", "nothing: a governance vote by token holders")],
  "governance; not a take", preserve="value above rent")
t("58210ce06325", "EGIO staking: stake boxes (EGIO Stake Token, EGIO)", [
    P("keyless with input", "INPUTS(0) holds the EGIO stake-state token 0e420219 && OUTPUTS(i) recreates SELF "
      "with R4(0) + 1 ...: a reward step"),
    P("keyless with input", "INPUTS(0) holds 097fd281 && INPUTS(1).id == SELF.id && ...: unstake"),
    P("keyless with input", "INPUTS(0) holds 097fd281 && INPUTS(1).id == SELF.id")],
  "every path needs the protocol's state box at INPUTS(0); none lets a third party merge or refresh",
  preserve="no keyless path for a third party: only the EGIO state box's own transactions respend them")
t("ab4e4dc33cd1", "ErgoMixer token sale box (ErgoMixer token, R4 price list)", [
    P("keyless now", "OUTPUTS.size == 4 && OUTPUTS(0) script hash 199a5a08 && OUTPUTS(1) same script, R4, R5, "
      "token kept && OUTPUTS(2) script hash ... gets the price for the tokens bought", "nothing: a purchase"),
    P("keyless with input", "OUTPUTS.size == 5 && INPUTS(0) script hash 199a5a08 && ...: a purchase from a mix"),
    P("key", "pk(b038b0…)")],
  "a sale; the buyer pays the listed price", preserve="no (0.1 ERG boxes, a purchase or the owner's key)")
t("c5328d694b98", "ErgoMixer fee box (R4 fee, token 1a6a8c16 accounting)", [
    P("key", "pk(b038b0…)"),
    P("keyless with input", "INPUTS.size == 2 && OUTPUTS.size == 3 && OUTPUTS(1) same script >= SELF.value - R4 "
      "&& ErgoMixer tokens paid in: a mix pays its fee"),
    P("keyless with input", "INPUTS.size == 3 && OUTPUTS.size == 4 && ...: the same with one more input")],
  "the mixer's fee box; R4 ERG leaves per use, paid for in ErgoMixer tokens", preserve="value above rent")

# ---- Paideia DAO ----------------------------------------------------------------------------------------------------
_PAIDEIA_REFRESH = P(
    "keyless later", "var 0 == 7 && OUTPUTS(INPUTS.indexOf(SELF)).value >= SELF.value - 0.002 ERG && its script "
    "hash is the one the DAO config (data input, R4 AVL tree, proof var 1) lists && the box bytes after value, "
    "script and height are unchanged && (new creation height - SELF creation height >= 504,000 || script changed)",
    "up to 0.002 ERG per box refreshed, once the box is 504,000 blocks old; needs the DAO config box as a data "
    "input and an AVL proof (both public)", whenRule={"kind": "creationPlus", "blocks": 504_000})
t("37142e749788", "Paideia DAO treasury (im.paideia.contracts.treasury) [inferred from the action codes]", [
    P("keyless with input", "var 0 in (3, 4) && the DAO config data input (AVL) && ...: a passed proposal's "
      "payout"),
    P("keyless with input", "var 0 == 9 && config data input ...: an update"),
    P("keyless now", "var 0 == 10 && at least 5 inputs and exactly 1 output of this exact script && every token "
      "kept && (inputs' ERG - output's ERG) <= 0.002 ERG && inputs' ERG >= 0.002 ERG",
      "up to 0.002 ERG per transaction (not per box), from which the miner fee is paid; needs >= 5 boxes of one "
      "DAO's tree"),
    _PAIDEIA_REFRESH],
  "a merge pays at most 0.002 ERG a transaction: barely above a 0.0011 ERG fee, a take only in a miner's own "
  "block; the refresh path is rent protection built in, open at 504,000 blocks of age",
  preserve="yes: merge (>= 5 boxes) any time; refresh after 504,000 blocks; both keyless")
t("5b41af39fc2d", "Paideia DAO treasury, variant (same action codes)", [
    P("keyless now", "var 0 == 10 && >= 5 inputs and 1 output of this script && the output holds every token && "
      "ERG taken <= 0.002", "as 37142e74"),
    _PAIDEIA_REFRESH],
  "as 37142e74", preserve="yes: merge (>= 5 boxes), refresh after 504,000 blocks")
t("59c5b7bfe28d", "Paideia DAO key / config-holder boxes (Sigmanauts DAO Key and others; R4 AVL)", [
    P("keyless with input", "var 0 == 8 && the box holding SELF's token (output) has the same tokens, more ERG, a "
      "script listed in its own R4 tree under im.paideia.contracts.action.<input 0's script> && the key is "
      "defined: an action spends it"),
    _PAIDEIA_REFRESH],
  "DAO plumbing with the refresh path", preserve="yes: refresh after 504,000 blocks")


# ---- protocol plumbing with a keyless-now path but no executor reward ------------------------------------------
t("ae9ac8d914dc", "EIP-27 re-emission contract (Reemission Contract NFT)", [
    P("keyless now", "OUTPUTS(0) same script, value > SELF.value, R2 token list(0) == the re-emission token && "
      "OUTPUTS(1).value <= 0.01 ERG && OUTPUTS.size == 2", "nothing: the emission tx funds it; no payout output"),
    P("keyless later", "OUTPUTS(0) same script, created at HEIGHT && OUTPUTS(1) pays the block's miner "
      "(minerPubKey) via the fee tree", "the miner reward portion; this is the emission/miner path, not a take")],
  "chain plumbing (one spend per block, by the emission tx); no bounty for a third party",
  preserve="value far above rent")
t("707c363f0914", "EIP-27 re-emission proxy (pay-to-reemission), swept into the emission tx", [
    P("keyless now", "OUTPUTS(0).R2 token list(0) == the re-emission token", "nothing: swept by the emission tx")],
  "plumbing: 1,185 proxy boxes waiting to be swept into an emission block; no executor reward",
  preserve="each box 9 to 18 ERG, far above rent")

# ---- Phoenix hodl banks: mint/burn, user-paid, no executor reward ----------------------------------------------
for _p, _n in [("8b5dac35309d", "Phoenix hodlERG3 bank (hodlERG3)"),
               ("5811576e4c7d", "Phoenix hodlComet bank (hodlCOMET3)")]:
    t(_p, _n, [
        P("keyless now", "OUTPUTS(0) same script, NFT kept, hodl token >= 1; a mint (token out) or burn (token in) "
          "at the bank's R4/R5/R7/R8 price and fee", "nothing: the user pays the dev fee (R7) and burn fee (R8); "
          "no output pays whoever builds the transaction"),
        P("keyless now", "the opposite side of the mint/burn", None)],
      "bank plumbing; a mint or burn pays the bank's own fees, not the executor (U1b i: hodlERG size < 0.01 ERG "
      "against its one dust pool)", preserve="value far above rent")

# ---- SigmaFi-style bonds: matured -> keyless refund to the lender, no reward -----------------------------------
for _p, _n in [("edacb0e6bc89", "SigmaFi-style bond (collateral; lender R8, borrower R5)"),
               ("44830db1e02b", "SigmaFi ERG bond")]:
    t(_p, _n, [
        P("keyless later", "HEIGHT >= R7 (maturity) && OUTPUTS(0) pays the lender (R8) the whole box, tokens and "
          "value kept, R4 = SELF.id", "nothing: the matured collateral goes entirely to the lender (U1b i)"),
        P("key", "!matured && the borrower repays (R5): OUTPUTS(0) the repayment to the lender, OUTPUTS(1) the "
          "collateral back to the borrower")],
      "liquidation is keyless once matured but pays the lender, not the executor; no reward",
      preserve="the lender claims it at maturity; a third party gains nothing")

# ---- fee / tip splitters: keyless, but every output is a fixed recipient ---------------------------------------
for _p, _n, _cut in [("0df8312fa401", "fee splitter (0.25% of inputs to a tip, rest to a fixed key)", "0.25%"),
                     ("9a54eb248256", "fee splitter (same, one box)", "0.25%")]:
    t(_p, _n, [
        P("keyless now", f"OUTPUTS(0).value >= inputs - ({_cut} of inputs + var 1) && OUTPUTS(0) pays the fixed "
          "key; the cut (var 1, var 2) is bounded but the surplus is not an output anyone names",
          "the cut is set by context variables the spender chooses, but OUTPUTS(0) must pay the fixed key: a "
          "service fee to that key, not a take for a third party"),
        P("key", "the fixed key spends it directly")],
      "a swap/relay fee box; the keyless path pays a fixed key, so a third party cannot take it",
      preserve="value above rent")
t("2b0bcc210c83", "payout splitter (4 fixed recipient keys, l10/100 each; a batch-payment box)", [
    P("keyless now", "OUTPUTS(0..3) pay four fixed keys their share of the total (R4 token or ERG), total >= "
      "0.005 ERG", "nothing: every output is a fixed recipient; a third party routes the payment but takes "
      "nothing")],
  "a scheduled multi-payout; keyless to execute, no executor reward", preserve="value above rent")
t("c7c5a98a7a18", "fee-distribution box (pays a fixed list of keys; else a 1-of-2 key)", [
    P("keyless now", "OUTPUTS.size == 2 && OUTPUTS(i) pay the fixed keys (constant 0 list) their pro-rata share "
      "&& blake2b256(OUTPUTS(1).propositionBytes) == the fee-contract hash", "nothing: outputs are fixed keys"),
    P("key", "atLeast(1, {two operator keys})")],
  "a GetBlok/pool fee distributor; keyless but pays fixed recipients", preserve="dust, below rent (44 boxes)")
t("a824f427539331fd", "token-conservation box (sum of value+token over SELF-script inputs == over outputs)", [
    P("keyless now", "fold over INPUTS of this script of (value + token amount) == the same fold over OUTPUTS",
      "nothing: it only forbids value leaving the script; a merge or split is free but pays nobody")],
  "an invariant wrapper (99.99e15 of one token); keyless to reshuffle, no reward", preserve="value above rent")

# ---- a one-transaction self-arb / vault with a keyless rebate path --------------------------------------------
t("16b06ffc7d80", "prefix-locked output box (OUTPUTS(0).propositionBytes[3:10] == a key prefix)", [
    P("keyless now", "OUTPUTS(0).propositionBytes.slice(3, 10) == 0x03d42ba1800ff4",
      "nothing beyond the box's own ERG: it only pins OUTPUTS(0) to a key with that prefix (the owner's); a third "
      "party gains nothing")],
  "a weak lock to one key family; 24 of 25 boxes below one rent claim", preserve="dust, below rent")

# ---- rent-age-gated airdrop sweep (a keyless path that fires only at rent age) ---------------------------------
t("fbbddf8180ca", "airdrop/escrow with a rent-age sweep (HEIGHT - creation > 1,051,190)", [
    P("keyless now", "INPUTS has a box of the operator key (constant 0): the operator sweeps"),
    P("keyless with input", "every non-self input is older than 1,051,190 blocks && OUTPUTS.size == 4 && one "
      "output to each of two fixed keys && the token totals are conserved: a rent-age cleanup to fixed keys",
      "nothing: the sweep pays two fixed keys, not the executor; it fires only at rent age")],
  "a distribution box swept at rent age to fixed keys; keyless but no executor reward",
  preserve="the operator or the rent-age sweep preserves it; a third party gains nothing")

# ---- Rosen bridge AWC/RWT (the largest keyless-with-input stock) ----------------------------------------------
t("0c7face721e4", "Rosen Bridge AWC (rspv3ErgoAWC, RSN)", [
    P("keyless with input", "INPUTS(0) holds the watcher-repo NFT (eedb8530...) && the AWC is recreated with "
      "R5 incremented / the collateral returned: a watcher action", "nothing beyond the bridge's own rules; "
      "needs the repo box")],
  "bridge plumbing; every path needs the Rosen repo/collateral box, which only a watcher holds",
  preserve="value above rent (RSN collateral)")
t("1151628ab5a4", "Rosen Bridge AWC (rspv2CardanoAWC, RSN; 21,600 ERG)", [
    P("keyless with input", "INPUTS(0) holds the Cardano watcher-repo NFT (eca7776f...) && the AWC recreated: a "
      "watcher collateral action", "nothing beyond the bridge's rules; needs the repo box")],
  "as 0c7face7", preserve="value above rent")
t("9259d83f4f6b", "SigmaUSD-style bank (SigUSD, SigRSV, SigUSDBankNFT; 10,191 ERG) [a second bank deployment]", [
    P("keyless with input", "the oracle box (54acaa0c...) as a data input && OUTPUTS(0) same script, >= 0.01 ERG "
      "&& exactly one of SC/RC changes by the oracle-priced amount: a mint or redeem", "nothing: the user pays "
      "the bank fee; no executor output (U1b b; the SigRSV arb needs a second pool leg)")],
  "AgeUSD bank plumbing; a mint/redeem is user-paid, the arbitrage take needs a second transaction (U1b j)",
  preserve="value far above rent")


def main():
    p = os.path.join(HERE, "u1c", "m.json")
    m = json.load(open(p))["templates"] if os.path.exists(p) else []
    full = {}
    for k, v in T.items():
        hits = [r["templateHash"] for r in m if r["templateHash"].startswith(k)]
        if len(hits) != 1:
            print(f"{k}: {len(hits)} matches in m.json; kept by prefix")
            full[k] = dict(v, prefixOnly=True)
            continue
        full[hits[0]] = v
    with open(os.path.join(HERE, "u1c", "traced.json"), "w") as f:
        json.dump(full, f, indent=1)
    print(f"wrote {len(full)} traced templates")


if __name__ == "__main__":
    main()
