"""Shared harness for the policy-layer experiments (skunks/policy/<n>-*/devnet-test.py).

Builds on skunks/keepalive/devnet-test.py (call, must, height, wait_height, wait_tx_outputs, FEE, FEE_TREE, G) and
adds what the plan (prompts/policy-experiments-plan.md §3) asks of every experiment:

  - two wallets: node A (mining; the owner, the oracle, account key K1) and node B (non-mining; only keys that must
    NOT open the owner path: heir, recovery, second owner, K2);
  - verdict classes: ACCEPT (HTTP 200 from /transactions/check), EVAL-ERROR (the node's text names an exception;
    tested first, valid only where a case pre-registers it), REFUSE ("should pass verification"; for a key path the
    wallet's "reduced to false" or its missing-secret error), MALFORMED (anything else: a harness bug);
  - every REFUSE names its ACCEPT sibling; every row records heights and the source of the verdict;
  - cost from the mempool entry (GET /transactions/unconfirmed/byTransactionId/{id}) right after POST /transactions.
"""
import importlib.util, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

POLICY = Path(__file__).parent
ROOT = POLICY.parent
_spec = importlib.util.spec_from_file_location("kt", ROOT / "keepalive" / "devnet-test.py")
kt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kt)
call, must, height, wait_height, wait_tx_outputs = kt.call, kt.must, kt.height, kt.wait_height, kt.wait_tx_outputs
FEE, FEE_TREE, G = kt.FEE, kt.FEE_TREE, kt.G
NOBODY_TREE = "0008cd" + G

A = os.environ.get("POLICY_A", "http://127.0.0.1:9181")
B = os.environ.get("POLICY_B", "http://127.0.0.1:9182")
ONESHOT = ROOT / "oneshot"
FALSE, TRUE = "0100", "0101"
STORAGE_FEE_FACTOR = 1_250_000

EXC = re.compile(r"(Exception|IndexOutOfBounds|NoSuchElement|None\.get|ArithmeticException|Failure\()")


def vlq(n):
    v = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        v.append(b | (0x80 if n else 0))
        if not n:
            return v.hex()


def zz32(n):
    return vlq((n << 1) ^ (n >> 31))


def zz64(n):
    return vlq((n << 1) ^ (n >> 63))


