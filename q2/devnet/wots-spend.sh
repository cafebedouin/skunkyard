# wots-spend: a WOTS (n=32, w=16) one-time-signature spend on a one-node devnet (PILOT-Q2 step 4).
# A mines into its wallet; once rewards mature, the wallet funds a box at the P2S address of q2/wots.es with
# R4 = blake2b256(pk); q2/devnet/Spend.scala builds the spending transaction (context var 0 = signature, 1 = full
# public key; outputs: value - fee to A's address, fee to the miner-fee script). A forged signature (one byte
# flipped) must be rejected by POST /transactions (HTTP 400); the valid one must be accepted and confirmed.
# PASS = forged rejected AND valid confirmed. Needs q2/devnet/build.sh run first (target/cp.txt).
# Env: WOTS_N (32), WOTS_W (16), WOTS_FUND (1 ERG), WOTS_FEE (0.001 ERG).
N_=${WOTS_N:-32}; W_=${WOTS_W:-16}; FUND=${WOTS_FUND:-1000000000}; FEE=${WOTS_FEE:-1000000}
Q2DEV="$(dirname "$RIG_HOOK")"; REPO="$(cd "$Q2DEV/../.." && pwd)"
CPF="$Q2DEV/target/cp.txt"; WD="$SCRATCH/wots"; mkdir -p "$WD"
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
echo "[wots] repo $REPO ($(cd "$REPO" && git rev-parse --short HEAD 2>/dev/null)); chain minerRewardDelay=$DELAY"
[[ -s "$CPF" ]] || { echo "[wots] FAIL: $CPF missing (run q2/devnet/build.sh)"; rig_verdict=FAIL; }

if [[ "${rig_verdict:-}" != FAIL ]]; then
  spend_cli keygen "$N_" "$W_" "$WD/keys" 2>&1 | sed 's/address=.*/address=(in keys\/address)/; s/^/[wots] /'
  P2S=$(cat "$WD/keys/address"); TREE=$(cat "$WD/keys/tree.hex"); R4=$(cat "$WD/keys/r4.hex")
  echo "[wots] P2S address ${P2S:0:24}... (${#P2S} chars), tree $(( ${#TREE} / 2 )) bytes, R4 $R4"
  need=$((FUND * 3))
  if bal=$(wait_balance A "$need" 300); then echo "[wots] A balance $bal nanoERG at height $(full_height A)"
  else echo "[wots] FAIL: A never reached $need nanoERG (balance $bal)"; rig_verdict=FAIL; fi
  # the wallet answers /wallet/addresses only once it is ready: read it after the balance, and insist on one
  ADDR_A=""; end=$((SECONDS + 60)); while [[ -z "$ADDR_A" && $SECONDS -lt $end ]]; do ADDR_A=$(address A 2>/dev/null); [[ -n "$ADDR_A" ]] || sleep 2; done
  echo "[wots] A address ${ADDR_A:-(none)}"
  [[ -n "$ADDR_A" ]] || { echo "[wots] FAIL: no wallet address for A"; rig_verdict=FAIL; }
fi

if [[ "${rig_verdict:-}" != FAIL ]]; then
  h0=$(full_height A)
  req="{\"requests\":[{\"address\":\"$P2S\",\"value\":$FUND,\"registers\":{\"R4\":\"$R4\"}}],\"fee\":$FEE}"
  fund=$(wallet A /wallet/transaction/send "$req" | jq -r 'if type == "string" then . else (.detail // .reason // tojson) end')
  echo "[wots] funding via /wallet/transaction/send (registers R4): $fund"
  # the funding transaction is an ordinary wallet P2PK (proveDlog) spend: its node cost is the Schnorr baseline
  [[ "$fund" =~ ^[0-9a-f]{64}$ ]] && echo "[wots] funding tx mempool entry (P2PK spend, Schnorr baseline): $(rest A "/transactions/unconfirmed/byTransactionId/$fund" | jq -c '{size, cost, inputs: (.inputs | length), outputs: (.outputs | length)}')"
  if [[ "$fund" =~ ^[0-9a-f]{64}$ ]] && fh=$(find_tx A "$fund" "$h0" 120); then
    ftx=$(tx_in_block A "$fh" "$fund")
    BOX=$(jq -r --arg t "$TREE" '.outputs[] | select(.ergoTree == $t) | .boxId' <<< "$ftx")
    echo "[wots] funding tx confirmed at height $fh; WOTS box $BOX"
    echo "[wots] funding tx fee output trees: $(jq -r --arg t "$TREE" '[.outputs[] | select(.ergoTree != $t) | .ergoTree[0:24]] | join(" ")' <<< "$ftx")"
    rest A "/utxo/byId/$BOX" > "$WD/box.json"
    echo "[wots] /utxo/byId/$BOX: value $(jq -r .value "$WD/box.json"), R4 $(jq -r .additionalRegisters.R4 "$WD/box.json"), creationHeight $(jq -r .creationHeight "$WD/box.json")"
    [[ "$(jq -r .additionalRegisters.R4 "$WD/box.json")" == "$R4" ]] || { echo "[wots] FAIL: box R4 differs from the key's commitment"; rig_verdict=FAIL; }
  else echo "[wots] FAIL: funding did not confirm"; rig_verdict=FAIL; fi
