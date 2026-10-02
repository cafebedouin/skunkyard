# keyout: SK-027, keys outside the proposition (research/lattice/README.md, direction 4). One mining node A at
# block version 4. For each variant: keygen (a random key of KEY_BYTES, default 1952 = ML-DSA-65), fund the
# per-variant P2S address (r4key: via /wallet/transaction/send with the key in R4; others: a plain payment),
# confirm, read the box, post a forged spend (wrong key bytes; must be rejected by the script check) then the
# valid one (must confirm), and read size and cost from the mempool entry and the block.
# Variants: r4key (key in the box), single (key in context var 1), ring32 and ring1024 (AVL ring, key + proof).
# PASS = every variant's forged rejected (r4key has no forged) and valid confirmed. Needs build.sh run first.
KEYB=${KEY_BYTES:-1952}; FUND=${KO_FUND:-1000000000}; FEE=${KO_FEE:-1000000}
VARIANTS=${KO_VARIANTS:-"r4key single ring:32 ring:1024"}
KODEV="$(dirname "$RIG_HOOK")"; REPO="$(cd "$KODEV/../../.." && pwd)"
CPF="$KODEV/target/cp.txt"; WD="$SCRATCH/keyout"; mkdir -p "$WD"
DELAY="${REWARD_DELAY:-720}"
ko_cli(){ (cd "$REPO" && java -Dkeyout.dir="$KODEV" -cp "$(cat "$CPF")" lattice.KeyOut "$@"); }
post_json(){ ip netns exec "${NS[$1]}" curl -s --max-time 60 -o "$3.body" -w '%{http_code}' -X POST \
  -H "api_key: $API_KEY" -H 'Content-Type: application/json' --data @"$3" "http://127.0.0.1:${REST[$1]}$2"; }
find_tx(){ local n="$1" t="$2" k="$3" end=$((SECONDS + ${4:-120})) h hid
  while [[ $SECONDS -lt $end ]]; do h=$(full_height "$n")
    while [[ $k -le $h ]]; do hid=$(header_at "$n" "$k")
      [[ -n "$hid" ]] && rest "$n" "/blocks/$hid/transactions" | jq -e --arg t "$t" '.transactions[] | select(.id == $t)' >/dev/null 2>&1 \
        && { echo "$k"; return 0; }
      k=$((k + 1)); done
    sleep 1; done; return 1; }
tx_in_block(){ rest "$1" "/blocks/$(header_at "$1" "$2")/transactions" | jq -c --arg t "$3" '.transactions[] | select(.id == $t)'; }

end=$((SECONDS + 300)); bv=""
while [[ $SECONDS -lt $end ]]; do bv=$(rest A /info | jq -r '.parameters.blockVersion // empty' 2>/dev/null); [[ "$bv" == 4 ]] && break; sleep 3; done
echo "[ko] blockVersion=$bv at height $(full_height A)"
[[ "$bv" == 4 ]] || { echo "[ko] FAIL: block version 4 did not activate"; rig_verdict=FAIL; }
echo "[ko] repo $REPO ($(cd "$REPO" && git rev-parse --short HEAD 2>/dev/null)); chain minerRewardDelay=$DELAY; key_bytes=$KEYB; variants: $VARIANTS"
[[ -s "$CPF" ]] || { echo "[ko] FAIL: $CPF missing (run build.sh)"; rig_verdict=FAIL; }
nvar=$(wc -w <<< "$VARIANTS"); need=$((FUND * (nvar + 2)))
if [[ "${rig_verdict:-}" != FAIL ]]; then
  if bal=$(wait_balance A "$need" 300); then echo "[ko] A balance $bal nanoERG at height $(full_height A)"
  else echo "[ko] FAIL: A never reached $need nanoERG (balance $bal)"; rig_verdict=FAIL; fi
  ADDR_A=""; end=$((SECONDS + 60)); while [[ -z "$ADDR_A" && $SECONDS -lt $end ]]; do ADDR_A=$(address A 2>/dev/null); [[ -n "$ADDR_A" ]] || sleep 2; done
  [[ -n "$ADDR_A" ]] || { echo "[ko] FAIL: no wallet address for A"; rig_verdict=FAIL; }
