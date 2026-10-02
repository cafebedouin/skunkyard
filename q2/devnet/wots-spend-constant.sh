# wots-spend-constant: vault step 1 (skunks/vault/CHARTER.md). A WOTS (n=32, w=16) spend of a box locked by
# q2/wots-constant.es: the 32-byte commitment blake2b256(pk) is compiled into the script, so the key has its own P2S
# address and the box has no registers. Run with wots-spend-v4.json: waits for block version 4 (the 6.0 rules), then
# A funds the per-key address with a plain /wallet/payment/send (no registers field, the wallet's default fee);
# q2/devnet/Spend.scala (key mode constant) builds the spending transaction with context variable 0 (the signature)
# only. A forged signature (one bit flipped) must be rejected by POST /transactions with the script-verification
# message (HTTP 400); the valid one must be accepted and confirmed.
# PASS = forged rejected by the script check AND valid confirmed. Needs q2/devnet/build.sh run first.
# Env: WOTS_N (32), WOTS_W (16), WOTS_FUND (1 ERG), WOTS_FEE (0.001 ERG, the spend's fee).
N_=${WOTS_N:-32}; W_=${WOTS_W:-16}; FUND=${WOTS_FUND:-1000000000}; FEE=${WOTS_FEE:-1000000}
Q2DEV="$(dirname "$RIG_HOOK")"; REPO="$(cd "$Q2DEV/../.." && pwd)"
CPF="$Q2DEV/target/cp.txt"; WD="$SCRATCH/wots-constant"; mkdir -p "$WD"
DELAY="${REWARD_DELAY:-720}"
spend_cli(){ (cd "$REPO" && java -cp "$(cat "$CPF")" q2.Spend "$@"); }
# post_json <node> <path> <file>: POST the file; body to <file>.body, prints the HTTP status
post_json(){ ip netns exec "${NS[$1]}" curl -s --max-time 60 -o "$3.body" -w '%{http_code}' -X POST \
  -H "api_key: $API_KEY" -H 'Content-Type: application/json' --data @"$3" "http://127.0.0.1:${REST[$1]}$2"; }
# find_tx <node> <txid> <from height> [timeout s]: the height of the block holding the tx, scanning forward
find_tx(){ local n="$1" t="$2" k="$3" end=$((SECONDS + ${4:-120})) h hid
  while [[ $SECONDS -lt $end ]]; do h=$(full_height "$n")
    while [[ $k -le $h ]]; do hid=$(header_at "$n" "$k")
      [[ -n "$hid" ]] && rest "$n" "/blocks/$hid/transactions" | jq -e --arg t "$t" '.transactions[] | select(.id == $t)' >/dev/null 2>&1 \
        && { echo "$k"; return 0; }
      k=$((k + 1)); done
    sleep 1; done; return 1; }
tx_in_block(){ rest "$1" "/blocks/$(header_at "$1" "$2")/transactions" | jq -c --arg t "$3" '.transactions[] | select(.id == $t)'; }

forged_rejected=no; valid_confirmed=no

# 0. block version 4
end=$((SECONDS + 300)); bv=""
while [[ $SECONDS -lt $end ]]; do bv=$(rest A /info | jq -r '.parameters.blockVersion // empty' 2>/dev/null); [[ "$bv" == 4 ]] && break; sleep 3; done
echo "[wc] blockVersion=$bv at height $(full_height A) after waiting $((SECONDS - end + 300)) s"
[[ "$bv" == 4 ]] || { echo "[wc] FAIL: block version 4 did not activate"; rig_verdict=FAIL; }

echo "[wc] repo $REPO ($(cd "$REPO" && git rev-parse --short HEAD 2>/dev/null)); chain minerRewardDelay=$DELAY"
[[ -s "$CPF" ]] || { echo "[wc] FAIL: $CPF missing (run q2/devnet/build.sh)"; rig_verdict=FAIL; }