fi

if [[ "${rig_verdict:-}" != FAIL ]]; then
  for mode in forged valid; do
    spend_cli spend "$WD/keys" "$WD/box.json" "$ADDR_A" "$FEE" "$mode" "$DELAY" > "$WD/tx_$mode.json" 2> "$WD/spend_$mode.err"
    sed 's/^/[wots] /' "$WD/spend_$mode.err" | grep -v '^\[wots\]\s*at ' | cut -c1-400
  done
  [[ -s "$WD/tx_forged.json" && -s "$WD/tx_valid.json" ]] || { echo "[wots] FAIL: Spend.scala built no transaction"; rig_verdict=FAIL; }
fi

if [[ "${rig_verdict:-}" != FAIL ]]; then
  fee_local=$(grep -o 'fee_tree=[0-9a-f]*' "$WD/spend_valid.err" | cut -d= -f2)
  echo "[wots] fee tree built here equals the wallet's own fee output: $(jq -e --arg f "$fee_local" 'any(.outputs[]; .ergoTree == $f)' <<< "$ftx" >/dev/null && echo yes || echo no)"

  code=$(post_json A /transactions "$WD/tx_forged.json")
  echo "[wots] FORGED POST /transactions -> HTTP $code"
  echo "[wots] FORGED response: $(jq -c . "$WD/tx_forged.json.body" 2>/dev/null || cat "$WD/tx_forged.json.body")"
  # a rejection counts only if it is the script check failing, not any 400 (an empty or malformed body is also a 400)
  if [[ "$code" == 400 ]] && grep -q 'Scripts of all transaction inputs should pass verification' "$WD/tx_forged.json.body"; then forged_rejected=yes
  elif [[ "$code" == 400 ]]; then echo "[wots] forged 400 is not a script-verification rejection: not counted"
  elif [[ "$code" == 200 ]]; then echo "[wots] FAIL: forged signature accepted"; fi

  h1=$(full_height A)
  code=$(post_json A /transactions "$WD/tx_valid.json")
  vid=$(jq -r 'if type == "string" then . else tojson end' "$WD/tx_valid.json.body" 2>/dev/null)
  mp=$(rest A "/transactions/unconfirmed/byTransactionId/$vid")
  echo "[wots] VALID POST /transactions -> HTTP $code, tx id $vid"
  echo "[wots] node tx id equals Spend.scala's local tx id: $(grep -q "tx_id=$vid " "$WD/spend_valid.err" && echo yes || echo no)"
  echo "[wots] mempool entry (/transactions/unconfirmed/byTransactionId): size=$(jq -r '.size // "absent"' <<< "$mp" 2>/dev/null) cost=$(jq -r 'if has("cost") then (.cost|tostring) else "absent" end' <<< "$mp" 2>/dev/null)"
  if [[ "$code" == 200 && "$vid" =~ ^[0-9a-f]{64}$ ]] && vh=$(find_tx A "$vid" "$h1" 120); then
    vtx=$(tx_in_block A "$vh" "$vid"); valid_confirmed=yes
    hid=$(header_at A "$vh")
    echo "[wots] VALID confirmed at height $vh (block $hid), block tx count $(block_txs A "$vh")"
    echo "[wots] confirmed tx size (block /transactions .size): $(jq -r .size <<< "$vtx") bytes; outputs $(jq -c '[.outputs[] | {value, ergoTree: .ergoTree[0:16]}]' <<< "$vtx")"
    echo "[wots] block $vh transactions: $(rest A "/blocks/$hid/transactions" | jq -c '[.transactions[] | {id: .id[0:16], inputs: (.inputs | length), outputs: (.outputs | length), size}]')"
    echo "[wots] block header version $(rest A "/blocks/$hid/header" | jq -r .version)"
    echo "[wots] WOTS box spent (no longer in UTXO): $(rest A "/utxo/byId/$BOX" | jq -r 'if .boxId then "no" else "yes" end' 2>/dev/null)"
  else echo "[wots] valid spend not confirmed (HTTP $code: $(cat "$WD/tx_valid.json.body"))"; fi
fi

echo "[wots] /info parameters: $(rest A /info | jq -c '.parameters')"
echo "[wots] /info: $(rest A /info | jq -c '{network, appVersion, fullHeight}')"
if [[ "${rig_verdict:-}" != FAIL && $forged_rejected == yes && $valid_confirmed == yes ]]; then rig_verdict=PASS; else rig_verdict=FAIL; fi
echo "WOTS-SPEND: $rig_verdict (forged_rejected=$forged_rejected valid_confirmed=$valid_confirmed)"
