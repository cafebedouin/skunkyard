#!/usr/bin/env bash
# Compare the scan's traversed root with the stateRoot in the header of the block the scanned state was at,
# as served by the running node (GET /blocks/{id}/header needs no API key).
set -euo pipefail
OUT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/out"
NODE="${NODE_URL:-http://127.0.0.1:9053}"
hid=$(grep '^state_header_id,' "$OUT/totals.csv" | cut -d, -f2)
root=$(grep '^traversed_root,' "$OUT/totals.csv" | cut -d, -f2)
hdr=$(curl -s -m 10 "$NODE/blocks/$hid/header")
python3 - "$hid" "$root" "$hdr" "$OUT/node-info.json" <<'PY'
import json, sys
import os
hid, root, hdr = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
info = json.load(open(sys.argv[4])) if os.path.exists(sys.argv[4]) else None
print(f"scanned state header id:            {hid}")
print(f"header height / stateRoot (node):   {hdr['height']} {hdr['stateRoot']}")
print(f"traversed root digest (scan):       {root}")
print(f"header stateRoot == traversed root: {hdr['stateRoot'] == root}")
if info:
    print(f"/info before stop: fullHeight={info['fullHeight']} bestFullHeaderId={info['bestFullHeaderId']} stateRoot={info['stateRoot']}")
    print(f"/info stateRoot == traversed root:  {info['stateRoot'] == root}  (blocks applied between /info and stop: {hdr['height'] - info['fullHeight']})")
else:
    print("(no out/node-info.json: the /info comparison is skipped; the header comparison above is the check)")
PY
