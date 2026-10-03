#!/usr/bin/env bash
# Public-testnet run of the many-time box through the Cornell node (API open). Needs a funded box id in $BOX0.
set -uo pipefail
NODE=${NODE:-http://128.253.41.110:9052}; REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"; TN="$REPO/skunks/manytime/testnet"
KEYS="${KEYS:-$TN/keys}"; TO=${TO_ADDR:-3WxtnwJojAm4C9DJtgNHs5zawzD44yE6cKyGM7NeHf7Cw1yP7XBU}   # the project's testnet wallet
FEE=1100000; AMT=100000000; DELAY=720
cli(){ (cd "$REPO" && java -Dmanytime.dir=skunks/manytime -cp "$(cat skunks/manytime/target-tn/cp.txt)" manytime.ManyTime "$@"); }
log(){ echo "[tn $(date -u +%H:%M:%SZ)] $*"; }
post(){ curl -s --max-time 60 -o "$2.body" -w '%{http_code}' -X POST -H 'Content-Type: application/json' --data @"$1" "$NODE/transactions"; }
wait_box(){ local id="$1" end=$((SECONDS + ${2:-900})); while [[ $SECONDS -lt $end ]]; do curl -s --max-time 15 "$NODE/utxo/byId/$id" > "$TN/box-$id.json" 2>/dev/null; python3 -c "import json,sys; d=json.load(open('$TN/box-$id.json')); sys.exit(0 if d.get('boxId') else 1)" 2>/dev/null && return 0; sleep 20; done; return 1; }
round(){ # <boxfile> <how> <tag> [leaf]; logs go to stderr so the caller can capture the code alone
  local bf="$1" how="$2" tag="$3" leaf="${4:-}" code h
  h=$(curl -s --max-time 10 "$NODE/info" | python3 -c 'import sys,json; print(json.load(sys.stdin)["fullHeight"])')
  cli spend "$KEYS" "$bf" "$TO" "$FEE" "$AMT" "$how" "$DELAY" "$h" $leaf > "$TN/tx_$tag.json" 2> "$TN/spend_$tag.err"
  grep -v '^\s*at ' "$TN/spend_$tag.err" | cut -c1-420 | sed "s/^/[tn:$tag] /" >&2
  code=$(post "$TN/tx_$tag.json" "$TN/tx_$tag.json"); log "$tag POST -> HTTP $code: $(tr -d '\n' < "$TN/tx_$tag.json.body" | cut -c1-240)" >&2
  echo "$code"
}
log "box0 $BOX0; node $(curl -s --max-time 10 $NODE/info | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["appVersion"], "height", d["fullHeight"], "blockVersion", d["parameters"]["blockVersion"])')"
wait_box "$BOX0" 60 || { log "box0 not in UTXO"; exit 1; }
B0="$TN/box-$BOX0.json"
c=$(round "$B0" forged forged); [[ "$c" == 400 ]] && grep -q 'should pass verification' "$TN/tx_forged.json.body" && R1=yes || R1=no
c=$(round "$B0" wrongindex wrongindex); [[ "$c" == 400 ]] && grep -q 'should pass verification' "$TN/tx_wrongindex.json.body" && R2=yes || R2=no
c=$(round "$B0" valid valid0); C1=no
if [[ "$c" == 200 ]]; then BOX1=$(grep -o 'out0_id=[0-9a-f]*' "$TN/spend_valid0.err" | cut -d= -f2); log "waiting for box1 $BOX1"
  if wait_box "$BOX1" 900; then C1=yes; log "box1 in UTXO: creationHeight $(python3 -c "import json; d=json.load(open('$TN/box-$BOX1.json')); print(d['creationHeight'], 'R4', d['additionalRegisters'].get('R4'))")"
    B1="$TN/box-$BOX1.json"
    c=$(round "$B1" staleleaf staleleaf); [[ "$c" == 400 ]] && grep -q 'should pass verification' "$TN/tx_staleleaf.json.body" && R3=yes || R3=no
    c=$(round "$B1" valid below 0); [[ "$c" == 400 ]] && grep -q 'should pass verification' "$TN/tx_below.json.body" && R4=yes || R4=no
    c=$(round "$B1" valid valid1 3); C2=no
    if [[ "$c" == 200 ]]; then BOX2=$(grep -o 'out0_id=[0-9a-f]*' "$TN/spend_valid1.err" | cut -d= -f2); log "waiting for box2 $BOX2 (leaf 3 used; R4 should read 4)"
      wait_box "$BOX2" 900 && { C2=yes; log "box2 in UTXO: creationHeight $(python3 -c "import json; d=json.load(open('$TN/box-$BOX2.json')); print(d['creationHeight'], 'R4', d['additionalRegisters'].get('R4'))")"; }; fi
  fi; fi
log "TESTNET-MANYTIME: forged_rejected=$R1 wrongindex_rejected=$R2 valid0_confirmed=$C1 staleleaf_rejected=${R3:-n/a} below_rejected=${R4:-n/a} skip_leaf3_confirmed=${C2:-n/a}"