def coll_bytes(h):
    """Coll[Byte] constant (type 0x0e) for a hex string."""
    return "0e" + vlq(len(h) // 2) + h


def int_c(n):
    return "04" + zz32(n)


def long_c(n):
    return "05" + zz64(n)


def ge_c(pk):
    return "07" + pk


def sigprop_c(pk):
    return "08cd" + pk


def compile_tree(src, subs, version=1, base=None):
    for k, v in subs.items():
        src = src.replace(k, v)
    if "$" in src:
        raise SystemExit("unsubstituted constant: " + re.findall(r"\$[A-Z_]+", src)[0])
    code, out = call(base or A, "/script/p2sAddress", {"source": src, "treeVersion": version})
    if code != 200:
        raise CompileError(str(out))
    addr = out["address"]
    return must(base or A, f"/script/addressToTree/{addr}")["tree"], addr


class CompileError(Exception):
    pass


def raw(box_id, base=None):
    return must(base or A, f"/utxo/byIdBinary/{box_id}")["bytes"]


def box_bytes(box_id):
    return len(raw(box_id)) // 2


def pk_of(base, i=0):
    addrs = must(base, "/wallet/addresses")
    return must(base, f"/utils/addressToRaw/{addrs[i]}")["raw"]


def wallet_keys(base):
    return [must(base, f"/utils/addressToRaw/{a}")["raw"] for a in must(base, "/wallet/addresses")]


def full_height(base=None):
    return must(base or A, "/info")["fullHeight"] or 0


def wots(*args):
    out = subprocess.run(["npx", "tsx", "scripts/wots-cli.mts", *args], cwd=ONESHOT, capture_output=True, text=True)
    if out.returncode:
        raise SystemExit("wots-cli: " + out.stderr[-400:])
    return json.loads(out.stdout.strip().splitlines()[-1])


def wots_sign(seed, box_id, outputs):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(outputs, f)
    try:
        return wots("sign", seed, "32", "16", box_id, f.name)["signature"]
    finally:
        os.unlink(f.name)


def out(value, tree, h, assets=(), regs=None):
    return {"value": value, "ergoTree": tree, "creationHeight": h,
            "assets": [{"tokenId": t["tokenId"], "amount": t["amount"]} for t in assets],
            "additionalRegisters": regs or {}}


def inp(box_id, ext=None):
    return {"boxId": box_id, "spendingProof": {"proofBytes": "", "extension": ext or {}}}


def send(requests, base=None):
    """A wallet payment from A, mined; returns the mined transaction."""
    return wait_tx_outputs(base or A, must(base or A, "/wallet/transaction/send", {"requests": requests, "fee": FEE}))


def issue(name, amount=1, base=None):
    base = base or A
    addr = must(base, "/wallet/addresses")[0]
    tx = send([{"address": addr, "ergValue": 1_000_000, "amount": amount, "name": name, "description": name,
                "decimals": 0}], base)
    return tx["outputs"][0]["assets"][0]["tokenId"]


def at(tx, tree):
    return [o for o in tx["outputs"] if o["ergoTree"] == tree]


def classify(code, text):
    if code == 200:
        return "ACCEPT"
    t = str(text)
    if "DecodingFailure" in t or "request content was malformed" in t:
        return "MALFORMED"
    if EXC.search(t):
        return "EVAL-ERROR"
    if "should pass verification" in t:
        return "REFUSE"
    return "MALFORMED"


class Run:
    def __init__(self, experiment, here, out="results.json"):
        self.here = Path(here)
        self.path = self.here / out
        info = must(A, "/info")
        self.doc = {"experiment": experiment, "started_height": info["fullHeight"],
                    "node": {"appVersion": info["appVersion"], "parameters": info["parameters"]},
                    "wallets": {"A": wallet_keys(A), "B": wallet_keys(B)}, "trees": [], "cases": [],
                    "harness_bugs": []}

    # ---- recording
    def tree(self, name, tree_hex, address, box_id=None, version=1, extra=None):
        bb = box_bytes(box_id) if box_id else None
        row = {"name": name, "tree_bytes": len(tree_hex) // 2, "box_bytes": bb, "address": address,
               "tree_version": version, "rent_per_period_nanoerg_derived": bb * STORAGE_FEE_FACTOR if bb else None}
        if extra:
            row.update(extra)
        self.doc["trees"] = [t for t in self.doc["trees"] if t["name"] != name] + [row]
        (self.here / f"{name}.tree").write_text(tree_hex + "\n")
        self.save()
        return row

    def record(self, n, label, expect, got, source="", sibling=None, detail="", cost=None, instrument=None,
               tx_id=None, heights=None, **extra):
        row = {"n": n, "label": label, "got": got, "source": source, "sibling_n": sibling, "cost": cost,
               "cost_instrument": instrument, "tx_id": tx_id, "heights": heights,
               "detail": str(detail).replace("\n", " ")[:600]}
        if expect is not None:
            row["expect"] = expect
            row["ok"] = got == expect
        row.update(extra)
        self.doc["cases"].append(row)
        flag = "" if expect is None else ("ok" if row["ok"] else "WRONG")
        print(f"{str(n):>5} {label[:66]:<66} expect {str(expect):<10} got {got:<10} {source:<14} {flag}", flush=True)
        self.save()
        return row

    def bug(self, case, what, fix):
        self.doc["harness_bugs"].append({"case": case, "what": what, "fix": fix})
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.doc, indent=1) + "\n")

    # ---- verdicts
    def check(self, n, label, tx, expect, sibling=None, submit=False, cost=False, source=None, **extra):
        h0 = full_height()
        code, o = call(A, "/transactions/check", tx)
        h1 = full_height()
        got = classify(code, o)
        detail = o if isinstance(o, str) else ""
        tx_id, c, ins, mined = None, None, None, None
        if got == "ACCEPT" and submit:
            tx_id = must(A, "/transactions", tx)
            if cost:
                c, ins = self.mempool_cost(tx_id)
            mined = wait_tx_outputs(A, tx_id)
        src = source or ("" if got == "ACCEPT" else ("EVAL-ERROR" if got == "EVAL-ERROR" else "node-check"))
        self.record(n, label, expect, got, src, sibling, detail, c, ins, tx_id or (o if code == 200 else None),
                    {"before": h0, "after": h1}, **extra)
        return mined if submit else (got, o)

    def sign(self, base, tx, inputs, data=(), secrets=None):
        """Sign `tx` (inputs with "extension") with the wallet of `base`, plus any external secrets
        ({"dlog": [hex], "dht": [{secret, g, h, u, v}]}). Returns (code, signed or text)."""
        body = {"tx": tx, "inputsRaw": [raw(b) for b in inputs], "dataInputsRaw": [raw(d) for d in data]}
        if secrets:
            body["secrets"] = secrets
        return call(base, "/wallet/transaction/sign", body)

    def key_spend(self, n, label, base, inputs, data, outputs, expect, sibling=None, submit=False, cost=False,
                  ext=None, secrets=None, **extra):
        """A spend signed by the wallet of `base` (A or B). A sign failure is a REFUSE only with the wallet's
        "reduced to false" or its missing-secret text; anything else is MALFORMED. The unsigned form is checked
        too, so the node's own verdict is in the detail."""
        ext = ext or {}
        unsigned = {"inputs": [{"boxId": b, "extension": ext.get(b, {})} for b in inputs],
                    "dataInputs": [{"boxId": d} for d in data], "outputs": outputs}
        h0 = full_height()
        code, signed = self.sign(base, unsigned, inputs, data, secrets)
        wallet = "A" if base == A else "B"
        if code != 200:
            empty = {"inputs": [inp(b, ext.get(b)) for b in inputs], "dataInputs": unsigned["dataInputs"],
                     "outputs": outputs}
            c2, o2 = call(A, "/transactions/check", empty)
            s = str(signed)
            # the two texts preflight.json recorded on this node (6.0.7): no open path, or an open path whose
            # secret this wallet lacks (the prover's root stays an UnprovenSchnorr / UnprovenDiffieHellmanTuple)
            if "Script reduced to false" in s:
                got, src = "REFUSE", "wallet-sign"
            elif "Tree root should be real" in s:
                got, src = "REFUSE", "wallet-sign/no-secret"
            elif EXC.search(s):
                got, src = "EVAL-ERROR", "wallet-sign"
            elif classify(c2, o2) == "EVAL-ERROR":
                # the wallet's text names nothing (e.g. "Malformed request: null", an exception without a message):
                # the verdict is the node's own check of the same transaction
                got, src = "EVAL-ERROR", "node-check (wallet text unrecognised)"
            else:
                got, src = "MALFORMED", "wallet-sign"
            self.record(n, label, expect, got, src, sibling, f"wallet {wallet} sign: {s[:350]} | unsigned check: "
                        f"{classify(c2, o2)} {str(o2)[:200]}", heights={"before": h0, "after": full_height()},
                        wallet=wallet, **extra)
            return None
        return self.check(n, label, signed, expect, sibling, submit, cost, wallet=wallet, **extra)

    def mempool_cost(self, tx_id):
        for _ in range(50):
            code, o = call(A, f"/transactions/unconfirmed/byTransactionId/{tx_id}")
            if code == 200 and isinstance(o, dict) and o.get("cost") is not None:
                return o["cost"], "mempool"
            time.sleep(0.2)
        return None, "missed"


# ---- tree constants (read-only use of research/agents/census/trees.py's type parser)
_tspec = importlib.util.spec_from_file_location("census_trees", ROOT.parent / "research" / "agents" / "census" / "trees.py")
census_trees = importlib.util.module_from_spec(_tspec)
_tspec.loader.exec_module(census_trees)


def constants(tree_hex):
    """[(type, start, end, value_hex)] of a tree's segregated constants; byte offsets into the tree."""
    b = bytes.fromhex(tree_hex)
    h, i = b[0], 1
    if h & 0x08:
        _, i = census_trees._vlq(b, i)
    if not h & 0x10:
        return []
    n, i = census_trees._vlq(b, i)
    res = []
    for _ in range(n):
        s = i
        t, j = census_trees._parse_type(b, i)
        i = census_trees._skip_value(b, j, t)
        res.append((t, s, i, b[j:i].hex()))
    return res
