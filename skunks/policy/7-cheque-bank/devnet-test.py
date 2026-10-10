#!/usr/bin/env python3
"""Experiment 7: a cheque bank on the `policy` devnet, in stages (stop at the first that cannot be built).

  --stage control  the AVL+ helper against the node's own AvlTree.insert: three inserts reach the helper's digest
                   (ACCEPT); the same with the proof's last byte flipped (REFUSE)
  --stage 7a       the bank skeleton (Bank.es)
  --stage 7b       payee-bound cheques (ChequeBank.es)
  --stage 7c       private payments from the shared bank (RingBank.es)

Keys. Account keys K1, K2 are generated here (state/keys.json); node A signs for K1 only and node B for K2 only, each
by passing the secret as an external dlog secret to /wallet/transaction/sign (the node wallet cannot export its own
keys on this devnet: /wallet/getPrivateKey answers 404 for its first address). Depositors' funds sit in keyless
fund boxes (`HEIGHT > 0`, devnet only) so a deposit needs no signature and its verdict is the node's check alone.

Every case asserts the helper's persisted digest equals the bank box's R4 digest first (plan §4.7), except where a
case says otherwise.
"""
import argparse, json, os, secrets as rnd, sys, time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from common import *  # noqa: E402
import bank as bk  # noqa: E402

ERG = 1_000_000_000
STATE = HERE / "state"
STATE.mkdir(exist_ok=True)
FUND_SRC = "{ sigmaProp(HEIGHT > 0) }"


def keys():
    p = STATE / "keys.json"
    if p.exists():
        return json.loads(p.read_text())
    k = {}
    for name in ("K1", "K2", "K3"):
        x = rnd.randbelow(bk.N - 1) + 1
        pk = bk.enc(bk.mul(x))
        k[name] = {"secret": f"{x:064x}", "pk": pk, "key": bk.blake(bytes.fromhex(pk)).hex()}
    p.write_text(json.dumps(k, indent=1))
    return k


def dlog(k):
    return {"dlog": [k["secret"]]}


def byte_c(b):
    return "02" + f"{b & 0xff:02x}"


def long8(v):
    return (v & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "big").hex()


def fund(values):
    """Keyless fund boxes of exactly these values (devnet only)."""
    ft, fa = compile_tree(FUND_SRC, {})
    tx = send([{"address": fa, "value": v} for v in values])
    got, used = [], set()
    for v in values:
        o = [o for o in at(tx, ft) if o["value"] == v and o["boxId"] not in used][0]
        used.add(o["boxId"])
        got.append(o)
    return got


# ------------------------------------------------------------------ control
def stage_control():
    run = Run("7-control", HERE, "results-control.json")
    t, a = compile_tree((HERE / "AvlControl.es").read_text(), {})
    log = "control.log"
    (STATE / log).unlink(missing_ok=True)
    empty = bk.avl("control.log", 8, [])["digestBefore"]
    entries = [(os.urandom(32).hex(), long8(i + 1)) for i in range(3)]
    r = bk.avl(log, 8, [f"insert:{k}:{v}" for k, v in entries])
    dep = send([{"address": a, "value": 10_000_000, "registers": {"R4": bk.avl_tree_c(empty, 1, 8)}}
                for _ in range(2)])
    b1, b2 = at(dep, t)
    run.tree("AvlControl", t, a, b1["boxId"])
    h = full_height()

    def tx(b, proof):
        return {"inputs": [inp(b["boxId"], {"1": coll_bytes(proof), "2": bk.kv_coll(entries),
                                             "3": coll_bytes(r["digest"])})],
                "dataInputs": [], "outputs": [out(b["value"], NOBODY_TREE, h)]}
    pr = r["proof"]
    flips = []
    for pos in (len(pr) - 2, len(pr) - 4, 2 * 40):
        bad = pr[:pos] + f"{int(pr[pos:pos + 2], 16) ^ 1:02x}" + pr[pos + 2:]
        got, o = run.check(f"c2.{len(flips)}", f"three inserts, proof byte {pos // 2} flipped (recorded)", tx(b2, bad),
                           None, sibling="c1")
        flips.append(got)
        if got == "REFUSE":
            break
    # a byte-flipped proof makes the verifier throw (EVAL-ERROR), so the control's refusal is a WELL-FORMED proof of
    # the same three inserts built against another starting tree (one extra key): the script's insert must be None
    (STATE / "control-other.log").unlink(missing_ok=True)
    bk.avl("control-other.log", 8, [f"insert:{'00' * 31 + '01'}:{long8(9)}"], commit=True)
    stale = bk.avl("control-other.log", 8, [f"insert:{k}:{v}" for k, v in entries])
    # Re-registered after runs 2-3 (results-control-run2/3.json): on 6.0.7 a failed AVL operation throws inside the
    # interpreter (Failure(InvocationTargetException)) for byte-flipped AND for well-formed stale proofs, so no
    # proof failure is ever a plain false; the control's negative is "never accepted", class EVAL-ERROR.
    c3, _ = run.check("c3", "three inserts, a well-formed proof built against another tree", tx(b2, stale["proof"]),
                      "EVAL-ERROR", sibling="c1")
    run.check("c1", "three inserts: the script's digest equals the helper's", tx(b1, pr), "ACCEPT")
    run.doc["control"] = {"entries": entries, "helper_digest": r["digest"], "empty_digest": empty,
                          "byte_flips": flips, "stale_proof": c3,
                          "passed": run.doc["cases"][-1]["got"] == "ACCEPT" and c3 != "ACCEPT"
                          and "ACCEPT" not in flips}
    run.save()
    print("control passed" if run.doc["control"]["passed"] else "CONTROL FAILED")


# ------------------------------------------------------------------ 7a
class BankBox:
    """The bank box and its helper state (accounts tree, value length 8)."""

    def __init__(self, run, tree, addr, log, box):
        self.run, self.tree, self.addr, self.log, self.box = run, tree, addr, log, box

    def digest(self, box=None):
        return (box or self.box)["additionalRegisters"]["R4"][2:68]

    def assert_digest(self):
        d = bk.avl(self.log, 8, [])["digestBefore"]
        if d != self.digest():
            raise SystemExit(f"STOP: helper digest {d} != bank R4 digest {self.digest()}")

    def total(self):
        r5 = self.box["additionalRegisters"]["R5"]
        v = 0
        for i, b in enumerate(bytes.fromhex(r5[2:])):
            v |= (b & 0x7F) << (7 * i)
        return (v >> 1) ^ -(v & 1)

    def succ(self, h, value, digest, total, nft=True, regs_extra=None):
        regs = {"R4": bk.avl_tree_c(digest, 3, 8), "R5": long_c(total)}
        if regs_extra:
            regs.update(regs_extra)
        return out(value, self.tree, h, self.box["assets"] if nft else [], regs)


