"""Box chains for U1d: every box that ever held a singleton NFT, in order, and the check that the chain is unbroken.

`/boxes/byTokenId/{nft}` pages ascending by global index (offset 0 is the first box that held the token; checked on
the SigmaUSD bank NFT, 2026-10-10: offset 0 is the minting box at 452,140). Every page but the last two is cached
(gzipped, `CENSUS_GZIP=1`); the tail is reread because its boxes may since have been spent. The compacted chain is
kept at census/out/u1d/chain-<nft>.json.gz (git-ignored).

A state is one box: it holds from the block that included it until the block of the transaction that spent it,
which (on an unbroken chain) is the block that included the next box.
"""
import gzip, json, os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CENSUS_GZIP", "1")
import explorer as X  # noqa: E402
import trees as T  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "u1d")
PAGE = 100


def _regs(b):
    return {k: v.get("renderedValue") for k, v in (b.get("additionalRegisters") or {}).items()}


def compact(b, nft):
    return {"box": b["boxId"], "tx": b["transactionId"], "spent": b.get("spentTransactionId"),
            "h": b["settlementHeight"], "ch": b["creationHeight"], "gix": b["globalIndex"], "idx": b["index"],
            "value": b["value"], "tpl": T.template_hash(b["ergoTree"])[:12],
            "assets": [[a["tokenId"], a["amount"]] for a in b["assets"]], "regs": _regs(b),
            "hasNft": any(a["tokenId"] == nft for a in b["assets"]), "tree": b["ergoTree"]}


def offset_at(base, total, height):
    """Page-aligned offset of the first page whose boxes reach `height` (pages ascend by height)."""
    lo, hi = 0, max(0, (total - 1) // PAGE)
    while lo < hi:
        m = (lo + hi + 1) // 2
        b = X.get(f"{base}offset={m * PAGE}&limit=1", cache=False)["items"][0]
        if b["settlementHeight"] < height:
            lo = m
        else:
            hi = m - 1
    return lo * PAGE


def fetch(nft, threads=4, keep_tree=False, from_height=None, template=None, address=None):
    """Every box that ever held nft (or from the page reaching from_height), compacted, sorted by (height, global
    index). Cached on disk. With template= (a template hash), every box ever of that template instead."""
    os.makedirs(OUT, exist_ok=True)
    if address:
        cp = os.path.join(OUT, f"address-{address[-16:]}{'' if from_height is None else f'-from{from_height}'}.json.gz")
        base = f"/boxes/byAddress/{address}?"
    elif template:
        nft = template
        cp = os.path.join(OUT, f"template-{template[:16]}.json.gz")
        base = f"/boxes/byErgoTreeTemplateHash/{template}?"
    else:
        cp = os.path.join(OUT, f"chain-{nft[:16]}{'' if from_height is None else f'-from{from_height}'}.json.gz")
        base = f"/boxes/byTokenId/{nft}?"
    total = X.get(f"{base}offset=0&limit=1", cache=False)["total"]
    if os.path.exists(cp):
        with gzip.open(cp, "rt") as f:
            have = json.load(f)
        if have["total"] == total and all(r["spent"] for r in have["rows"][:-1]):
            return have["rows"]
    start = 0 if from_height is None else offset_at(base, total, from_height)
    offs = list(range(start, total, PAGE))
    tail = set(offs[-2:])

    def page(o):
        return X.get(f"{base}offset={o}&limit={PAGE}", cache=o not in tail)["items"]

    with ThreadPoolExecutor(threads) as ex:
        pages = list(ex.map(page, offs))
    rows, seen = [], set()
    for p in pages:
        for b in p:
            if b["boxId"] in seen:
                continue
            seen.add(b["boxId"])
            r = compact(b, nft)
            if not keep_tree and not template and not address:
                r["tree"] = r["tree"] if len(rows) == 0 or r["tpl"] != rows[-1]["tpl"] else None
            rows.append(r)
    rows.sort(key=lambda r: (r["h"], r["gix"]))
    with gzip.open(cp + ".tmp", "wt") as f:
        json.dump({"nft": nft, "total": total, "rows": rows}, f)
    os.replace(cp + ".tmp", cp)
    return rows


def check(rows):
    """Is each NFT-holding box spent by the transaction that creates the next? Returns (breaks, report)."""
    held = [r for r in rows if r["hasNft"]]
    breaks = []
    for a, b in zip(held, held[1:]):
        if a["spent"] != b["tx"]:
            breaks.append({"box": a["box"], "h": a["h"], "spent": a["spent"], "nextTx": b["tx"], "nextH": b["h"]})
    last = held[-1] if held else None
    return breaks, {"boxes": len(held), "first": held[0]["h"] if held else None, "last": last and last["h"],
                    "lastUnspent": bool(last and not last["spent"]), "breaks": len(breaks)}


def states(rows):
    """[(from_height, to_height_exclusive_or_None, row)]: the state each NFT box held. to = the next box's height."""
    held = [r for r in rows if r["hasNft"]]
    out = []
    for i, r in enumerate(held):
        nxt = held[i + 1]["h"] if i + 1 < len(held) else None
        out.append((r["h"], nxt, r))
    return out


class Series:
    """State at any height: the last box included at or before h (several boxes in one block: the last one)."""

    def __init__(self, rows):
        import bisect
        self._b = bisect
        self.rows = [r for r in rows if r["hasNft"]]
        self.hs = [r["h"] for r in self.rows]

    def at(self, h):
        """State at the end of block h."""
        i = self._b.bisect_right(self.hs, h) - 1
        return self.rows[i] if i >= 0 else None

    def before(self, h):
        """State at the start of block h (end of h - 1)."""
        return self.at(h - 1)

    def changes(self, lo, hi):
        return {h for h in self.hs if lo <= h <= hi}
