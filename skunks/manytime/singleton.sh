# singleton: SK-029 v3 (skunks/manytime/state.es + deposit.es). One mining node A at block version 4. keygen 2^H WOTS
# leaves (n=32, w=16); the wallet issues a token of supply 1; the state and deposit scripts are compiled with that
# token id; one wallet transaction funds the singleton S (token + R4 = 0), two plain deposits D1, D2 at the deposit
# address and one plain box P at the state address without the token. Rounds: forged (S), wrongindex (S), nostate
# (D1 alone, no singleton), addinput (signed over S alone, posted with D1 added), notoken (P with a valid signature),
# valid0 (S + D1, must confirm: S1 with R4 = 1, D1 gone), staleleaf (S1 with leaf 0), skip (S1 + D2 with leaf 3,
# must confirm: S2 with R4 = 4 and the token, D2 gone); then v3.1's rounds on S2: overindex (continuing index written as
# the leaf count), lastsame (leaf 15 with the token staying under this script), lastdeposit (leaf 15 with the token sent
# to the deposit script), rotate (leaf 15 with the token moved to key set B's singleton at index 0; must confirm), and
# a sweep of D3 by key set B's singleton with its leaf 0 (must confirm: the deposit address survives rotation).
# PASS = eight rejections, four confirmations, three deposits gone.
MT_N=${MT_N:-32}; MT_W=${MT_W:-16}; MT_H=${MT_H:-4}; FUND=${MT_FUND:-1000000000}; FEE=${MT_FEE:-1000000}; AMT=${MT_AMOUNT:-100000000}
MTD="$(dirname "$RIG_HOOK")"; REPO="$(cd "$MTD/../.." && pwd)"
CPF="$MTD/target/cp.txt"; WD="$SCRATCH/singleton"; mkdir -p "$WD"; DELAY="${REWARD_DELAY:-720}"
mt_cli(){ (cd "$REPO" && java -Dmanytime.dir="$MTD" -cp "$(cat "$CPF")" "$@"); }
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
send_wallet(){ # send_wallet <node> <requests json array> -> tx id or error text
  wallet "$1" /wallet/transaction/send "{\"requests\":$2,\"fee\":$FEE}" | jq -r 'if type == "string" then . else (.detail // .reason // tojson) end'; }
in_utxo(){ rest "$1" "/utxo/byId/$2" | jq -e '.boxId' >/dev/null 2>&1; }
end=$((SECONDS + 300)); bv=""
while [[ $SECONDS -lt $end ]]; do bv=$(rest A /info | jq -r '.parameters.blockVersion // empty' 2>/dev/null); [[ "$bv" == 4 ]] && break; sleep 3; done
echo "[sg] blockVersion=$bv at height $(full_height A); repo $REPO ($(cd "$REPO" && git rev-parse --short HEAD)); n=$MT_N w=$MT_W h=$MT_H"
[[ "$bv" == 4 ]] || { echo "[sg] FAIL: block version 4 did not activate"; rig_verdict=FAIL; }
[[ -s "$CPF" ]] || { echo "[sg] FAIL: $CPF missing (run build.sh)"; rig_verdict=FAIL; }
if [[ "${rig_verdict:-}" != FAIL ]]; then
  if bal=$(wait_balance A "$((FUND * 7))" 300); then echo "[sg] A balance $bal nanoERG at height $(full_height A)"; else echo "[sg] FAIL: balance"; rig_verdict=FAIL; fi
  ADDR_A=""; end=$((SECONDS + 60)); while [[ -z "$ADDR_A" && $SECONDS -lt $end ]]; do ADDR_A=$(address A 2>/dev/null); [[ -n "$ADDR_A" ]] || sleep 2; done
  [[ -n "$ADDR_A" ]] || { echo "[sg] FAIL: no wallet address"; rig_verdict=FAIL; }
