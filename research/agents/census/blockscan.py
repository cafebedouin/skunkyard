"""Every block of a window, in full, for U1b lines (f) and (k): headers from the block stream, then /blocks/{id}
for each (inputs with their spending proofs and addresses, outputs with their trees). Fetched from a few threads
under the explorer client's global rate limit, and cached like every other response (census/raw/).

usage: blockscan.py LO HI [WORKERS]   (prefetch only; prints progress)
"""
import concurrent.futures as cf, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explorer as X  # noqa: E402


def headers(lo, hi, workers=4):
    """{height: block summary} for lo..hi from /blocks/byGlobalIndex/stream (500 a request)."""
    starts = list(range(lo - 1, hi, 500))

    def one(g):
        return X.get(f"/blocks/byGlobalIndex/stream?minGix={g}&limit={min(500, hi - g)}")

    out = {}
    with cf.ThreadPoolExecutor(workers) as ex:
        for part in ex.map(one, starts):
            for b in part:
                if lo <= b["height"] <= hi:
                    out[b["height"]] = b
    missing = [h for h in range(lo, hi + 1) if h not in out]
    assert not missing, f"block stream missing {len(missing)} heights, first {missing[:5]}"
    return out


def full_blocks(hdr, workers=4, progress=None):
    """Yields (height, /blocks/{id} response) in height order."""
    hs = sorted(hdr)

    def one(h):
        return h, X.get(f"/blocks/{hdr[h]['id']}")

    with cf.ThreadPoolExecutor(workers) as ex:
        for k, (h, b) in enumerate(ex.map(one, hs)):
            if progress and k % 500 == 0:
                progress(f"block {h} ({k}/{len(hs)}) {X.stats}")
            yield h, b


if __name__ == "__main__":
    lo, hi = int(sys.argv[1]), int(sys.argv[2])
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    X.MIN_INTERVAL = 0.12
    hdr = headers(lo, hi, w)
    print("headers", len(hdr), flush=True)
    n = 0
    for h, b in full_blocks(hdr, w, lambda m: print(m, flush=True)):
        n += 1
    print("done", n, X.stats, flush=True)
