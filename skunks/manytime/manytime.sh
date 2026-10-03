# manytime: SK-029, many-time hash-based keys with no fork (skunks/manytime/). One mining node A at block
# version 4. keygen 2^H WOTS leaves (n=32, w=16) under one AVL root; fund the box with R4 = 0 (leaf index);
# on the funded box post: forged (one signature bit flipped; must be rejected by the script check), wrongindex
# (recreated box keeps R4 = i; must be rejected), valid (must confirm, recreating the box with R4 = 1); then on the
# recreated box: staleleaf (leaf 0's signature and proof against R4 = 1; must be rejected), valid with leaf 1 (must
# confirm, R4 = 2). Each rejection prints the local cost and the node's verdict. PASS = three rejections, two
# confirmations.
MT_N=${MT_N:-32}; MT_W=${MT_W:-16}; MT_H=${MT_H:-4}; FUND=${MT_FUND:-1000000000}; FEE=${MT_FEE:-1000000}; AMT=${MT_AMOUNT:-100000000}
MTD="$(dirname "$RIG_HOOK")"; REPO="$(cd "$MTD/../.." && pwd)"
CPF="$MTD/target/cp.txt"; WD="$SCRATCH/manytime"; mkdir -p "$WD"; DELAY="${REWARD_DELAY:-720}"
mt_cli(){ (cd "$REPO" && java -Dmanytime.dir="$MTD" -cp "$(cat "$CPF")" manytime.ManyTime "$@"); }
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
echo "[mt] blockVersion=$bv at height $(full_height A); repo $REPO ($(cd "$REPO" && git rev-parse --short HEAD)); n=$MT_N w=$MT_W h=$MT_H"
[[ "$bv" == 4 ]] || { echo "[mt] FAIL: block version 4 did not activate"; rig_verdict=FAIL; }
[[ -s "$CPF" ]] || { echo "[mt] FAIL: $CPF missing (run build.sh)"; rig_verdict=FAIL; }
if [[ "${rig_verdict:-}" != FAIL ]]; then
  if bal=$(wait_balance A "$((FUND * 3))" 300); then echo "[mt] A balance $bal nanoERG at height $(full_height A)"; else echo "[mt] FAIL: balance"; rig_verdict=FAIL; fi
  ADDR_A=""; end=$((SECONDS + 60)); while [[ -z "$ADDR_A" && $SECONDS -lt $end ]]; do ADDR_A=$(address A 2>/dev/null); [[ -n "$ADDR_A" ]] || sleep 2; done
  [[ -n "$ADDR_A" ]] || { echo "[mt] FAIL: no wallet address"; rig_verdict=FAIL; }
fi
rej_forged=no; rej_wrongindex=no; rej_stale=no; rej_below=no; conf3=no; rej_nodlog=n/a; [[ "${MT_MODE:-manytime}" == hybrid ]] && rej_nodlog=no; conf1=no; conf2=no
if [[ "${rig_verdict:-}" != FAIL ]]; then
  mt_cli keygen "$WD/keys" "$MT_N" "$MT_W" "$MT_H" "${MT_MODE:-manytime}" 2>&1 | sed 's/^/[mt] /'
  P2S=$(cat "$WD/keys/address"); TREE=$(cat "$WD/keys/tree.hex"); R4=$(cat "$WD/keys/r4-0.hex")
  h0=$(full_height A)
  req="{\"requests\":[{\"address\":\"$P2S\",\"value\":$FUND,\"registers\":{\"R4\":\"$R4\"}}],\"fee\":$FEE}"
  fund=$(wallet A /wallet/transaction/send "$req" | jq -r 'if type == "string" then . else (.detail // .reason // tojson) end')
  echo "[mt] funding with R4=$R4: $fund"
  if [[ "$fund" =~ ^[0-9a-f]{64}$ ]] && fh=$(find_tx A "$fund" "$h0" 120); then
    BOX=$(tx_in_block A "$fh" "$fund" | jq -r --arg t "$TREE" '.outputs[] | select(.ergoTree == $t) | .boxId')
    rest A "/utxo/byId/$BOX" > "$WD/box0.json"; echo "[mt] funded at height $fh; box0 $BOX R4=$(jq -r .additionalRegisters.R4 "$WD/box0.json")"
  else echo "[mt] FAIL: funding did not confirm"; rig_verdict=FAIL; fi
