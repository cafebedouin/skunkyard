"""U1c line l: the whole unspent set, walked by inclusion height through the explorer.

`/boxes/unspent/stream?minHeight=a&maxHeight=b` returns every box still unspent that was included in blocks a..b
(the mirror refuses more than 1,536 blocks per request). Walking 0..H in such ranges lists the unspent set without
a node: about 1,232 requests at H = 1.89M. The set moves while it is walked (a range read early can lose boxes spent
later); each range records when it was read.

Raw responses are kept gzipped under census/raw/u1c/ (git-ignored), one file per range; `compact` reduces each box
to what the census needs (template hash, value, heights, size in bytes, tokens, registers) in census/out/.
"""
import concurrent.futures as cf, gzip, json, os, sys, threading, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explorer as X  # noqa: E402
import trees as T  # noqa: E402

STEP = 1536
RAW = os.path.join(X.RAW, "u1c")
_lock = threading.Lock()
_last = [0.0]


def _range_path(lo, hi):
    return os.path.join(RAW, f"unspent-{lo:07d}-{hi:07d}.json.gz")


def fetch_range(lo, hi):
    p = _range_path(lo, hi)
    if os.path.exists(p):
        return p
    try:
        body = _fetch(lo, hi, 5)
    except Exception:  # noqa: BLE001  (the mirror times out on a dense range: read it in halves)
        mid = (lo + hi) // 2
        print(f"{lo}-{hi}: split at {mid}", file=sys.stderr, flush=True)
        body = _fetch_split(lo, mid) + b"\n" + _fetch_split(mid + 1, hi)
    os.makedirs(RAW, exist_ok=True)
    url = f"{X.EXPLORER}/boxes/unspent/stream?minHeight={lo}&maxHeight={hi}"
    with gzip.open(p + ".tmp", "wb") as f:
        f.write(json.dumps({"url": url, "fetchedAt": time.time()}).encode() + b"\n" + body)
    os.replace(p + ".tmp", p)
    return p


def _fetch_split(lo, hi, depth=0):
    try:
        return _fetch(lo, hi, 5)
    except Exception:  # noqa: BLE001
        if depth >= 4 or hi <= lo:
            raise
        mid = (lo + hi) // 2
        return _fetch_split(lo, mid, depth + 1) + b"\n" + _fetch_split(mid + 1, hi, depth + 1)


def _fetch(lo, hi, tries):
    url = f"{X.EXPLORER}/boxes/unspent/stream?minHeight={lo}&maxHeight={hi}"
    for attempt in range(tries):
        with _lock:
            wait = X.MIN_INTERVAL - (time.time() - _last[0])
            if wait > 0:
                time.sleep(wait)
            _last[0] = time.time()
        try:
            with urllib.request.urlopen(url, timeout=600) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            print(f"{lo}-{hi}: {e}; retry", file=sys.stderr, flush=True)
            time.sleep(min(60, 2 ** (attempt + 1)))


def read_range(p):
    with gzip.open(p, "rb") as f:
        head, body = f.read().split(b"\n", 1)
    return json.loads(head), X._parse(body.decode(), "/stream")


def walk(tip, workers=4, log=print):
    ranges = [(lo, min(lo + STEP - 1, tip)) for lo in range(0, tip + 1, STEP)]
    done = 0
    with cf.ThreadPoolExecutor(workers) as ex:
        for _ in ex.map(lambda r: fetch_range(*r), ranges):
            done += 1
            if done % 50 == 0:
                log(f"walk: {done}/{len(ranges)} ranges")
    return ranges


# ---- box size: the bytes the storage fee is charged on (ErgoBox serialization) -------------------------------

def _vlq(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def box_size(box):
    """len(ErgoBox.bytes): value, tree, creation height, tokens, registers R4.., transaction id, output index.
    Same layout as ergo's ErgoBoxCandidate serializer followed by txId and index; register values are the
    explorer's serializedValue verbatim."""
    n = len(_vlq(box["value"])) + len(box["ergoTree"]) // 2 + len(_vlq(box["creationHeight"]))
    toks = box.get("assets") or []
    n += 1 + sum(32 + len(_vlq(a["amount"])) for a in toks)
    regs = box.get("additionalRegisters") or {}
    n += 1 + sum(len(v["serializedValue"] if isinstance(v, dict) else v) // 2 for v in regs.values())
    n += 32 + len(_vlq(box["index"]))
    return n


def compact(box):
    tree = box["ergoTree"]
    if tree.startswith("0008cd"):
        th = "p2pk"
    else:
        th = box.get("ergoTreeTemplateHash")
        if not th:
            try:
                th = T.template_hash(tree)
            except (ValueError, IndexError):
                th = "unparsed:" + tree[:16]
    regs = box.get("additionalRegisters") or {}
    return {"id": box["boxId"], "tx": box["transactionId"], "i": box["index"], "v": box["value"],
            "ch": box["creationHeight"], "sh": box["settlementHeight"], "th": th, "size": box_size(box),
            "tok": [[a["tokenId"], a["amount"]] for a in box.get("assets") or []],
            "regs": sorted(regs)}