fi
rej_forged=no; rej_wrongindex=no; rej_nostate=no; rej_addinput=no; rej_notoken=no; rej_stale=no; conf1=no; conf2=no; d1_gone=no; d2_gone=no
rej_overindex=no; rej_lastsame=no; rej_lastdeposit=no; conf_rotate=no; conf_after=no; d3_gone=no
if [[ "${rig_verdict:-}" != FAIL ]]; then
  mt_cli manytime.ManyTime keygen "$WD/keys" "$MT_N" "$MT_W" "$MT_H" manytime 2>&1 | sed 's/^/[sg] /'
  mt_cli manytime.ManyTime keygen "$WD/keysB" "$MT_N" "$MT_W" "$MT_H" manytime 2>&1 | sed 's/^/[sg:B] /'
  h0=$(full_height A)
  mint=$(send_wallet A "[{\"amount\":1,\"name\":\"sk029-singleton\",\"description\":\"\",\"decimals\":0}]")
  echo "[sg] token issue: $mint"
  if [[ "$mint" =~ ^[0-9a-f]{64}$ ]] && mh=$(find_tx A "$mint" "$h0" 120); then
    TOKEN=$(tx_in_block A "$mh" "$mint" | jq -r '.outputs[] | select(.assets | length > 0) | .assets[0].tokenId' | head -1)
    echo "[sg] token $TOKEN issued at height $mh"
  else echo "[sg] FAIL: token issue did not confirm"; rig_verdict=FAIL; fi
fi
if [[ "${rig_verdict:-}" != FAIL ]]; then
  mt_cli manytime.Singleton address "$WD/keys" "$TOKEN" 2>&1 | sed 's/^/[sg] /'
  mt_cli manytime.Singleton address "$WD/keysB" "$TOKEN" 2>&1 | sed 's/^/[sg:B] /'; STREE_B=$(cat "$WD/keysB/state-tree.hex")
  [[ "$(cat "$WD/keysB/deposit-address")" == "$(cat "$WD/keys/deposit-address")" ]] && echo "[sg] key set B shares the deposit address (same token)" || echo "[sg] FAIL: deposit addresses differ"

  SADDR=$(cat "$WD/keys/state-address"); DADDR=$(cat "$WD/keys/deposit-address"); STREE=$(cat "$WD/keys/state-tree.hex"); DTREE=$(cat "$WD/keys/deposit-tree.hex"); R4=$(cat "$WD/keys/r4-0.hex")
  h0=$(full_height A)
  fund=$(send_wallet A "[{\"address\":\"$SADDR\",\"value\":$FUND,\"assets\":[{\"tokenId\":\"$TOKEN\",\"amount\":1}],\"registers\":{\"R4\":\"$R4\"}},{\"address\":\"$DADDR\",\"value\":$FUND},{\"address\":\"$DADDR\",\"value\":$FUND},{\"address\":\"$DADDR\",\"value\":$FUND},{\"address\":\"$SADDR\",\"value\":$FUND}]")
  echo "[sg] funding S (token, R4=$R4), D1, D2, D3, P: $fund"
  if [[ "$fund" =~ ^[0-9a-f]{64}$ ]] && fh=$(find_tx A "$fund" "$h0" 120); then
    ftx=$(tx_in_block A "$fh" "$fund")
    S0=$(jq -r --arg t "$STREE" '.outputs[] | select(.ergoTree == $t and (.assets | length > 0)) | .boxId' <<< "$ftx")
    P0=$(jq -r --arg t "$STREE" '.outputs[] | select(.ergoTree == $t and (.assets | length == 0)) | .boxId' <<< "$ftx")
    D1=$(jq -r --arg t "$DTREE" '[.outputs[] | select(.ergoTree == $t) | .boxId][0]' <<< "$ftx"); D2=$(jq -r --arg t "$DTREE" '[.outputs[] | select(.ergoTree == $t) | .boxId][1]' <<< "$ftx"); D3=$(jq -r --arg t "$DTREE" '[.outputs[] | select(.ergoTree == $t) | .boxId][2]' <<< "$ftx")
    for b in S0 P0 D1 D2 D3; do rest A "/utxo/byId/${!b}" > "$WD/$b.json"; done
    echo "[sg] funded at height $fh: S0 $S0 R4=$(jq -r .additionalRegisters.R4 "$WD/S0.json") assets=$(jq -c '.assets' "$WD/S0.json"); P0 $P0 assets=$(jq -c .assets "$WD/P0.json"); D1 $D1 registers=$(jq -c '.additionalRegisters | keys' "$WD/D1.json"); D2 $D2"
  else echo "[sg] FAIL: funding did not confirm"; rig_verdict=FAIL; fi