fi
spend_round(){ # <boxfile> <how> <tag> [leaf] ; sets LAST_BOX
  local bf="$1" how="$2" tag="$3" leaf="${4:-}" hb code body vid
  mt_cli spend "$WD/keys" "$bf" "$ADDR_A" "$FEE" "$AMT" "$how" "$DELAY" "$(full_height A)" $leaf > "$WD/tx_$tag.json" 2> "$WD/spend_$tag.err"
  grep -v '^\s*at ' "$WD/spend_$tag.err" | cut -c1-420 | sed "s/^/[mt:$tag] /"
  [[ -s "$WD/tx_$tag.json" ]] || { echo "[mt:$tag] FAIL: no transaction built"; return 1; }
  hb=$(full_height A); code=$(post_json A /transactions "$WD/tx_$tag.json"); body=$(cat "$WD/tx_$tag.json.body")
  if [[ "$how" != valid ]]; then
    echo "[mt:$tag] POST -> HTTP $code: $(tr -d '\n' <<< "$body" | cut -c1-260)"
    echo "[mt:$tag] REJECTED local_cost=$(grep -o 'cost=[^ ]*' "$WD/spend_$tag.err" | head -1) node_verdict=$(grep -o 'Success((false,[0-9]*))\|Failure([^)]*)' <<< "$body" | head -1)"
    [[ "$code" == 400 ]] && grep -q 'Scripts of all transaction inputs should pass verification' <<< "$body" && return 0 || return 1
  fi
  vid=$(jq -r 'if type == "string" then . else tojson end' <<< "$body" 2>/dev/null)
  local mp; mp=$(rest A "/transactions/unconfirmed/byTransactionId/$vid")
  echo "[mt:$tag] POST -> HTTP $code, tx $vid; mempool size=$(jq -r '.size // "absent"' <<< "$mp") cost=$(jq -r '.cost // "absent"' <<< "$mp")"
  if [[ "$code" == 200 && "$vid" =~ ^[0-9a-f]{64}$ ]] && vh=$(find_tx A "$vid" "$hb" 120); then
    local vtx; vtx=$(tx_in_block A "$vh" "$vid")
    echo "[mt:$tag] confirmed at height $vh; block tx size $(jq -r .size <<< "$vtx"); recreated box R4=$(jq -r '.outputs[0].additionalRegisters.R4' <<< "$vtx")"
    echo "[mt:$tag] RESULT $(grep -o 'leaf=[^ ]*\|next=[^ ]*\|cost=[^ ]*\|tx_bytes=[^ ]*\|sig_bytes=[^ ]*\|proof_bytes=[^ ]*\|box_bytes=[^ ]*\|tree_bytes=[^ ]*' "$WD/spend_$tag.err" | tr '\n' ' ')mempool_cost=$(jq -r '.cost // "absent"' <<< "$mp") block_tx_bytes=$(jq -r .size <<< "$vtx")"
    LAST_BOX=$(jq -r '.outputs[0].boxId' <<< "$vtx"); return 0
  fi
  echo "[mt:$tag] FAIL: not confirmed (HTTP $code: $(tr -d '\n' <<< "$body" | cut -c1-200))"; return 1
}
if [[ "${rig_verdict:-}" != FAIL ]]; then
  if [[ "${MT_MODE:-manytime}" == hybrid ]]; then spend_round "$WD/box0.json" nodlog nodlog && rej_nodlog=yes; fi
  spend_round "$WD/box0.json" forged forged && rej_forged=yes
  spend_round "$WD/box0.json" wrongindex wrongindex && rej_wrongindex=yes
  if spend_round "$WD/box0.json" valid valid0; then conf1=yes
    rest A "/utxo/byId/$LAST_BOX" > "$WD/box1.json"; echo "[mt] box1 $LAST_BOX R4=$(jq -r .additionalRegisters.R4 "$WD/box1.json")"
    spend_round "$WD/box1.json" staleleaf staleleaf && rej_stale=yes
    spend_round "$WD/box1.json" valid below 0 && rej_below=no || rej_below=yes   # leaf 0 named explicitly against R4 = 1: must be rejected
    if spend_round "$WD/box1.json" valid skip 3; then conf2=yes   # leaf 3 >= 1: allowed, next index 4
      rest A "/utxo/byId/$LAST_BOX" > "$WD/box2.json"; echo "[mt] box2 $LAST_BOX R4=$(jq -r .additionalRegisters.R4 "$WD/box2.json")"
      # a second plain box at the same address (no R4), spent with the wallet counter leaf 4: the per-box index is 0, the wallet's is 4
      hb=$(full_height A); f2=$(wallet A /wallet/payment/send "[{\"address\":\"$P2S\",\"value\":$FUND}]" | jq -r 'if type == "string" then . else (.detail // .reason // tojson) end')
      if [[ "$f2" =~ ^[0-9a-f]{64}$ ]] && fh2=$(find_tx A "$f2" "$hb" 120); then
        B3=$(tx_in_block A "$fh2" "$f2" | jq -r --arg t "$TREE" '.outputs[] | select(.ergoTree == $t) | .boxId'); rest A "/utxo/byId/$B3" > "$WD/box3.json"
        echo "[mt] second plain box $B3 registers: $(jq -c '.additionalRegisters | keys' "$WD/box3.json")"
        spend_round "$WD/box3.json" valid plain2 4 && conf3=yes
      else echo "[mt] second plain funding did not confirm"; fi
    fi
  fi
fi
echo "[mt] /info parameters: $(rest A /info | jq -c '.parameters')"
if [[ "${rig_verdict:-}" != FAIL && $rej_forged == yes && $rej_wrongindex == yes && $rej_stale == yes && $conf1 == yes && $conf2 == yes && $rej_below == yes && $conf3 == yes && ( $rej_nodlog == n/a || $rej_nodlog == yes ) ]]; then rig_verdict=PASS; else rig_verdict=FAIL; fi
echo "MANYTIME: $rig_verdict (mode=${MT_MODE:-manytime} nodlog_rejected=$rej_nodlog forged_rejected=$rej_forged wrongindex_rejected=$rej_wrongindex staleleaf_rejected=$rej_stale below_rejected=$rej_below spend0_confirmed=$conf1 skip_spend_confirmed=$conf2 second_plain_box_confirmed=$conf3)"
