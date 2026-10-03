#!/usr/bin/env python3
"""Q3 recent-era sample via the public explorer: random heights in [lo, hi], the P2PK addresses that signed inputs
in those blocks, each address's lifetime transaction total, reweighted by 1/total (a block sample is length-biased
toward frequent signers). Prints aggregates only; addresses are never written (PROGRAM rule: no target lists)."""
import json, random, sys, time, urllib.request, statistics
API = "https://api.ergoplatform.com/api/v1"
lo, hi, nblocks, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
random.seed(seed)
def get(path):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(API + path, timeout=30) as r: return json.load(r)
        except Exception as e:
            time.sleep(2 + 2 * attempt)
    return None
heights = sorted(random.sample(range(lo, hi + 1), nblocks))
addrs = {}  # address -> count of appearances as an input signer in sampled blocks
blocks_ok = 0; inputs_total = 0; inputs_p2pk = 0
for h in heights:
    lst = get(f"/blocks?offset={h-1}&limit=1&sortBy=height&sortDirection=asc"); time.sleep(0.25)
    if not lst or not lst.get("items"): continue
    item = lst["items"][0]
    if item.get("height") != h: continue
    blk = get(f"/blocks/{item['id']}"); time.sleep(0.25)
    if not blk: continue
    blocks_ok += 1
    for tx in blk.get("block", {}).get("blockTransactions", []):
        seen = set()
        for inp in tx.get("inputs", []):
            a = inp.get("address") or ""; inputs_total += 1
            if a.startswith("9") and len(a) == 51 and a not in seen:
                seen.add(a); inputs_p2pk += 1; addrs[a] = addrs.get(a, 0) + 1
totals = {}
for i, a in enumerate(addrs):
    d = get(f"/addresses/{a}/transactions?limit=1"); time.sleep(0.3)
    if d and isinstance(d.get("total"), int): totals[a] = d["total"]
counts = sorted(totals.values())
n = len(counts)
w = [1.0 / c for c in counts]; W = sum(w)
def wq(p):  # weighted quantile under 1/count weights (estimates the per-address distribution)
    acc = 0.0
    for c, wi in zip(counts, w):
        acc += wi
        if acc >= p * W: return c
    return counts[-1] if counts else 0
def wshare(pred): return sum(wi for c, wi in zip(counts, w) if pred(c)) / W if W else 0
print(json.dumps({
  "range": [lo, hi], "blocks_sampled": blocks_ok, "inputs_seen": inputs_total, "p2pk_signer_appearances": inputs_p2pk,
  "distinct_signing_addresses": len(addrs), "addresses_with_total": n,
  "lifetime_tx_total_per_address_lengthbiased": {"median": statistics.median(counts) if n else 0, "mean": statistics.mean(counts) if n else 0, "max": counts[-1] if n else 0},
  "per_address_estimate_reweighted": {"median": wq(0.5), "p90": wq(0.9), "p99": wq(0.99), "share_1": wshare(lambda c: c == 1), "share_le_16": wshare(lambda c: c <= 16), "share_gt_16": wshare(lambda c: c > 16), "share_gt_1024": wshare(lambda c: c > 1024)},
  "note": "a block sample over-represents frequent signers; the reweighted block estimates the per-address distribution among addresses active in the sampled range; 'total' counts transactions involving the address (as input or output), an upper bound on signings"
}, indent=1))