fi
spend_round(){ # <stateFile|none> <depositFiles|none> <how> <tag> <expect: reject|confirm> [leaf]; sets LAST_BOX; KEYS_DIR selects the key set
  local sf="$1" df="$2" how="$3" tag="$4" expect="$5" leaf="${6:-}" hb code body vid
  ROTATE_KEYS="$WD/keysB" mt_cli manytime.Singleton spend "${KEYS_DIR:-$WD/keys}" "$sf" "$df" "$ADDR_A" "$FEE" "$AMT" "$how" "$DELAY" "$(full_height A)" $leaf > "$WD/tx_$tag.json" 2> "$WD/spend_$tag.err"
  grep -v '^\s*at ' "$WD/spend_$tag.err" | cut -c1-420 | sed "s/^/[sg:$tag] /"
  [[ -s "$WD/tx_$tag.json" ]] || { echo "[sg:$tag] FAIL: no transaction built"; return 1; }
  hb=$(full_height A); code=$(post_json A /transactions "$WD/tx_$tag.json"); body=$(cat "$WD/tx_$tag.json.body")
  if [[ "$expect" == reject ]]; then
    echo "[sg:$tag] POST -> HTTP $code: $(tr -d '\n' <<< "$body" | cut -c1-260)"
    echo "[sg:$tag] REJECTED local=$(grep -o 'total_cost=[^ ]*' "$WD/spend_$tag.err" | head -1) node_verdict=$(grep -o 'Success((false,[0-9]*))\|Failure([^)]*)' <<< "$body" | head -1)"
    [[ "$code" == 400 ]] && grep -q 'Scripts of all transaction inputs should pass verification' <<< "$body" && return 0 || return 1
  fi
  vid=$(jq -r 'if type == "string" then . else tojson end' <<< "$body" 2>/dev/null)
  local mp; mp=$(rest A "/transactions/unconfirmed/byTransactionId/$vid")
  echo "[sg:$tag] POST -> HTTP $code, tx $vid; mempool size=$(jq -r '.size // "absent"' <<< "$mp") cost=$(jq -r '.cost // "absent"' <<< "$mp")"
  if [[ "$code" == 200 && "$vid" =~ ^[0-9a-f]{64}$ ]] && vh=$(find_tx A "$vid" "$hb" 120); then
    local vtx; vtx=$(tx_in_block A "$vh" "$vid")
    echo "[sg:$tag] confirmed at height $vh; block tx size $(jq -r .size <<< "$vtx"); inputs $(jq -r '.inputs | length' <<< "$vtx"); singleton' R4=$(jq -r '.outputs[0].additionalRegisters.R4' <<< "$vtx") assets=$(jq -c '.outputs[0].assets' <<< "$vtx")"
    echo "[sg:$tag] RESULT $(grep -o 'leaf=[^ ]*\|next=[^ ]*\|total_cost=[^ ]*\|tx_bytes=[^ ]*\|out0_bytes=[^ ]*' "$WD/spend_$tag.err" | tr '\n' ' ')mempool_cost=$(jq -r '.cost // "absent"' <<< "$mp") block_tx_bytes=$(jq -r .size <<< "$vtx")"
    LAST_BOX=$(jq -r '.outputs[0].boxId' <<< "$vtx"); return 0
  fi
  echo "[sg:$tag] FAIL: not confirmed (HTTP $code: $(tr -d '\n' <<< "$body" | cut -c1-200))"; return 1
}
if [[ "${rig_verdict:-}" != FAIL ]]; then
  spend_round "$WD/S0.json" none forged forged reject && rej_forged=yes
  spend_round "$WD/S0.json" "$WD/D1.json" wrongindex wrongindex reject && rej_wrongindex=yes   # with D1 attached: the deposit script prints its own verdict (false: the index did not advance)
  spend_round none "$WD/D1.json" nostate nostate reject && rej_nostate=yes
  spend_round "$WD/S0.json" "$WD/D1.json" addinput addinput reject && rej_addinput=yes
  spend_round "$WD/P0.json" none valid notoken reject && rej_notoken=yes
  if spend_round "$WD/S0.json" "$WD/D1.json" valid valid0 confirm; then conf1=yes
    rest A "/utxo/byId/$LAST_BOX" > "$WD/S1.json"; echo "[sg] S1 $LAST_BOX R4=$(jq -r .additionalRegisters.R4 "$WD/S1.json") assets=$(jq -c .assets "$WD/S1.json")"
    in_utxo A "$D1" && echo "[sg] D1 still unspent" || { d1_gone=yes; echo "[sg] D1 spent (gone from UTXO)"; }
    spend_round "$WD/S1.json" none staleleaf staleleaf reject && rej_stale=yes
    if spend_round "$WD/S1.json" "$WD/D2.json" valid skip confirm 3; then conf2=yes
      rest A "/utxo/byId/$LAST_BOX" > "$WD/S2.json"; echo "[sg] S2 $LAST_BOX R4=$(jq -r .additionalRegisters.R4 "$WD/S2.json") assets=$(jq -c .assets "$WD/S2.json")"
      in_utxo A "$D2" && echo "[sg] D2 still unspent" || { d2_gone=yes; echo "[sg] D2 spent (gone from UTXO)"; }
      spend_round "$WD/S2.json" none overindex overindex reject && rej_overindex=yes
      spend_round "$WD/S2.json" none lastsame lastsame reject 15 && rej_lastsame=yes
      spend_round "$WD/S2.json" none lastdeposit lastdeposit reject 15 && rej_lastdeposit=yes
      if spend_round "$WD/S2.json" none rotate rotate confirm 15; then conf_rotate=yes
        rest A "/utxo/byId/$LAST_BOX" > "$WD/S3.json"; echo "[sg] S3 $LAST_BOX (key set B) R4=$(jq -r .additionalRegisters.R4 "$WD/S3.json") assets=$(jq -c .assets "$WD/S3.json") tree_is_B=$([[ "$(jq -r .ergoTree "$WD/S3.json")" == "$STREE_B" ]] && echo yes || echo no)"
        if KEYS_DIR="$WD/keysB" spend_round "$WD/S3.json" "$WD/D3.json" valid after confirm; then conf_after=yes
          rest A "/utxo/byId/$LAST_BOX" > "$WD/S4.json"; echo "[sg] S4 $LAST_BOX (key set B) R4=$(jq -r .additionalRegisters.R4 "$WD/S4.json") assets=$(jq -c .assets "$WD/S4.json")"
          in_utxo A "$D3" && echo "[sg] D3 still unspent" || { d3_gone=yes; echo "[sg] D3 spent by key set B's singleton (gone from UTXO)"; }
        fi
      fi
    fi
  fi