def stage_7a():
    run = Run("7a-bank", HERE, "results-7a.json")
    k = keys()
    run.doc["account_keys"] = {n: {"pk": v["pk"], "key": v["key"]} for n, v in k.items()}
    run.doc["signers"] = {"A": "K1 (external dlog secret)", "B": "K2 (external dlog secret)"}
    t, a = compile_tree((HERE / "Bank.es").read_text(), {})
    log = "7a.log"
    (STATE / log).unlink(missing_ok=True)
    empty = bk.avl(log, 8, [])["digestBefore"]
    nft, fake_nft = issue("BANK-7A"), issue("BANK-7A-FAKE")
    regs0 = {"R4": bk.avl_tree_c(empty, 3, 8), "R5": long_c(0)}
    dep = send([{"address": a, "value": 10_000_000, "assets": [{"tokenId": nft, "amount": 1}], "registers": regs0},
                {"address": a, "value": 10_000_000, "assets": [{"tokenId": fake_nft, "amount": 1}],
                 "registers": regs0}])
    real = [o for o in at(dep, t) if o["assets"][0]["tokenId"] == nft][0]
    fake = [o for o in at(dep, t) if o["assets"][0]["tokenId"] == fake_nft][0]
    B_ = BankBox(run, t, a, log, real)
    run.tree("Bank", t, a, real["boxId"])
    f1a, f1b, f1c, f1d, fh = fund([1 * ERG, 1 * ERG, ERG // 2, ERG // 2, ERG // 2])
    K1, K2 = k["K1"], k["K2"]

    def deposit_tx(key, new_bal, fund_box, action, credit_total=None, value_delta=None, nft=True, bank_first=True,
                   proof=None, extra_inputs=(), h=None):
        h = h or full_height()
        op = "insert" if action == 1 else "update"
        r = bk.avl(log, 8, [f"{op}:{key}:{long8(new_bal)}"])
        ext = {"1": coll_bytes(proof or r["proof"]), "2": coll_bytes(key), "3": long_c(new_bal), "5": byte_c(action)}
        if action == 2:
            ext["4"] = coll_bytes(bk.avl(log, 8, [f"lookup:{key}"])["proof"])
        old = 0
        if action == 2:
            old = int(bk.avl(log, 8, [f"lookup:{key}"])["results"][0].split(":")[1], 16)
        credit = new_bal - old
        tot = B_.total() + (credit if credit_total is None else credit_total)
        val = B_.box["value"] + (fund_box["value"] if value_delta is None else value_delta)
        outs = [B_.succ(h, val, r["digest"], tot, nft)]
        if not nft:
            outs.append(out(1_000_000, NOBODY_TREE, h, B_.box["assets"]))
            outs[0]["value"] -= 1_000_000
        rest = B_.box["value"] + fund_box["value"] - sum(o["value"] for o in outs)
        if rest > 0:
            outs.append(out(rest, NOBODY_TREE, h))
        ins = [inp(B_.box["boxId"], ext), inp(fund_box["boxId"])]
        if not bank_first:
            ins = list(extra_inputs) + ins
        return {"inputs": ins, "dataInputs": [], "outputs": outs}, r

    def commit(r_ops, mined):
        bk.avl(log, 8, r_ops, commit=True)
        B_.box = [o for o in mined["outputs"] if o["ergoTree"] == t and o["assets"]
                  and o["assets"][0]["tokenId"] == nft][0]
        B_.assert_digest()

    B_.assert_digest()
    tx, _ = deposit_tx(K1["key"], 2 * ERG, f1a, 1)
    run.check(1, "deposit crediting 2 ERG while adding 1 ERG (new account K1)", tx, "REFUSE", sibling=3)
    tx, _ = deposit_tx(K1["key"], 1 * ERG, f1a, 1, nft=False)
    run.check(2, "deposit whose successor lacks the NFT", tx, "REFUSE", sibling=3)
    tx, r3 = deposit_tx(K1["key"], 1 * ERG, f1a, 1)
    m = run.check(3, "deposit 1 ERG to account K1 (new), honest", tx, "ACCEPT", submit=True, cost=True)
    commit([f"insert:{K1['key']}:{long8(ERG)}"], m)

    tx, _ = deposit_tx(K2["key"], 1 * ERG, f1b, 1, proof=r3["proof"])
    # re-registered EVAL-ERROR (the plan said REFUSE): a stale proof throws on 6.0.7 (results-control.json c3)
    run.check(4, "deposit to K2 with the AVL proof of case 3 replayed", tx, "EVAL-ERROR", sibling=6)
    h = full_height()
    r = bk.avl(log, 8, [f"update:{K1['key']}:{long8(ERG // 2)}"])
    ext = {"1": coll_bytes(r["proof"]), "2": coll_bytes(K1["key"]), "3": long_c(ERG // 2), "5": byte_c(2),
           "4": coll_bytes(bk.avl(log, 8, [f"lookup:{K1['key']}"])["proof"])}
    steal = {"inputs": [inp(B_.box["boxId"], ext)], "dataInputs": [],
             "outputs": [B_.succ(h, B_.box["value"] - ERG // 2, r["digest"], B_.total() - ERG // 2),
                         out(ERG // 2, NOBODY_TREE, h)]}
    run.check(5, "keyless 'deposit' setting K1's balance lower, taking the difference", steal, "REFUSE", sibling=6)
    tx, _ = deposit_tx(K2["key"], 1 * ERG, f1b, 1)
    m = run.check(6, "deposit 1 ERG to account K2 (new), honest", tx, "ACCEPT", submit=True)
    commit([f"insert:{K2['key']}:{long8(ERG)}"], m)

    def withdraw(n, label, base, key, amount, signer, expect, sibling=None, submit=False, cost=False):
        B_.assert_digest()
        h = full_height()
        bal = int(bk.avl(log, 8, [f"lookup:{key['key']}"])["results"][0].split(":")[1], 16)
        r = bk.avl(log, 8, [f"update:{key['key']}:{long8(bal - amount)}"]) if bal - amount >= 0 else \
            bk.avl(log, 8, [f"update:{key['key']}:{long8(bal - amount)}"])
        ext = {"1": coll_bytes(r["proof"]), "2": coll_bytes(key["key"]), "3": long_c(bal - amount), "5": byte_c(3),
               "4": coll_bytes(bk.avl(log, 8, [f"lookup:{key['key']}"])["proof"]), "6": ge_c(key["pk"])}
        outs = [B_.succ(h, B_.box["value"] - amount, r["digest"], B_.total() - amount),
                out(amount, "0008cd" + key["pk"], h)]
        m = run.key_spend(n, label, base, [B_.box["boxId"]], [], outs, expect, sibling, submit=submit, cost=cost,
                          ext={B_.box["boxId"]: ext}, secrets=dlog(signer))
        return m, r, bal - amount

    withdraw(7, "withdrawal from K1 of balance + 1, signed by A (K1)", A, K1, ERG + 1, K1, "REFUSE", sibling=9)
    withdraw(8, "withdrawal from K1 signed by B (K2's key)", B, K1, ERG // 2, K2, "REFUSE", sibling=9)
    m, r, nb = withdraw(9, "withdrawal of half of K1 by A, honest", A, K1, ERG // 2, K1, "ACCEPT", submit=True,
                        cost=True)
    commit([f"update:{K1['key']}:{long8(nb)}"], m)

    # look-alike bank at INPUTS(0), the real bank at INPUTS(1), honest deltas on the real bank
    h = full_height()
    tx, r10 = deposit_tx(K2["key"], ERG + ERG // 2, f1c, 2, h=h)
    fake_in = inp(fake["boxId"])
    tx10 = {"inputs": [fake_in] + tx["inputs"], "dataInputs": [],
            "outputs": tx["outputs"] + [out(fake["value"], t, h, fake["assets"], fake["additionalRegisters"])]}
    run.check(10, "look-alike bank (another NFT) at INPUTS(0), the bank at INPUTS(1), honest deltas", tx10, "REFUSE",
              sibling="10.s")
    run.check("10.s", "the same deltas with the bank at INPUTS(0)", tx, "ACCEPT")
    tx11 = json.loads(json.dumps(tx))
    tx11["outputs"][0]["value"] -= 1
    tx11["outputs"].append(out(1_000_000, NOBODY_TREE, h))
    tx11["outputs"][0]["value"] -= 1_000_000 - 1 - 1
    # keep the total as the honest successor, value 1 nanoERG lower; the leftover goes to a stranger
    tx11["outputs"][0]["value"] = tx["outputs"][0]["value"] - 1
    tx11["outputs"][-1]["value"] = 1_000_000
    tx11["inputs"].append(inp(fh["boxId"]))
    tx11["outputs"].insert(1, out(fh["value"] - 1_000_000 + 1, NOBODY_TREE, h))
    run.check(11, "successor keeping the total but value - 1", tx11, "REFUSE", sibling="11.s")
    run.check("11.s", "the honest successor (same as 10.s)", tx, "ACCEPT")
    run.doc["bank_box"] = B_.box["boxId"]
    run.doc["helper_digest_final"] = bk.avl(log, 8, [])["digestBefore"]
    run.save()
    bad = [c for c in run.doc["cases"] if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


# ------------------------------------------------------------------ 7b
def stage_7b():
    """Payee-bound cheques. Rows 7, 7b and 12 are pre-registered EVAL-ERROR, not the plan's REFUSE: on 6.0.7 a failed
    AVL operation (insert with a missing or stale proof, contains with another key's proof) throws
    (results-control.json)."""
    run = Run("7b-cheques", HERE, "results-7b.json")
    k = keys()
    K1, K2 = k["K1"], k["K2"]
    t, a = compile_tree((HERE / "ChequeBank.es").read_text(), {})
    for lg in ("7b-acc.log", "7b-spent.log", "7b-comm.log"):
        (STATE / lg).unlink(missing_ok=True)
    acc0 = bk.avl("7b-acc.log", 8, [])["digestBefore"]
    set0 = bk.avl("7b-spent.log", 0, [])["digestBefore"]
    nft, fake_nft = issue("CHEQUEBANK"), issue("CHEQUEBANK-FAKE")
    regs = lambda acc, tot, sp, cm: {"R4": bk.avl_tree_c(acc, 3, 8), "R5": long_c(tot),
                                     "R6": bk.avl_tree_c(sp, 1, 0), "R7": bk.avl_tree_c(cm, 1, 0)}
    bank = at(send([{"address": a, "value": 10_000_000, "assets": [{"tokenId": nft, "amount": 1}],
                     "registers": regs(acc0, 0, set0, set0)}]), t)[0]
    run.tree("ChequeBank", t, a, bank["boxId"])
    st = {"box": bank}

    def dig(r):
        return st["box"]["additionalRegisters"][r][2:68]

    def total():
        r5 = st["box"]["additionalRegisters"]["R5"]
        v = 0
        for i, b in enumerate(bytes.fromhex(r5[2:])):
            v |= (b & 0x7F) << (7 * i)
        return (v >> 1) ^ -(v & 1)

    def check_digests():
        for lg, vl, r in (("7b-acc.log", 8, "R4"), ("7b-spent.log", 0, "R6"), ("7b-comm.log", 0, "R7")):
            d = bk.avl(lg, vl, [])["digestBefore"]
            if d != dig(r):
                raise SystemExit(f"STOP: helper {lg} digest {d} != bank {r} {dig(r)}")

    def adopt(mined):
        st["box"] = [o for o in mined["outputs"] if o["ergoTree"] == t][0]

    def bal(key):
        r = bk.avl("7b-acc.log", 8, [f"lookup:{key}"])["results"][0]
        return int(r.split(":")[1], 16) if r.startswith("some:") else None

    def succ(h, value, acc, tot, sp, cm):
        return out(value, t, h, st["box"]["assets"], regs(acc, tot, sp, cm))

    # deposits: K1 3 ERG, K2 1 ERG (fund boxes are keyless)
    for key, amt in ((K1, 3 * ERG), (K2, 1 * ERG)):
        f = fund([amt])[0]
        h = full_height()
        r = bk.avl("7b-acc.log", 8, [f"insert:{key['key']}:{long8(amt)}"])
        ext = {"1": coll_bytes(r["proof"]), "2": coll_bytes(key["key"]), "3": long_c(amt), "5": byte_c(1)}
        tx = {"inputs": [inp(st["box"]["boxId"], ext), inp(f["boxId"])], "dataInputs": [],
              "outputs": [succ(h, st["box"]["value"] + amt, r["digest"], total() + amt, dig("R6"), dig("R7"))]}
        m = run.check(f"d.{key['key'][:4]}", "deposit (setup)", tx, "ACCEPT", submit=True)
        bk.avl("7b-acc.log", 8, [f"insert:{key['key']}:{long8(amt)}"], commit=True)
        adopt(m)
    check_digests()
    P_tree, Q_tree = "0008cd" + pk_of(A, 3), NOBODY_TREE

    def cheque(key, payee_tree, amount, expiry, nft_id=None, nonce=None):
        body = bytes.fromhex(nft_id or nft) + bytes.fromhex(key["key"]) + bk.blake(bytes.fromhex(payee_tree)) + \
            amount.to_bytes(8, "big") + expiry.to_bytes(8, "big") + (nonce or os.urandom(8))
        return body.hex()

    def sign(secret_key, body):
        x = int(secret_key["secret"], 16)
        return bk.schnorr_sign(x, bk.blake(bytes.fromhex(body)))

    def cash_tx(body, signer=None, sig=None, payee_tree=None, pay_value=None, acct=None, pk=None, spent_proof=None,
                spent_digest=None, action=4, contains_proof=None, h=None, debit=None):
        h = h or full_height()
        acct = acct or K1
        amount = int(body[192:208], 16)
        debit = amount if debit is None else debit
        b0 = bal(acct["key"])
        nb = b0 - debit
        ra = bk.avl("7b-acc.log", 8, [f"update:{acct['key']}:{long8(nb)}"])
        cid = bk.blake(bytes.fromhex(body)).hex()
        rs = bk.avl("7b-spent.log", 0, [f"insert:{cid}:"])
        ext = {"5": byte_c(action), "2": coll_bytes(acct["key"]), "3": long_c(nb), "1": coll_bytes(ra["proof"]),
               "4": coll_bytes(bk.avl("7b-acc.log", 8, [f"lookup:{acct['key']}"])["proof"]),
               "6": ge_c(pk or acct["pk"]), "8": coll_bytes(body)}
        if spent_proof != "none":
            ext["15"] = coll_bytes(spent_proof or rs["proof"])
        if action == 4:
            R, s = sig or sign(signer or acct, body)
            ext["13"], ext["14"] = ge_c(R), coll_bytes(s)
        else:
            ext["16"] = coll_bytes(contains_proof or bk.avl("7b-comm.log", 0, [f"lookup:{cid}"])["proof"])
        pv = amount if pay_value is None else pay_value
        outs = [succ(h, st["box"]["value"] - pv, ra["digest"], total() - debit,
                     spent_digest or (rs["digest"] if spent_proof != "none" else dig("R6")), dig("R7")),
                out(pv, payee_tree or P_tree, h)]
        return {"inputs": [inp(st["box"]["boxId"], ext)], "dataInputs": [], "outputs": outs}, ra, rs, cid, nb

    def commit_cash(mined, ra_ops, rs_ops):
        bk.avl("7b-acc.log", 8, ra_ops, commit=True)
        bk.avl("7b-spent.log", 0, rs_ops, commit=True)
        adopt(mined)
        check_digests()

    H = full_height() + 1
    C1 = cheque(K1, P_tree, ERG // 4, H + 500)
    R, s = sign(K1, C1)
    s_forged = bk.bigint_bytes(int.from_bytes(bytes.fromhex(s), "big", signed=True) + 1).hex()
    run.check(1, "cash C1 to payee P with the signature's s + 1 (forged)", cash_tx(C1, sig=(R, s_forged))[0], "REFUSE",
              sibling=6)
    run.check(2, "cash C1 to payee Q", cash_tx(C1, sig=(R, s), payee_tree=Q_tree)[0], "REFUSE", sibling=6)
    run.check(3, "cash C1 with the payee output's value = amount + 1, cheque unchanged",
              cash_tx(C1, sig=(R, s), pay_value=ERG // 4 + 1)[0], "REFUSE", sibling=6)
    C1n = cheque(K1, P_tree, ERG // 4, H + 500, nft_id=fake_nft, nonce=bytes.fromhex(C1[224:]))
    run.check(4, "cash C1 with nft = the look-alike's id in the message, signed consistently", cash_tx(C1n)[0],
              "REFUSE", sibling=6)
    C1k = cheque(K2, P_tree, ERG // 4, H + 500, nonce=bytes.fromhex(C1[224:]))
    run.check(5, "cash C1 against account K2 (key field changed, signed consistently by K1)",
              cash_tx(C1k, signer=K1, acct=K2, pk=K1["pk"])[0], "REFUSE", sibling=6)
    tx, ra, rs, cid1, nb = cash_tx(C1, sig=(R, s))
    stale_spent = dig("R6")
    m = run.check(6, "cash C1 (K1 -> P, within expiry), honest", tx, "ACCEPT", submit=True, cost=True)
    commit_cash(m, [f"update:{K1['key']}:{long8(nb)}"], [f"insert:{cid1}:"])

    # double cash
    C6 = cheque(K1, P_tree, ERG // 10, H + 500)
    run.check(7, "re-cash C1 on the new bank box with no spent-set update (no proof variable)",
              cash_tx(C1, sig=(R, s), spent_proof="none")[0], "EVAL-ERROR", sibling="7.s")
    run.check("7b", "re-cash C1 with an insert proof built against the stale pre-case-6 R6 digest",
              cash_tx(C1, sig=(R, s), spent_proof=rs["proof"], spent_digest=rs["digest"])[0], "EVAL-ERROR",
              sibling="7.s")
    run.check("7.s", "cash C6, a fresh cheque (sibling of 7, 7b), checked", cash_tx(C6)[0], "ACCEPT")
    again = bk.avl("7b-spent.log", 0, [f"insert:{cid1}:"])
    run.record("7x", "re-cash C1 with a fresh insert proof: the helper cannot produce one for an existing key", None,
               "recorded", "helper", detail=f"helper result: {again['results']}")

    # expiry and balance
    h = full_height()
    HN = h + 1
    C2 = cheque(K1, P_tree, ERG // 10, HN - 1)
    run.check(8, f"cash C2 with expiry = HEIGHT - 1 ({HN - 1}; evaluated HEIGHT {HN})", cash_tx(C2, h=h)[0], "REFUSE",
              sibling="8.s")
    C2s = cheque(K1, P_tree, ERG // 10, HN)
    run.check("8.s", f"cash C2' with expiry = HEIGHT ({HN})", cash_tx(C2s, h=h)[0], "ACCEPT")
    rem = bal(K1["key"])
    C3 = cheque(K1, P_tree, rem + 1, H + 500)
    run.check(9, f"cash C3 whose amount ({rem + 1}) exceeds K1's remaining balance", cash_tx(C3)[0], "REFUSE",
              sibling="9.s")
    C3s = cheque(K1, P_tree, rem, H + 500)
    run.check("9.s", "cash C3' at exactly the balance", cash_tx(C3s)[0], "ACCEPT")

    # pre-committed cheques
    C4 = cheque(K1, P_tree, ERG // 10, H + 500)
    C5 = cheque(K1, P_tree, ERG // 10, H + 500)
    ids = [bk.blake(bytes.fromhex(c)).hex() for c in (C4, C5)]

    def commit_tx(base, signer, bodies, n, label, expect, sibling=None, submit=False):
        h = full_height()
        r = bk.avl("7b-comm.log", 0, [f"insert:{i}:" for i in [bk.blake(bytes.fromhex(b)).hex() for b in bodies]])
        ext = {"5": byte_c(6), "2": coll_bytes(K1["key"]), "6": ge_c(K1["pk"]), "17": bk.keys_coll(bodies),
               "1": coll_bytes(r["proof"])}
        outs = [succ(h, st["box"]["value"], dig("R4"), total(), dig("R6"), r["digest"])]
        return run.key_spend(n, label, base, [st["box"]["boxId"]], [], outs, expect, sibling, submit=submit,
                             cost=submit, ext={st["box"]["boxId"]: ext}, secrets=dlog(signer)), r

    commit_tx(B, K2, [C4], 10, "B (K2) commits a cheque whose account field is K1", "REFUSE", sibling=11)
    m, r = commit_tx(A, K1, [C4, C5], 11, "A (K1) commits the ids of C4 and C5 into R7", "ACCEPT", submit=True)
    bk.avl("7b-comm.log", 0, [f"insert:{i}:" for i in ids], commit=True)
    adopt(m)
    check_digests()
    C7 = cheque(K1, P_tree, ERG // 10, H + 500)
    run.check(12, "cash C7, never committed, with a contains proof for C5's id", cash_tx(C7, action=5, contains_proof=
              bk.avl("7b-comm.log", 0, [f"lookup:{ids[1]}"])["proof"])[0], "EVAL-ERROR", sibling=13)
    tx13, ra13, rs13, cid4, nb13 = cash_tx(C4, action=5)
    m13 = None
    code, o = call(A, "/transactions/check", tx13)
    # contention: 13 submitted, then 14 chained on 13's unconfirmed bank output, back to back; the helper runs 13 and
    # 14 in one uncommitted session (temporary logs) and commits both once both are mined
    import shutil
    for lg in ("7b-acc.log", "7b-spent.log"):
        shutil.copy(STATE / lg, STATE / (lg + ".session"))
    t13 = run.check(13, "cash C4 by membership, honest (submitted; mined below)", tx13, "ACCEPT", submit=False)
    tid13 = must(A, "/transactions", tx13)
    c13, ins13 = run.mempool_cost(tid13)
    run.doc["cases"][-1].update({"tx_id": tid13, "cost": c13, "cost_instrument": ins13})
    out13 = None
    for _ in range(50):
        cc, e = call(A, f"/transactions/unconfirmed/byTransactionId/{tid13}")
        if cc == 200:
            out13 = e["outputs"][0]
            break
        time.sleep(0.2)
    bk.avl("7b-acc.log.session", 8, [f"update:{K1['key']}:{long8(nb13)}"], commit=True)
    bk.avl("7b-spent.log.session", 0, [f"insert:{cid4}:"], commit=True)
    # build 14 against the session logs and 13's unconfirmed bank output
    cid5 = ids[1]
    nb14 = nb13 - ERG // 10
    ra14 = bk.avl("7b-acc.log.session", 8, [f"update:{K1['key']}:{long8(nb14)}"])
    rs14 = bk.avl("7b-spent.log.session", 0, [f"insert:{cid5}:"])
    h = full_height()
    ext14 = {"5": byte_c(5), "2": coll_bytes(K1["key"]), "3": long_c(nb14), "1": coll_bytes(ra14["proof"]),
             "4": coll_bytes(bk.avl("7b-acc.log.session", 8, [f"lookup:{K1['key']}"])["proof"]),
             "6": ge_c(K1["pk"]), "8": coll_bytes(C5), "15": coll_bytes(rs14["proof"]),
             "16": coll_bytes(bk.avl("7b-comm.log", 0, [f"lookup:{cid5}"])["proof"])}
    tot13 = total() - ERG // 10
    tx14 = {"inputs": [inp(out13["boxId"], ext14)], "dataInputs": [],
            "outputs": [out(out13["value"] - ERG // 10, t, h, st["box"]["assets"],
                            regs(ra14["digest"], tot13 - ERG // 10, rs14["digest"], dig("R7"))),
                        out(ERG // 10, P_tree, h)]}
    c14, o14 = call(A, "/transactions/check", tx14)
    tid14 = must(A, "/transactions", tx14) if c14 == 200 else None
    m13 = wait_tx_outputs(A, tid13)
    m14 = wait_tx_outputs(A, tid14) if tid14 else None
    run.record(14, "contention: cash C5 chained on case 13's unconfirmed output, submitted back to back", "ACCEPT",
               classify(c14, o14) if not m14 else "ACCEPT", "" if m14 else "node-check", tx_id=tid14,
               detail=str(o14)[:300] if c14 != 200 else "",
               heights={"13_included": m13.get("inclusionHeight"), "14_included": m14.get("inclusionHeight") if m14
                        else None, "same_block": bool(m14) and m13.get("inclusionHeight") == m14.get("inclusionHeight")})
    bk.avl("7b-acc.log", 8, [f"update:{K1['key']}:{long8(nb13)}"], commit=True)
    bk.avl("7b-spent.log", 0, [f"insert:{cid4}:"], commit=True)
    adopt(m13)
    if m14:
        bk.avl("7b-acc.log", 8, [f"update:{K1['key']}:{long8(nb14)}"], commit=True)
        bk.avl("7b-spent.log", 0, [f"insert:{cid5}:"], commit=True)
        adopt(m14)
    check_digests()
    costs = {c["n"]: c["cost"] for c in run.doc["cases"]}
    run.doc["schnorr_minus_contains"] = None if None in (costs.get(6), costs.get(13)) else costs[6] - costs[13]
    run.save()
    print("cost 6 - 13 =", run.doc["schnorr_minus_contains"])
    bad = [c for c in run.doc["cases"] if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


# ------------------------------------------------------------------ 7c
def local_eval(tx, boxes, height):
    job = STATE / "localeval-job.json"
    job.write_text(json.dumps({"tx": tx, "boxes": boxes, "dataBoxes": [], "height": height}))
    import subprocess
    o = subprocess.run(["java", "-cp", bk.CP, "LocalEval", "eval", str(job)], capture_output=True, text=True)
    if o.returncode:
        return {"error": o.stderr[-400:]}
    return json.loads(o.stdout.strip().splitlines()[-1])


def stage_7c():
    """Private payments. Rows 4 and 4b are pre-registered EVAL-ERROR (the plan said REFUSE): a missing or stale R7
    insert proof throws on 6.0.7 (results-control.json). Rows 1 and 2 reduce the whole proposition to false, so the
    wallet refuses to sign ("Script reduced to false") and the node's check of the unsigned transaction is recorded
    beside it."""
    run = Run("7c-ring", HERE, "results-7c.json")
    DENOM = 10_000_000
    H, ctr = bk.hash_to_point(b"policy-7c")
    run.doc["H"] = {"seed": "policy-7c", "point": H, "counter": ctr,
                    "method": "try-and-increment: x = blake2b256(seed ++ counter as 4 bytes), point 0x02 ++ x"}
    t, a = compile_tree((HERE / "RingBank.es").read_text(), {"$H": H, "$DENOML": f"{DENOM}L"})
    for lg in ("7c-notes.log", "7c-images.log", "7c-acc.log"):
        (STATE / lg).unlink(missing_ok=True)
    e8 = bk.avl("7c-acc.log", 8, [])["digestBefore"]
    e0 = bk.avl("7c-notes.log", 0, [])["digestBefore"]
    nft = issue("RINGBANK")
    regs = lambda notes, images: {"R4": bk.avl_tree_c(e8, 3, 8), "R5": long_c(0),
                                  "R6": bk.avl_tree_c(notes, 1, 0), "R7": bk.avl_tree_c(images, 1, 0)}
    st = {"box": at(send([{"address": a, "value": 10_000_000, "assets": [{"tokenId": nft, "amount": 1}],
                           "registers": regs(e0, e0)}]), t)[0]}
    run.tree("RingBank", t, a, st["box"]["boxId"])
    G_enc = bk.enc(bk.Gpt)
    notes = []
    for _ in range(70):
        r = rnd.randbelow(bk.N - 1) + 1
        C = bk.enc(bk.mul(r))
        notes.append({"r": r, "C": C, "key": bk.blake(bytes.fromhex(C)).hex(),
                      "I": bk.enc(bk.mul(r, bk.dec(H)))})
    P_tree = "0008cd" + pk_of(A, 3)

    def dig(r):
        return st["box"]["additionalRegisters"][r][2:68]

    def check_digests():
        for lg, r in (("7c-notes.log", "R6"), ("7c-images.log", "R7")):
            d = bk.avl(lg, 0, [])["digestBefore"]
            if d != dig(r):
                raise SystemExit(f"STOP: helper {lg} digest {d} != bank {r} {dig(r)}")

    def adopt(m):
        st["box"] = [o for o in m["outputs"] if o["ergoTree"] == t][0]

    def deposit_tx(batch, value_notes=None):
        h = full_height()
        f = fund([DENOM * (value_notes if value_notes is not None else len(batch))])[0]
        r = bk.avl("7c-notes.log", 0, [f"insert:{n['key']}:" for n in batch])
        ext = {"5": byte_c(7), "18": bk.ge_coll([n["C"] for n in batch]), "1": coll_bytes(r["proof"])}
        tx = {"inputs": [inp(st["box"]["boxId"], ext), inp(f["boxId"])], "dataInputs": [],
              "outputs": [out(st["box"]["value"] + f["value"], t, h, st["box"]["assets"], regs(r["digest"], dig("R7")))]}
        return tx, r

    tx, _ = deposit_tx(notes[:2], value_notes=1)
    run.check(0, "deposit inserting 2 commitments while adding 1 x DENOM", tx, "REFUSE", sibling="0.s")
    for i, batch in enumerate((notes[:2], notes[2:36], notes[36:70])):
        tx, r = deposit_tx(batch)
        m = run.check("0.s" if i == 0 else f"0.d{i}", f"deposit {len(batch)} notes, honest", tx, "ACCEPT",
                      submit=True, cost=(i == 0))
        bk.avl("7c-notes.log", 0, [f"insert:{n['key']}:" for n in batch], commit=True)
        adopt(m)
        check_digests()
    used = set()

    def pay_tx(payer, ring, I=None, value=DENOM, images_proof=None, images_digest=None, no_insert=False):
        h = full_height()
        keys = [n["key"] if isinstance(n, dict) else n for n in ring]
        rg = bk.avl("7c-notes.log", 0, [f"lookup:{k}" for k in keys])
        I = I or payer["I"]
        ri = bk.avl("7c-images.log", 0, [f"insert:{bk.blake(bytes.fromhex(I)).hex()}:"])
        ext = {"5": byte_c(8), "18": bk.ge_coll([n["C"] if isinstance(n, dict) else n for n in ring]),
               "16": coll_bytes(rg["proof"]), "19": ge_c(I)}
        if not no_insert:
            ext["15"] = coll_bytes(images_proof or ri["proof"])
        outs = [out(st["box"]["value"] - value, t, h, st["box"]["assets"],
                    regs(dig("R6"), dig("R7") if no_insert else (images_digest or ri["digest"]))),
                out(value, P_tree, h)]
        unsigned = {"inputs": [{"boxId": st["box"]["boxId"], "extension": ext}], "dataInputs": [], "outputs": outs}
        return unsigned, ri, ext

    def dht(payer, I=None):
        return {"dht": [{"secret": f"{payer['r']:064x}", "g": G_enc, "h": H, "u": payer["C"], "v": I or payer["I"]}]}

    def ring_for(payer, n):
        others = [x for x in notes if x is not payer][:n - 1]
        pos = rnd.randbelow(n)
        return others[:pos] + [payer] + others[pos:]

    def pay(nn, label, payer, ring, expect, sibling=None, submit=False, measure=False, **kw):
        unsigned, ri, ext = pay_tx(payer, ring, **{k: v for k, v in kw.items() if k in
                                                   ("I", "value", "images_proof", "images_digest", "no_insert")})
        h0 = full_height()
        code, signed = run.sign(A, unsigned, [st["box"]["boxId"]], (), dht(payer, kw.get("I")))
        if code != 200:
            row = run.key_spend(nn, label, A, [st["box"]["boxId"]], [], unsigned["outputs"], expect, sibling,
                                ext={st["box"]["boxId"]: ext}, secrets=dht(payer, kw.get("I")), ring=len(ring))
            return None, ri, None
        le = local_eval(signed, [must(A, f"/utxo/byId/{st['box']['boxId']}")], h0 + 1)
        if measure:
            code2, o2 = call(A, "/transactions/check", signed)
            got = classify(code2, o2)
            mined, cost, ins = None, None, None
            par = run.doc["node"]["parameters"]
            sc = sum(x.get("cost", 0) for x in le.get("inputs", []))
            derived = sc + par["inputCost"] * 1 + par["outputCost"] * len(signed["outputs"])
            if got == "ACCEPT" and derived <= par["maxBlockCost"]:
                tid = must(A, "/transactions", signed)
                cost, ins = run.mempool_cost(tid)
                mined = wait_tx_outputs(A, tid)
            run.record(nn, label, None, got, "measured", detail=str(o2)[:300] if code2 != 200 else "",
                       cost=cost, instrument=ins, tx_id=signed.get("id"), heights={"before": h0},
                       ring=len(ring), local_eval=le, derived_total=derived,
                       proof_bytes=len(signed["inputs"][0]["spendingProof"]["proofBytes"]) // 2,
                       tx_bytes=le.get("tx_bytes"), mined=bool(mined))
            return mined, ri, le
        m = run.check(nn, label, signed, expect, sibling, submit=submit, cost=submit, ring=len(ring), local_eval=le,
                      proof_bytes=len(signed["inputs"][0]["spendingProof"]["proofBytes"]) // 2,
                      tx_bytes=le.get("tx_bytes"))
        return m, ri, le

    def payer_note():
        for n in notes:
            if n["C"] not in used:
                used.add(n["C"])
                return n

    p3 = payer_note()
    stranger = bk.enc(bk.mul(rnd.randbelow(bk.N - 1) + 1))
    bad_ring = ring_for(p3, 4)[:3] + [{"C": stranger, "key": bk.blake(bytes.fromhex(stranger)).hex()}]
    if p3 not in bad_ring:
        bad_ring[0] = p3
    pay(1, "pay with a ring containing one commitment not in R6", p3, bad_ring, "REFUSE", sibling=3)
    pay(2, "pay with amount DENOM + 1", p3, ring_for(p3, 4), "REFUSE", sibling=3, value=DENOM + 1)
    stale_images = bk.avl("7c-images.log", 0, [f"insert:{bk.blake(bytes.fromhex(p3['I'])).hex()}:"])
    m, ri, le = pay(3, "pay, N = 4, honest", p3, ring_for(p3, 4), "ACCEPT", submit=True)
    bk.avl("7c-images.log", 0, [f"insert:{bk.blake(bytes.fromhex(p3['I'])).hex()}:"], commit=True)
    adopt(m)
    check_digests()
    p4 = payer_note()
    pay(4, "pay a second note with no key-image insert (no proof variable)", p4, ring_for(p4, 4), "EVAL-ERROR",
        sibling="4.s", no_insert=True)
    pay("4.s", "the same payment with the insert, checked", p4, ring_for(p4, 4), "ACCEPT")
    pay("4b", "pay again with case 3's key image and an insert proof built against the stale pre-case-3 R7 digest",
        p3, ring_for(p3, 4), "EVAL-ERROR", sibling="4.s", images_proof=stale_images["proof"],
        images_digest=stale_images["digest"])
    again = bk.avl("7c-images.log", 0, [f"insert:{bk.blake(bytes.fromhex(p3['I'])).hex()}:"])
    run.record("4x", "pay again with case 3's image and a fresh insert proof: the helper cannot produce one", None,
               "recorded", "helper", detail=f"helper result: {again['results']}")
    other = [x for x in notes if x["C"] not in used and x is not p4][0]
    unsigned, _, ext = pay_tx(p4, ring_for(p4, 4), I=other["I"])
    code, s5 = run.sign(A, unsigned, [st["box"]["boxId"]], (), dht(p4, other["I"]))
    run.record("5x", "key image from another note's r while proving with this one's", None, "recorded", "prover",
               detail=f"wallet sign: {code} {str(s5)[:400]}")
    for n in (8, 16, 32, 64):
        pn = payer_note()
        m, ri, le = pay(f"6.{n}", f"pay, N = {n}, honest (measurement)", pn, ring_for(pn, n), None, measure=True)
        if m:
            bk.avl("7c-images.log", 0, [f"insert:{bk.blake(bytes.fromhex(pn['I'])).hex()}:"], commit=True)
            adopt(m)
            check_digests()
    series = []
    for c in run.doc["cases"]:
        if c.get("ring") and c["got"] in ("ACCEPT", "measured") or (c.get("ring") and str(c["n"]).startswith("6.")):
            le = c.get("local_eval") or {}
            sc = sum(x.get("cost", 0) for x in le.get("inputs", [])) if le else None
            series.append({"n": c["n"], "ring": c["ring"], "script_cost_local": sc, "derived_total": c.get(
                "derived_total"), "mempool_cost": c.get("cost"), "proof_bytes": c.get("proof_bytes"),
                "tx_bytes": c.get("tx_bytes"), "node": c["got"]})
    run.doc["series"] = series
    run.save()
    for x in series:
        print(x)
    bad = [c for c in run.doc["cases"] if c.get("ok") is False]
    print("ALL AS EXPECTED" if not bad else f"{len(bad)} UNEXPECTED")


def stage_7b_expiry():
    """Rerun of rows 8 / 8.s (harness bug: in the first run a block landed between building the cheques for
    HEIGHT 242 and checking them at 243, so 8.s, expiry 242, was correctly refused). Both transactions are built
    first; each is checked only if fullHeight is still the one it was built for, else both are rebuilt."""
    import urllib.request
    run = Run("7b-cheques", HERE, "results-7b.json")
    run.doc = json.loads(run.path.read_text())
    run.doc["cases"] = [c for c in run.doc["cases"] if c["n"] not in (8, "8.s")]
    run.bug(8, "a block landed between building rows 8 / 8.s for evaluated HEIGHT 242 and checking them (fullHeight "
               "242, HEIGHT 243): 8.s (expiry 242) was refused, correctly at 243",
            "--stage 7b-expiry: build both, check each only while fullHeight is unchanged, else rebuild")
    k = keys()
    K1 = k["K1"]
    tname = [t for t in run.doc["trees"] if t["name"] == "ChequeBank"][0]
    t = (HERE / "ChequeBank.tree").read_text().strip()
    req = urllib.request.Request(A + "/blockchain/box/unspent/byErgoTree?limit=5", data=json.dumps(t).encode(),
                                 headers={"Content-Type": "application/json"})
    box = json.load(urllib.request.urlopen(req))[0]
    nft = box["assets"][0]["tokenId"]
    P_tree = "0008cd" + pk_of(A, 3)
    regs = lambda acc, tot, sp, cm: {"R4": bk.avl_tree_c(acc, 3, 8), "R5": long_c(tot),
                                     "R6": bk.avl_tree_c(sp, 1, 0), "R7": bk.avl_tree_c(cm, 1, 0)}
    dig = lambda r: box["additionalRegisters"][r][2:68]
    r5 = box["additionalRegisters"]["R5"]
    v = 0
    for i, b in enumerate(bytes.fromhex(r5[2:])):
        v |= (b & 0x7F) << (7 * i)
    total = (v >> 1) ^ -(v & 1)
    for lg, vl, r in (("7b-acc.log", 8, "R4"), ("7b-spent.log", 0, "R6"), ("7b-comm.log", 0, "R7")):
        if bk.avl(lg, vl, [])["digestBefore"] != dig(r):
            raise SystemExit(f"STOP: helper {lg} != bank {r}")
    amt = ERG // 100

    def build(h, expiry):
        body = (bytes.fromhex(nft) + bytes.fromhex(K1["key"]) + bk.blake(bytes.fromhex(P_tree)) +
                amt.to_bytes(8, "big") + expiry.to_bytes(8, "big") + os.urandom(8)).hex()
        R, sg = bk.schnorr_sign(int(K1["secret"], 16), bk.blake(bytes.fromhex(body)))
        b0 = int(bk.avl("7b-acc.log", 8, [f"lookup:{K1['key']}"])["results"][0].split(":")[1], 16)
        ra = bk.avl("7b-acc.log", 8, [f"update:{K1['key']}:{long8(b0 - amt)}"])
        rs = bk.avl("7b-spent.log", 0, [f"insert:{bk.blake(bytes.fromhex(body)).hex()}:"])
        ext = {"5": byte_c(4), "2": coll_bytes(K1["key"]), "3": long_c(b0 - amt), "1": coll_bytes(ra["proof"]),
               "4": coll_bytes(bk.avl("7b-acc.log", 8, [f"lookup:{K1['key']}"])["proof"]), "6": ge_c(K1["pk"]),
               "8": coll_bytes(body), "15": coll_bytes(rs["proof"]), "13": ge_c(R), "14": coll_bytes(sg)}
        outs = [out(box["value"] - amt, t, h, box["assets"], regs(ra["digest"], total - amt, rs["digest"], dig("R7"))),
                out(amt, P_tree, h)]
        return {"inputs": [inp(box["boxId"], ext)], "dataInputs": [], "outputs": outs}

    for attempt in range(8):
        h = full_height()
        HN = h + 1
        t8, t8s = build(h, HN - 1), build(h, HN)
        if full_height() != h:
            continue
        g8, _ = run.check(8, f"cash C2 with expiry = HEIGHT - 1 ({HN - 1}; evaluated HEIGHT {HN}) (rerun)", t8,
                          "REFUSE", sibling="8.s", attempt=attempt)
        if full_height() != h:
            run.doc["cases"] = [c for c in run.doc["cases"] if c["n"] != 8]
            continue
        run.check("8.s", f"cash C2' with expiry = HEIGHT ({HN}) (rerun)", t8s, "ACCEPT", attempt=attempt)
        if full_height() == h:
            break
        run.doc["cases"] = [c for c in run.doc["cases"] if c["n"] not in (8, "8.s")]
    run.save()


def stage_7a_pos():
    """Row 10b (added after row 10's detail named only input #0, the look-alike, which fails on its own): a keyless
    fund box at INPUTS(0), the real bank at INPUTS(1), honest deposit deltas; the node's text must name input #1.
    Sibling 10b.s: the same deposit with the bank at INPUTS(0)."""
    import urllib.request
    run = Run("7a-bank", HERE, "results-7a.json")
    run.doc = json.loads(run.path.read_text())
    k = keys()
    t = (HERE / "Bank.tree").read_text().strip()
    req = urllib.request.Request(A + "/blockchain/box/unspent/byErgoTree?limit=5", data=json.dumps(t).encode(),
                                 headers={"Content-Type": "application/json"})
    nft = [c for c in run.doc["trees"] if c["name"] == "Bank"]
    box = [b for b in json.load(urllib.request.urlopen(req)) if b["boxId"] == run.doc["bank_box"]][0]
    if bk.avl("7a.log", 8, [])["digestBefore"] != box["additionalRegisters"]["R4"][2:68]:
        raise SystemExit("STOP: helper digest != bank R4")
    r5 = box["additionalRegisters"]["R5"]
    v = 0
    for i, b in enumerate(bytes.fromhex(r5[2:])):
        v |= (b & 0x7F) << (7 * i)
    total = (v >> 1) ^ -(v & 1)
    K2 = k["K2"]
    f1, f2 = fund([ERG // 2, ERG // 2])
    h = full_height()
    old = int(bk.avl("7a.log", 8, [f"lookup:{K2['key']}"])["results"][0].split(":")[1], 16)
    r = bk.avl("7a.log", 8, [f"update:{K2['key']}:{long8(old + ERG // 2)}"])
    ext = {"1": coll_bytes(r["proof"]), "2": coll_bytes(K2["key"]), "3": long_c(old + ERG // 2), "5": byte_c(2),
           "4": coll_bytes(bk.avl("7a.log", 8, [f"lookup:{K2['key']}"])["proof"])}
    succ = out(box["value"] + ERG // 2, t, h, box["assets"],
               {"R4": bk.avl_tree_c(r["digest"], 3, 8), "R5": long_c(total + ERG // 2)})
    stranger = out(f2["value"], NOBODY_TREE, h)
    run.check("10b", "a keyless box at INPUTS(0), the bank at INPUTS(1), honest deltas", {
        "inputs": [inp(f2["boxId"]), inp(box["boxId"], ext), inp(f1["boxId"])], "dataInputs": [],
        "outputs": [succ, stranger]}, "REFUSE", sibling="10b.s")
    run.check("10b.s", "the same deposit with the bank at INPUTS(0)", {
        "inputs": [inp(box["boxId"], ext), inp(f1["boxId"]), inp(f2["boxId"])], "dataInputs": [],
        "outputs": [succ, stranger]}, "ACCEPT")


def stage_7b_contention():
    """Rerun of rows 13/14 with diagnostics (row 14 of the first run passed /transactions/check and POST but was
    never mined; row 13's mempool cost was missed). Rows: 6.r a fresh SIGNED cheque, cost (same instrument as 13.r);
    11.r A commits C8, C9; 13.r cash C8 by membership, cost; 14.r cash C9 chained on 13.r's unconfirmed output,
    the mempool polled for both; 14.r2 if 14.r is not mined within 3 blocks of 13.r, the same cheque resubmitted on the
    confirmed bank box."""
    import shutil, urllib.request
    run = Run("7b-cheques", HERE, "results-7b.json")
    run.doc = json.loads(run.path.read_text())
    k = keys()
    K1 = k["K1"]
    t = (HERE / "ChequeBank.tree").read_text().strip()

    def bank_box():
        req = urllib.request.Request(A + "/blockchain/box/unspent/byErgoTree?limit=5", data=json.dumps(t).encode(),
                                     headers={"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req))[0]
    st = {"box": bank_box()}
    nft = st["box"]["assets"][0]["tokenId"]
    P_tree = "0008cd" + pk_of(A, 3)
    regs = lambda acc, tot, sp, cm: {"R4": bk.avl_tree_c(acc, 3, 8), "R5": long_c(tot),
                                     "R6": bk.avl_tree_c(sp, 1, 0), "R7": bk.avl_tree_c(cm, 1, 0)}

    def dig(r, box=None):
        return (box or st["box"])["additionalRegisters"][r][2:68]

    def total(box=None):
        r5 = (box or st["box"])["additionalRegisters"]["R5"]
        v = 0
        for i, b in enumerate(bytes.fromhex(r5[2:])):
            v |= (b & 0x7F) << (7 * i)
        return (v >> 1) ^ -(v & 1)

    def sync(suffix=""):
        for lg, vl, r in (("7b-acc.log", 8, "R4"), ("7b-spent.log", 0, "R6"), ("7b-comm.log", 0, "R7")):
            if bk.avl(lg + suffix, vl, [])["digestBefore"] != dig(r):
                raise SystemExit(f"STOP: helper {lg}{suffix} != bank {r}")
    sync()
    amt = ERG // 100
    H = full_height() + 500

    def cheque():
        return (bytes.fromhex(nft) + bytes.fromhex(K1["key"]) + bk.blake(bytes.fromhex(P_tree)) +
                amt.to_bytes(8, "big") + H.to_bytes(8, "big") + os.urandom(8)).hex()

    def cash(body, action, suffix="", box=None):
        box = box or st["box"]
        h = full_height()
        cid = bk.blake(bytes.fromhex(body)).hex()
        b0 = int(bk.avl("7b-acc.log" + suffix, 8, [f"lookup:{K1['key']}"])["results"][0].split(":")[1], 16)
        ra = bk.avl("7b-acc.log" + suffix, 8, [f"update:{K1['key']}:{long8(b0 - amt)}"])
        rs = bk.avl("7b-spent.log" + suffix, 0, [f"insert:{cid}:"])
        ext = {"5": byte_c(action), "2": coll_bytes(K1["key"]), "3": long_c(b0 - amt), "1": coll_bytes(ra["proof"]),
               "4": coll_bytes(bk.avl("7b-acc.log" + suffix, 8, [f"lookup:{K1['key']}"])["proof"]),
               "6": ge_c(K1["pk"]), "8": coll_bytes(body), "15": coll_bytes(rs["proof"])}
        if action == 4:
            R, sg = bk.schnorr_sign(int(K1["secret"], 16), bk.blake(bytes.fromhex(body)))
            ext["13"], ext["14"] = ge_c(R), coll_bytes(sg)
        else:
            ext["16"] = coll_bytes(bk.avl("7b-comm.log", 0, [f"lookup:{cid}"])["proof"])
        outs = [out(box["value"] - amt, t, h, box["assets"], regs(ra["digest"], total(box) - amt, rs["digest"],
                                                                     dig("R7", box))), out(amt, P_tree, h)]
        ops = ([f"update:{K1['key']}:{long8(b0 - amt)}"], [f"insert:{cid}:"])
        return {"inputs": [inp(box["boxId"], ext)], "dataInputs": [], "outputs": outs}, ops

    def commit_ops(ops, suffix=""):
        bk.avl("7b-acc.log" + suffix, 8, ops[0], commit=True)
        bk.avl("7b-spent.log" + suffix, 0, ops[1], commit=True)

    # 6.r: a fresh signed cheque, cost
    tx, ops = cash(cheque(), 4)
    m = run.check("6.r", "cash a fresh signed cheque, honest (cost, same instrument as 13.r)", tx, "ACCEPT",
                  submit=True, cost=True)
    commit_ops(ops)
    st["box"] = at(m, t)[0]
    sync()
    # 11.r: commit C8, C9
    C8, C9 = cheque(), cheque()
    ids = [bk.blake(bytes.fromhex(c)).hex() for c in (C8, C9)]
    h = full_height()
    r = bk.avl("7b-comm.log", 0, [f"insert:{i}:" for i in ids])
    ext = {"5": byte_c(6), "2": coll_bytes(K1["key"]), "6": ge_c(K1["pk"]), "17": bk.keys_coll([C8, C9]),
           "1": coll_bytes(r["proof"])}
    outs = [out(st["box"]["value"], t, h, st["box"]["assets"], regs(dig("R4"), total(), dig("R6"), r["digest"]))]
    m = run.key_spend("11.r", "A (K1) commits C8 and C9", A, [st["box"]["boxId"]], [], outs, "ACCEPT", submit=True,
                      cost=True, ext={st["box"]["boxId"]: ext}, secrets=dlog(K1))
    bk.avl("7b-comm.log", 0, [f"insert:{i}:" for i in ids], commit=True)
    st["box"] = at(m, t)[0]
    sync()
    # 13.r and 14.r, back to back
    for lg in ("7b-acc.log", "7b-spent.log"):
        shutil.copy(STATE / lg, STATE / (lg + ".session"))
    tx13, ops13 = cash(C8, 5)
    c13, o13 = call(A, "/transactions/check", tx13)
    tid13 = must(A, "/transactions", tx13)
    cost13, ins13 = run.mempool_cost(tid13)
    e13 = must(A, f"/transactions/unconfirmed/byTransactionId/{tid13}")
    bank13 = e13["outputs"][0]
    commit_ops(ops13, ".session")
    tx14, ops14 = cash(C9, 5, ".session", box=bank13)
    c14, o14 = call(A, "/transactions/check", tx14)
    p14 = call(A, "/transactions", tx14) if c14 == 200 else (None, None)
    tid14 = p14[1] if p14[0] == 200 else None
    polls = []
    for _ in range(15):
        polls.append({"13": call(A, f"/transactions/unconfirmed/byTransactionId/{tid13}")[0],
                      "14": call(A, f"/transactions/unconfirmed/byTransactionId/{tid14}")[0] if tid14 else None})
        time.sleep(0.2)
    m13 = wait_tx_outputs(A, tid13)
    run.record("13.r", "cash C8 by membership, honest", "ACCEPT", classify(c13, o13), "", cost=cost13,
               instrument=ins13, tx_id=tid13, heights={"included": m13.get("inclusionHeight")})
    commit_ops(ops13)
    h13 = m13.get("inclusionHeight")
    mined14 = None
    if tid14:
        for _ in range(60):
            cm, mt = call(A, f"/blockchain/transaction/byId/{tid14}")
            if cm == 200:
                mined14 = mt
                break
            if full_height() >= h13 + 3:
                break
            time.sleep(2)
    run.record("14.r", "cash C9 chained on 13.r's unconfirmed output, submitted back to back", "ACCEPT",
               "ACCEPT" if mined14 else ("NOT-MINED" if tid14 else classify(c14, o14)), "node",
               tx_id=tid14, detail=f"check {c14} {str(o14)[:200]}; post {p14[0]} {str(p14[1])[:200]}",
               heights={"13_included": h13, "14_included": mined14.get("inclusionHeight") if mined14 else None,
                        "mempool_polls": polls})
    if mined14:
        commit_ops(ops14)
        st["box"] = at(mined14, t)[0]
    else:
        st["box"] = bank_box()
        sync()
        tx14b, ops14b = cash(C9, 5)
        m = run.check("14.r2", "C9 resubmitted on the confirmed bank box after 14.r was not mined", tx14b, "ACCEPT",
                      submit=True, cost=True)
        commit_ops(ops14b)
        st["box"] = at(m, t)[0]
    sync()
    costs = {c["n"]: c["cost"] for c in run.doc["cases"]}
    run.doc["schnorr_minus_contains"] = {"rows": ["6.r", "13.r"], "instrument": "mempool",
                                         "value": None if None in (costs.get("6.r"), costs.get("13.r"))
                                         else costs["6.r"] - costs["13.r"]}
    run.save()
    print("6.r - 13.r =", run.doc["schnorr_minus_contains"])


def stage_7c_rerun():
    """Rerun of 7c rows 4 and 4b (MALFORMED in the first run: the wallet's text was "Malformed request: null" while the
    node's own check of the same transaction was EVAL-ERROR, as pre-registered; common.py now takes the node's class
    when the wallet's text is unrecognised) and of row 5x, whose wallet-signed transaction the first run recorded but
    never checked. The first run's note secrets were not kept, so: deposit 6 fresh notes (secrets in
    state/7c-notes-rerun.json, not committed), pay one honestly (3.r), then 4.r, 4b.r (3.r's image, a proof against
    the pre-3.r R7 digest), 4.s.r, 5x.r (the signed transaction checked by the node)."""
    import urllib.request
    run = Run("7c-ring", HERE, "results-7c.json")
    run.doc = json.loads(run.path.read_text())
    run.bug("4/4b", "MALFORMED: the wallet's sign error was 'Malformed request: null', which matches neither wallet "
                    "refusal text; the node's check of the unsigned transaction was EVAL-ERROR",
            "key_spend takes the node's EVAL-ERROR when the wallet text is unrecognised; rows rerun as 4.r, 4b.r")
    run.bug("5x", "the wallet SIGNED the mismatched-image payment (200) and the first run did not check it",
            "5x.r checks the signed transaction")
    DENOM = 10_000_000
    H = run.doc["H"]["point"]
    t = (HERE / "RingBank.tree").read_text().strip()
    req = urllib.request.Request(A + "/blockchain/box/unspent/byErgoTree?limit=5", data=json.dumps(t).encode(),
                                 headers={"Content-Type": "application/json"})
    st = {"box": json.load(urllib.request.urlopen(req))[0]}
    e8 = bk.avl("7c-acc.log", 8, [])["digestBefore"]
    regs = lambda notes, images: {"R4": bk.avl_tree_c(e8, 3, 8), "R5": long_c(0),
                                  "R6": bk.avl_tree_c(notes, 1, 0), "R7": bk.avl_tree_c(images, 1, 0)}
    dig = lambda r: st["box"]["additionalRegisters"][r][2:68]

    def sync():
        for lg, r in (("7c-notes.log", "R6"), ("7c-images.log", "R7")):
            if bk.avl(lg, 0, [])["digestBefore"] != dig(r):
                raise SystemExit(f"STOP: helper {lg} != bank {r}")
    sync()
    G_enc = bk.enc(bk.Gpt)
    notes = []
    for _ in range(6):
        r = rnd.randbelow(bk.N - 1) + 1
        C = bk.enc(bk.mul(r))
        notes.append({"r": r, "C": C, "key": bk.blake(bytes.fromhex(C)).hex(), "I": bk.enc(bk.mul(r, bk.dec(H)))})
    (STATE / "7c-notes-rerun.json").write_text(json.dumps([dict(n, r=f"{n['r']:064x}") for n in notes]))
    f = fund([DENOM * 6])[0]
    h = full_height()
    rr = bk.avl("7c-notes.log", 0, [f"insert:{n['key']}:" for n in notes])
    tx = {"inputs": [inp(st["box"]["boxId"], {"5": byte_c(7), "18": bk.ge_coll([n["C"] for n in notes]),
                                              "1": coll_bytes(rr["proof"])}), inp(f["boxId"])], "dataInputs": [],
          "outputs": [out(st["box"]["value"] + f["value"], t, h, st["box"]["assets"], regs(rr["digest"], dig("R7")))]}
    m = run.check("0.r", "deposit 6 fresh notes (rerun setup)", tx, "ACCEPT", submit=True)
    bk.avl("7c-notes.log", 0, [f"insert:{n['key']}:" for n in notes], commit=True)
    st["box"] = at(m, t)[0]
    sync()
    P_tree = "0008cd" + pk_of(A, 3)
    ring_of = lambda payer: [payer] + [n for n in notes if n is not payer][:3]

    def unsigned(payer, I=None, images_proof=None, images_digest=None, no_insert=False):
        h = full_height()
        I = I or payer["I"]
        ring = ring_of(payer)
        rg = bk.avl("7c-notes.log", 0, [f"lookup:{n['key']}" for n in ring])
        ri = bk.avl("7c-images.log", 0, [f"insert:{bk.blake(bytes.fromhex(I)).hex()}:"])
        ext = {"5": byte_c(8), "18": bk.ge_coll([n["C"] for n in ring]), "16": coll_bytes(rg["proof"]),
               "19": ge_c(I)}
        if not no_insert:
            ext["15"] = coll_bytes(images_proof or ri["proof"])
        outs = [out(st["box"]["value"] - DENOM, t, h, st["box"]["assets"],
                    regs(dig("R6"), dig("R7") if no_insert else (images_digest or ri["digest"]))),
                out(DENOM, P_tree, h)]
        return outs, ext, ri

    def dht(payer, I=None):
        return {"dht": [{"secret": f"{payer['r']:064x}", "g": G_enc, "h": H, "u": payer["C"], "v": I or payer["I"]}]}

    p3, p4, other = notes[0], notes[1], notes[2]
    stale = bk.avl("7c-images.log", 0, [f"insert:{bk.blake(bytes.fromhex(p3['I'])).hex()}:"])
    outs, ext, ri = unsigned(p3)
    m = run.key_spend("3.r", "pay, N = 4, honest (rerun setup)", A, [st["box"]["boxId"]], [], outs, "ACCEPT",
                      submit=True, ext={st["box"]["boxId"]: ext}, secrets=dht(p3))
    bk.avl("7c-images.log", 0, [f"insert:{bk.blake(bytes.fromhex(p3['I'])).hex()}:"], commit=True)
    st["box"] = at(m, t)[0]
    sync()
    outs, ext, _ = unsigned(p4, no_insert=True)
    run.key_spend("4.r", "pay a second note with no key-image insert (no proof variable)", A, [st["box"]["boxId"]], [],
                  outs, "EVAL-ERROR", "4.s.r", ext={st["box"]["boxId"]: ext}, secrets=dht(p4))
    outs, ext, _ = unsigned(p3, images_proof=stale["proof"], images_digest=stale["digest"])
    run.key_spend("4b.r", "pay again with 3.r's key image, insert proof against the pre-3.r R7 digest", A,
                  [st["box"]["boxId"]], [], outs, "EVAL-ERROR", "4.s.r", ext={st["box"]["boxId"]: ext},
                  secrets=dht(p3))
    outs, ext, _ = unsigned(p4)
    run.key_spend("4.s.r", "the same payment as 4.r with the insert, checked", A, [st["box"]["boxId"]], [], outs,
                  "ACCEPT", ext={st["box"]["boxId"]: ext}, secrets=dht(p4))
    outs, ext, _ = unsigned(p4, I=other["I"])
    run.key_spend("5x.r", "key image from another note's r while proving with this one's (signed by the wallet, then "
                  "checked)", A, [st["box"]["boxId"]], [], outs, "REFUSE", "4.s.r", ext={st["box"]["boxId"]: ext},
                  secrets=dht(p4, other["I"]))
    # ---- the ring's real limit: atLeast takes at most 255 children (MaxChildrenCountForAtLeastOp). Enough
    # commitments for a 256-member ring (their secrets are not needed: only the payer proves), then N = 255, 256.
    filler = [bk.enc(bk.mul(rnd.randbelow(bk.N - 1) + 1)) for _ in range(190)]
    for i in range(0, 190, 95):
        batch = filler[i:i + 95]
        keys_ = [bk.blake(bytes.fromhex(c)).hex() for c in batch]
        f = fund([DENOM * len(batch)])[0]
        h = full_height()
        rr = bk.avl("7c-notes.log", 0, [f"insert:{k}:" for k in keys_])
        tx = {"inputs": [inp(st["box"]["boxId"], {"5": byte_c(7), "18": bk.ge_coll(batch),
                                                  "1": coll_bytes(rr["proof"])}), inp(f["boxId"])],
              "dataInputs": [], "outputs": [out(st["box"]["value"] + f["value"], t, h, st["box"]["assets"],
                                                regs(rr["digest"], dig("R7")))]}
        m = run.check(f"0.f{i // 95}", f"deposit {len(batch)} filler notes (for N = 255, 256)", tx, "ACCEPT",
                      submit=True)
        bk.avl("7c-notes.log", 0, [f"insert:{k}:" for k in keys_], commit=True)
        st["box"] = at(m, t)[0]
        sync()
    first = [l.split(":")[1] for l in (STATE / "7c-notes.log").read_text().split()]
    pool_C = {bk.blake(bytes.fromhex(c)).hex(): c for c in filler + [n["C"] for n in notes]}
    for n_ring, payer in ((255, notes[3]), (256, notes[4])):
        ring = [payer["C"]] + [c for c in filler + [x["C"] for x in notes] if c != payer["C"]][:n_ring - 1]
        h = full_height()
        keys_ = [bk.blake(bytes.fromhex(c)).hex() for c in ring]
        rg = bk.avl("7c-notes.log", 0, [f"lookup:{k}" for k in keys_])
        ri = bk.avl("7c-images.log", 0, [f"insert:{bk.blake(bytes.fromhex(payer['I'])).hex()}:"])
        ext = {"5": byte_c(8), "18": bk.ge_coll(ring), "16": coll_bytes(rg["proof"]), "19": ge_c(payer["I"]),
               "15": coll_bytes(ri["proof"])}
        outs = [out(st["box"]["value"] - DENOM, t, h, st["box"]["assets"], regs(dig("R6"), ri["digest"])),
                out(DENOM, P_tree, h)]
        uns = {"inputs": [{"boxId": st["box"]["boxId"], "extension": ext}], "dataInputs": [], "outputs": outs}
        code, signed = run.sign(A, uns, [st["box"]["boxId"]], (), dht(payer))
        if code != 200:
            c2, o2 = call(A, "/transactions/check", {"inputs": [inp(st["box"]["boxId"], ext)], "dataInputs": [],
                                                     "outputs": outs})
            run.record(f"6.{n_ring}", f"pay, N = {n_ring} (measurement)", None, "SIGN-FAILED", "measured",
                       detail=f"wallet: {str(signed)[:300]} | unsigned check: {classify(c2, o2)} {str(o2)[:300]}",
                       ring=n_ring)
            continue
        le = local_eval(signed, [must(A, f"/utxo/byId/{st['box']['boxId']}")], h + 1)
        c2, o2 = call(A, "/transactions/check", signed)
        cost, ins, mined = None, None, None
        if c2 == 200:
            tid = must(A, "/transactions", signed)
            cost, ins = run.mempool_cost(tid)
            mined = wait_tx_outputs(A, tid)
            bk.avl("7c-images.log", 0, [f"insert:{bk.blake(bytes.fromhex(payer['I'])).hex()}:"], commit=True)
            st["box"] = at(mined, t)[0]
            sync()
        run.record(f"6.{n_ring}", f"pay, N = {n_ring} (measurement)", None, classify(c2, o2), "measured",
                   detail=str(o2)[:400] if c2 != 200 else "", cost=cost, instrument=ins, ring=n_ring, local_eval=le,
                   proof_bytes=len(signed["inputs"][0]["spendingProof"]["proofBytes"]) // 2,
                   tx_bytes=le.get("tx_bytes"), mined=bool(mined))
    run.save()


def stage_7c_limit():
    """N = 255 and N = 256, after 7c-rerun measured N = 196 under those labels (harness bug). 270 fresh commitments,
    points saved (state/7c-limit-points.json), two payer notes with secrets; the ring size is asserted."""
    import urllib.request
    run = Run("7c-ring", HERE, "results-7c.json")
    run.doc = json.loads(run.path.read_text())
    DENOM = 10_000_000
    H = run.doc["H"]["point"]
    t = (HERE / "RingBank.tree").read_text().strip()
    req = urllib.request.Request(A + "/blockchain/box/unspent/byErgoTree?limit=5", data=json.dumps(t).encode(),
                                 headers={"Content-Type": "application/json"})
    st = {"box": json.load(urllib.request.urlopen(req))[0]}
    e8 = bk.avl("7c-acc.log", 8, [])["digestBefore"]
    regs = lambda notes, images: {"R4": bk.avl_tree_c(e8, 3, 8), "R5": long_c(0),
                                  "R6": bk.avl_tree_c(notes, 1, 0), "R7": bk.avl_tree_c(images, 1, 0)}
    dig = lambda r: st["box"]["additionalRegisters"][r][2:68]

    def sync():
        for lg, r in (("7c-notes.log", "R6"), ("7c-images.log", "R7")):
            if bk.avl(lg, 0, [])["digestBefore"] != dig(r):
                raise SystemExit(f"STOP: helper {lg} != bank {r}")
    sync()
    G_enc = bk.enc(bk.Gpt)
    payers = []
    for _ in range(2):
        r = rnd.randbelow(bk.N - 1) + 1
        payers.append({"r": r, "C": bk.enc(bk.mul(r)), "I": bk.enc(bk.mul(r, bk.dec(H)))})
    points = [p["C"] for p in payers] + [bk.enc(bk.mul(rnd.randbelow(bk.N - 1) + 1)) for _ in range(268)]
    (STATE / "7c-limit-points.json").write_text(json.dumps(points))
    for i in range(0, len(points), 90):
        batch = points[i:i + 90]
        keys_ = [bk.blake(bytes.fromhex(c)).hex() for c in batch]
        f = fund([DENOM * len(batch)])[0]
        h = full_height()
        rr = bk.avl("7c-notes.log", 0, [f"insert:{k}:" for k in keys_])
        tx = {"inputs": [inp(st["box"]["boxId"], {"5": byte_c(7), "18": bk.ge_coll(batch),
                                                  "1": coll_bytes(rr["proof"])}), inp(f["boxId"])],
              "dataInputs": [], "outputs": [out(st["box"]["value"] + f["value"], t, h, st["box"]["assets"],
                                                regs(rr["digest"], dig("R7")))]}
        m = run.check(f"0.g{i // 90}", f"deposit {len(batch)} saved commitments (for N = 255, 256)", tx, "ACCEPT",
                      submit=True)
        bk.avl("7c-notes.log", 0, [f"insert:{k}:" for k in keys_], commit=True)
        st["box"] = at(m, t)[0]
        sync()
    P_tree = "0008cd" + pk_of(A, 3)
    for n_ring, payer in ((255, payers[0]), (256, payers[1])):
        ring = [payer["C"]] + [c for c in points if c != payer["C"]][:n_ring - 1]
        assert len(ring) == n_ring, (len(ring), n_ring)
        h = full_height()
        keys_ = [bk.blake(bytes.fromhex(c)).hex() for c in ring]
        rg = bk.avl("7c-notes.log", 0, [f"lookup:{k}" for k in keys_])
        ri = bk.avl("7c-images.log", 0, [f"insert:{bk.blake(bytes.fromhex(payer['I'])).hex()}:"])
        ext = {"5": byte_c(8), "18": bk.ge_coll(ring), "16": coll_bytes(rg["proof"]), "19": ge_c(payer["I"]),
               "15": coll_bytes(ri["proof"])}
        outs = [out(st["box"]["value"] - DENOM, t, h, st["box"]["assets"], regs(dig("R6"), ri["digest"])),
                out(DENOM, P_tree, h)]
        uns = {"inputs": [{"boxId": st["box"]["boxId"], "extension": ext}], "dataInputs": [], "outputs": outs}
        dht = {"dht": [{"secret": f"{payer['r']:064x}", "g": G_enc, "h": H, "u": payer["C"], "v": payer["I"]}]}
        code, signed = run.sign(A, uns, [st["box"]["boxId"]], (), dht)
        if code != 200:
            c2, o2 = call(A, "/transactions/check", {"inputs": [inp(st["box"]["boxId"], ext)], "dataInputs": [],
                                                     "outputs": outs})
            run.record(f"6.{n_ring}", f"pay, N = {n_ring} (measurement)", None, "SIGN-FAILED", "measured",
                       detail=f"wallet: {str(signed)[:300]} | unsigned check: {classify(c2, o2)} {str(o2)[:300]}",
                       ring=n_ring)
            continue
        le = local_eval(signed, [must(A, f"/utxo/byId/{st['box']['boxId']}")], h + 1)
        c2, o2 = call(A, "/transactions/check", signed)
        cost, ins, mined = None, None, None
        if c2 == 200:
            tid = must(A, "/transactions", signed)
            cost, ins = run.mempool_cost(tid)
            mined = wait_tx_outputs(A, tid)
            bk.avl("7c-images.log", 0, [f"insert:{bk.blake(bytes.fromhex(payer['I'])).hex()}:"], commit=True)
            st["box"] = at(mined, t)[0]
            sync()
        run.record(f"6.{n_ring}", f"pay, N = {n_ring} (measurement)", None, classify(c2, o2), "measured",
                   detail=str(o2)[:400] if c2 != 200 else "", cost=cost, instrument=ins, ring=n_ring, local_eval=le,
                   proof_bytes=len(signed["inputs"][0]["spendingProof"]["proofBytes"]) // 2,
                   tx_bytes=le.get("tx_bytes"), mined=bool(mined))
    run.save()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["control", "7a", "7a-pos", "7b", "7b-expiry", "7b-contention", "7c", "7c-rerun", "7c-limit"])
    a = ap.parse_args()
    {"control": stage_control, "7a": stage_7a, "7a-pos": stage_7a_pos, "7b": stage_7b, "7b-expiry": stage_7b_expiry, "7b-contention": stage_7b_contention, "7c": stage_7c, "7c-rerun": stage_7c_rerun, "7c-limit": stage_7c_limit}[a.stage]()


if __name__ == "__main__":
    main()
