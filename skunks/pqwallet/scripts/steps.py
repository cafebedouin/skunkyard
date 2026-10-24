#!/usr/bin/env python3
"""Chosen-digest search (pqwallet step 2): count each spend's WOTS+ chain steps with the Python reference's trace,
print the distribution, and write the spends with the most and the fewest steps as a sigs file for `verify-ext`.
Usage: steps.py <sigs.json> <slhdsa dir> <out extremes.json>"""
import importlib.util, json, statistics, sys
from pathlib import Path

sigs, slh, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
spec = importlib.util.spec_from_file_location("slhdsa_ref", slh / "slhdsa_ref.py")
ref = importlib.util.module_from_spec(spec); spec.loader.exec_module(ref)
CAP = ref.D * ref.LEN * (ref.W - 1)            # 3,675 hashed steps if every chain ran 15; a valid signature caps at 3,570
rows = []
for k in json.load(open(sigs))["keys"]:
    pk = bytes.fromhex(k["pk"])
    for s in k["spends"]:
        trace = {}
        ok = ref.verify(bytes.fromhex(s["msg"]), b"", bytes.fromhex(s["sig"]), pk, trace)
        steps = sum(sum(ref.W - 1 - d for d in t["digits"]) for t in trace["layers"])
        rows.append((steps, ok, k["pk"], s))
steps = [r[0] for r in rows]
mx, mn = max(rows, key=lambda r: r[0]), min(rows, key=lambda r: r[0])
print(f"steps spends={len(rows)} all_valid={all(r[1] for r in rows)} min={min(steps)} median={statistics.median(steps):.0f} "
      f"mean={statistics.mean(steps):.1f} sd={statistics.pstdev(steps):.1f} max={max(steps)} cap_valid=3570 cap_variant={CAP}")
print(f"steps max_spend i={mx[3]['i']} steps={mx[0]}  min_spend i={mn[3]['i']} steps={mn[0]}")
json.dump({"keys": [{"pk": mx[2], "spends": [mx[3], mn[3]]}]}, open(out, "w"))
print(f"steps extremes -> {out}")