fi
echo "[sg] /info parameters: $(rest A /info | jq -c '.parameters')"
if [[ "${rig_verdict:-}" != FAIL && $rej_forged == yes && $rej_wrongindex == yes && $rej_nostate == yes && $rej_addinput == yes && $rej_notoken == yes && $conf1 == yes && $rej_stale == yes && $conf2 == yes && $d1_gone == yes && $d2_gone == yes && $rej_overindex == yes && $rej_lastsame == yes && $rej_lastdeposit == yes && $conf_rotate == yes && $conf_after == yes && $d3_gone == yes ]]; then rig_verdict=PASS; else rig_verdict=FAIL; fi
echo "SINGLETON: $rig_verdict (forged_rejected=$rej_forged wrongindex_rejected=$rej_wrongindex nostate_rejected=$rej_nostate addinput_rejected=$rej_addinput notoken_rejected=$rej_notoken spend0_confirmed=$conf1 staleleaf_rejected=$rej_stale skip_spend_confirmed=$conf2 deposit1_spent=$d1_gone deposit2_spent=$d2_gone overindex_rejected=$rej_overindex lastleaf_same_script_rejected=$rej_lastsame lastleaf_to_deposit_rejected=$rej_lastdeposit rotate_confirmed=$conf_rotate sweep_after_rotation_confirmed=$conf_after deposit3_spent=$d3_gone)"