# 1. per-key keys, tree and address; A's matured balance
if [[ "${rig_verdict:-}" != FAIL ]]; then
  spend_cli keygen "$N_" "$W_" "$WD/keys" constant 2>&1 | sed 's/address=.*/address=(in keys\/address)/; s/^/[wc] /'
  P2S=$(cat "$WD/keys/address"); TREE=$(cat "$WD/keys/tree.hex")
  echo "[wc] per-key P2S address ${P2S:0:24}... (${#P2S} chars), tree $(( ${#TREE} / 2 )) bytes, r4.hex present: $([[ -e "$WD/keys/r4.hex" ]] && echo yes || echo no)"
  need=$((FUND * 3))
  if bal=$(wait_balance A "$need" 300); then echo "[wc] A balance $bal nanoERG at height $(full_height A)"
  else echo "[wc] FAIL: A never reached $need nanoERG (balance $bal)"; rig_verdict=FAIL; fi
  ADDR_A=""; end=$((SECONDS + 60)); while [[ -z "$ADDR_A" && $SECONDS -lt $end ]]; do ADDR_A=$(address A 2>/dev/null); [[ -n "$ADDR_A" ]] || sleep 2; done
  echo "[wc] A address ${ADDR_A:-(none)}"
  [[ -n "$ADDR_A" ]] || { echo "[wc] FAIL: no wallet address for A"; rig_verdict=FAIL; }
fi

# 2. fund with a plain payment (no registers), confirm, fetch the box, check it has no R4
if [[ "${rig_verdict:-}" != FAIL ]]; then
  h0=$(full_height A)
  req="[{\"address\":\"$P2S\",\"value\":$FUND}]"
  echo "[wc] funding request body (address elided): $(jq -c --arg a "${P2S:0:24}..." '.[0].address = $a' <<< "$req")"
  fund=$(wallet A /wallet/payment/send "$req" | jq -r 'if type == "string" then . else (.detail // .reason // tojson) end')
  echo "[wc] funding via /wallet/payment/send (no registers): $fund"
  [[ "$fund" =~ ^[0-9a-f]{64}$ ]] && echo "[wc] funding tx mempool entry (P2PK wallet spend): $(rest A "/transactions/unconfirmed/byTransactionId/$fund" | jq -c '{size, cost, inputs: (.inputs | length), outputs: (.outputs | length)}')"
  if [[ "$fund" =~ ^[0-9a-f]{64}$ ]] && fh=$(find_tx A "$fund" "$h0" 120); then
    ftx=$(tx_in_block A "$fh" "$fund")
    BOX=$(jq -r --arg t "$TREE" '.outputs[] | select(.ergoTree == $t) | .boxId' <<< "$ftx")
    echo "[wc] funding tx confirmed at height $fh; WOTS box $BOX"
    rest A "/utxo/byId/$BOX" > "$WD/box.json"
    echo "[wc] /utxo/byId/$BOX: value $(jq -r .value "$WD/box.json"), additionalRegisters $(jq -c .additionalRegisters "$WD/box.json"), creationHeight $(jq -r .creationHeight "$WD/box.json"), ergoTree equals the per-key tree: $(jq -e --arg t "$TREE" '.ergoTree == $t' "$WD/box.json" >/dev/null && echo yes || echo no)"
    if jq -e '(.additionalRegisters // {}) | has("R4") | not' "$WD/box.json" >/dev/null 2>&1 && jq -e '.boxId' "$WD/box.json" >/dev/null 2>&1; then
      echo "[wc] box has no R4: yes"
    else echo "[wc] FAIL: box has R4 or was not read"; rig_verdict=FAIL; fi
  else echo "[wc] FAIL: funding did not confirm"; rig_verdict=FAIL; fi
fi