fi
all_ok=yes
for v in $VARIANTS; do
  [[ "${rig_verdict:-}" == FAIL ]] && break
  mode=${v%%:*}; N=1; [[ "$v" == *:* ]] && N=${v##*:}
  K="$WD/$v"; rm -rf "$K"; mkdir -p "$K"
  ko_cli keygen "$K/keys" "$mode" "$KEYB" "$N" 2>&1 | sed "s/^/[ko:$v] /"
  P2S=$(cat "$K/keys/address"); TREE=$(cat "$K/keys/tree.hex")
  h0=$(full_height A)
  if [[ "$mode" == r4key ]]; then
    R4=$(cat "$K/keys/r4.hex")
    req="{\"requests\":[{\"address\":\"$P2S\",\"value\":$FUND,\"registers\":{\"R4\":\"$R4\"}}],\"fee\":$FEE}"
    fund=$(wallet A /wallet/transaction/send "$req" | jq -r 'if type == "string" then . else (.detail // .reason // tojson) end')
    echo "[ko:$v] funding via /wallet/transaction/send with R4 ($(( ${#R4} / 2 )) bytes): $fund"
  else
    req="[{\"address\":\"$P2S\",\"value\":$FUND}]"
    fund=$(wallet A /wallet/payment/send "$req" | jq -r 'if type == "string" then . else (.detail // .reason // tojson) end')
    echo "[ko:$v] funding via /wallet/payment/send: $fund"
  fi
  if [[ "$fund" =~ ^[0-9a-f]{64}$ ]] && fh=$(find_tx A "$fund" "$h0" 120); then
    ftx=$(tx_in_block A "$fh" "$fund")
    BOX=$(jq -r --arg t "$TREE" '.outputs[] | select(.ergoTree == $t) | .boxId' <<< "$ftx")
    rest A "/utxo/byId/$BOX" > "$K/box.json"
    echo "[ko:$v] funded at height $fh; box $BOX; registers: $(jq -c '.additionalRegisters | keys' "$K/box.json")"
  else echo "[ko:$v] FAIL: funding did not confirm ($fund)"; all_ok=no; continue; fi
  hows="forged valid"; [[ "$mode" == r4key ]] && hows="valid"
  forged_rejected=n/a; valid_confirmed=no
  for how in $hows; do
    ko_cli spend "$K/keys" "$K/box.json" "$ADDR_A" "$FEE" "$how" "$DELAY" > "$K/tx_$how.json" 2> "$K/spend_$how.err"
    grep -v '^\s*at ' "$K/spend_$how.err" | cut -c1-400 | sed "s/^/[ko:$v] /"
    [[ -s "$K/tx_$how.json" ]] || { echo "[ko:$v] FAIL: no transaction built for $how"; all_ok=no; continue; }
    hb=$(full_height A)
    code=$(post_json A /transactions "$K/tx_$how.json")
    body=$(cat "$K/tx_$how.json.body")
    if [[ "$how" == forged ]]; then
      echo "[ko:$v] FORGED POST -> HTTP $code: $(cut -c1-300 <<< "$body")"
      if [[ "$code" == 400 ]] && grep -q 'Scripts of all transaction inputs should pass verification' <<< "$body"; then forged_rejected=yes; else forged_rejected=no; all_ok=no; fi
    else
      vid=$(jq -r 'if type == "string" then . else tojson end' <<< "$body" 2>/dev/null)
      mp=$(rest A "/transactions/unconfirmed/byTransactionId/$vid")
      echo "[ko:$v] VALID POST -> HTTP $code, tx $vid; mempool size=$(jq -r '.size // "absent"' <<< "$mp" 2>/dev/null) cost=$(jq -r 'if has("cost") then (.cost|tostring) else "absent" end' <<< "$mp" 2>/dev/null)"
      if [[ "$code" == 200 && "$vid" =~ ^[0-9a-f]{64}$ ]] && vh=$(find_tx A "$vid" "$hb" 120); then
        vtx=$(tx_in_block A "$vh" "$vid"); valid_confirmed=yes
        echo "[ko:$v] VALID confirmed at height $vh; block tx size $(jq -r .size <<< "$vtx") bytes"
        echo "[ko:$v] RESULT variant=$v key_bytes=$KEYB $(grep -o 'cost=[^ ]*\|tx_bytes=[^ ]*\|ext_bytes=[^ ]*\|box_bytes=[^ ]*\|tree_bytes=[^ ]*' "$K/spend_valid.err" | tr '\n' ' ')mempool_size=$(jq -r '.size // "absent"' <<< "$mp") mempool_cost=$(jq -r '.cost // "absent"' <<< "$mp") block_tx_bytes=$(jq -r .size <<< "$vtx") forged_rejected=$forged_rejected"
      else echo "[ko:$v] FAIL: valid spend not confirmed (HTTP $code: $(cut -c1-300 <<< "$body"))"; all_ok=no; fi
    fi
  done
done
echo "[ko] /info parameters: $(rest A /info | jq -c '.parameters')"
if [[ "${rig_verdict:-}" != FAIL && $all_ok == yes ]]; then rig_verdict=PASS; else rig_verdict=FAIL; fi
echo "KEYOUT: $rig_verdict"