# 3. build forged and valid spends (context variable 0 only)
if [[ "${rig_verdict:-}" != FAIL ]]; then
  for mode in forged valid; do
    spend_cli spend "$WD/keys" "$WD/box.json" "$ADDR_A" "$FEE" "$mode" "$DELAY" > "$WD/tx_$mode.json" 2> "$WD/spend_$mode.err"
    sed 's/^/[wc] /' "$WD/spend_$mode.err" | grep -v '^\[wc\]\s*at ' | cut -c1-400
  done
  [[ -s "$WD/tx_forged.json" && -s "$WD/tx_valid.json" ]] || { echo "[wc] FAIL: Spend.scala built no transaction"; rig_verdict=FAIL; }
  [[ -s "$WD/tx_valid.json" ]] && echo "[wc] context extension keys sent: $(jq -c '.inputs[0].spendingProof.extension | keys' "$WD/tx_valid.json")"
fi

# 4. post forged, then valid
if [[ "${rig_verdict:-}" != FAIL ]]; then
  code=$(post_json A /transactions "$WD/tx_forged.json")
  echo "[wc] FORGED POST /transactions -> HTTP $code"
  echo "[wc] FORGED response: $(jq -c . "$WD/tx_forged.json.body" 2>/dev/null || cat "$WD/tx_forged.json.body")"
  if [[ "$code" == 400 ]] && grep -q 'Scripts of all transaction inputs should pass verification' "$WD/tx_forged.json.body"; then forged_rejected=yes
  elif [[ "$code" == 400 ]]; then echo "[wc] forged 400 is not a script-verification rejection: not counted"
  elif [[ "$code" == 200 ]]; then echo "[wc] FAIL: forged signature accepted"; fi

  h1=$(full_height A)
  code=$(post_json A /transactions "$WD/tx_valid.json")
  vid=$(jq -r 'if type == "string" then . else tojson end' "$WD/tx_valid.json.body" 2>/dev/null)
  mp=$(rest A "/transactions/unconfirmed/byTransactionId/$vid")
  echo "[wc] VALID POST /transactions -> HTTP $code, tx id $vid"
  echo "[wc] node tx id equals Spend.scala's local tx id: $(grep -q "tx_id=$vid " "$WD/spend_valid.err" && echo yes || echo no)"
  echo "[wc] mempool entry (/transactions/unconfirmed/byTransactionId): size=$(jq -r '.size // "absent"' <<< "$mp" 2>/dev/null) cost=$(jq -r 'if has("cost") then (.cost|tostring) else "absent" end' <<< "$mp" 2>/dev/null)"
  if [[ "$code" == 200 && "$vid" =~ ^[0-9a-f]{64}$ ]] && vh=$(find_tx A "$vid" "$h1" 120); then
    vtx=$(tx_in_block A "$vh" "$vid"); valid_confirmed=yes
    hid=$(header_at A "$vh")
    echo "[wc] VALID confirmed at height $vh (block $hid), block tx count $(block_txs A "$vh")"
    echo "[wc] confirmed tx size (block /transactions .size): $(jq -r .size <<< "$vtx") bytes; outputs $(jq -c '[.outputs[] | {value, ergoTree: .ergoTree[0:16]}]' <<< "$vtx")"
    echo "[wc] block header version $(rest A "/blocks/$hid/header" | jq -r .version)"
    echo "[wc] WOTS box spent (no longer in UTXO): $(rest A "/utxo/byId/$BOX" | jq -r 'if .boxId then "no" else "yes" end' 2>/dev/null)"
  else echo "[wc] valid spend not confirmed (HTTP $code: $(cat "$WD/tx_valid.json.body"))"; fi
fi

echo "[wc] /info parameters: $(rest A /info | jq -c '.parameters')"
echo "[wc] /info: $(rest A /info | jq -c '{network, appVersion, fullHeight}')"
if [[ "${rig_verdict:-}" != FAIL && $forged_rejected == yes && $valid_confirmed == yes ]]; then rig_verdict=PASS; else rig_verdict=FAIL; fi
echo "WOTS-CONSTANT: $rig_verdict (forged_rejected=$forged_rejected valid_confirmed=$valid_confirmed)"
