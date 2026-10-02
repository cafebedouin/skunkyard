# oneshot-flow: oneshot step 3 (skunks/oneshot/CHARTER.md). A real node accepts a WOTS spend built by the page's
# own code (src/spend.ts, run headless by scripts/flow.mjs). Run with oneshot-v4.json (one node, block version 4,
# ergo.node.extraIndex = true for /blockchain/box/unspent/byAddress). Steps: wait for block version 4 and A's
# matured balance; flow.mjs --generate (fresh seed, address); A funds the address with a plain
# /wallet/payment/send (no registers); then flow.mjs in node mode INSIDE A's namespace, forged first (signature
# byte 0 flipped, must get the node's script-verification 400), then valid (must confirm). Both runs pass the same
# --height and --state, so the forged and the valid transaction sign the same message (one signature, not two).
# PASS = forged rejected by the script check AND valid confirmed. Needs `npm ci` in skunks/oneshot first.
# Env: ONESHOT_SEED (hex; default a fresh one), ONESHOT_FUND (1 ERG).
FUND=${ONESHOT_FUND:-1000000000}
DEVDIR="$(dirname "$RIG_HOOK")"; PKG="$(cd "$DEVDIR/.." && pwd)"; REPO="$(cd "$PKG/../.." && pwd)"
WD="$SCRATCH/oneshot-flow"; mkdir -p "$WD"
DELAY="${REWARD_DELAY:-720}"
FLOW="$PKG/scripts/flow.mjs"
# find_tx <node> <txid> <from height> [timeout s]: the height of the block holding the tx, scanning forward
find_tx(){ local n="$1" t="$2" k="$3" end=$((SECONDS + ${4:-120})) h hid
  while [[ $SECONDS -lt $end ]]; do h=$(full_height "$n")
    while [[ $k -le $h ]]; do hid=$(header_at "$n" "$k")
      [[ -n "$hid" ]] && rest "$n" "/blocks/$hid/transactions" | jq -e --arg t "$t" '.transactions[] | select(.id == $t)' >/dev/null 2>&1 \
        && { echo "$k"; return 0; }
      k=$((k + 1)); done
    sleep 1; done; return 1; }
tx_in_block(){ rest "$1" "/blocks/$(header_at "$1" "$2")/transactions" | jq -c --arg t "$3" '.transactions[] | select(.id == $t)'; }
flow_in_A(){ ip netns exec "${NS[A]}" node "$FLOW" "$@"; }

forged_rejected=no; valid_confirmed=no

# 0. block version 4, tools
end=$((SECONDS + 300)); bv=""
while [[ $SECONDS -lt $end ]]; do bv=$(rest A /info | jq -r '.parameters.blockVersion // empty' 2>/dev/null); [[ "$bv" == 4 ]] && break; sleep 3; done
echo "[os] blockVersion=$bv at height $(full_height A)"
[[ "$bv" == 4 ]] || { echo "[os] FAIL: block version 4 did not activate"; rig_verdict=FAIL; }
echo "[os] repo $REPO ($(cd "$REPO" && git rev-parse --short HEAD 2>/dev/null)$(cd "$REPO" && [[ -n "$(git status --porcelain -- skunks/oneshot 2>/dev/null)" ]] && echo ', skunks/oneshot modified')); node $(node --version); chain minerRewardDelay=$DELAY"
[[ -d "$PKG/node_modules/@fleet-sdk/core" ]] || { echo "[os] FAIL: $PKG/node_modules missing (npm ci)"; rig_verdict=FAIL; }

# 1. key, A's balance and address
if [[ "${rig_verdict:-}" != FAIL ]]; then
  if [[ -n "${ONESHOT_SEED:-}" ]]; then SEED="$ONESHOT_SEED"; else SEED=$(node "$FLOW" --generate | awk '$1 == "seed" {print $2}'); fi
  P2S=$(node "$FLOW" --seed "$SEED" --address)
  echo "[os] seed $SEED"
  echo "[os] oneshot address ${P2S:0:24}... (${#P2S} chars)"
  if bal=$(wait_balance A $((FUND * 3)) 300); then echo "[os] A balance $bal nanoERG at height $(full_height A)"
  else echo "[os] FAIL: A never reached $((FUND * 3)) nanoERG (balance $bal)"; rig_verdict=FAIL; fi
  ADDR_A=""; end=$((SECONDS + 60)); while [[ -z "$ADDR_A" && $SECONDS -lt $end ]]; do ADDR_A=$(address A 2>/dev/null); [[ -n "$ADDR_A" ]] || sleep 2; done
  echo "[os] A address ${ADDR_A:-(none)}"
  [[ -n "$ADDR_A" ]] || { echo "[os] FAIL: no wallet address for A"; rig_verdict=FAIL; }
fi

# 2. fund with a plain payment (no registers) and wait for the block
if [[ "${rig_verdict:-}" != FAIL ]]; then
  h0=$(full_height A)
  fund=$(wallet A /wallet/payment/send "[{\"address\":\"$P2S\",\"value\":$FUND}]" | jq -r 'if type == "string" then . else (.detail // .reason // tojson) end')
  echo "[os] funding via /wallet/payment/send (no registers): $fund"
  if [[ "$fund" =~ ^[0-9a-f]{64}$ ]] && fh=$(find_tx A "$fund" "$h0" 120); then
    ftx=$(tx_in_block A "$fh" "$fund")
    echo "[os] funding tx confirmed at height $fh; outputs $(jq -c '[.outputs[] | {value, ergoTree: (.ergoTree[0:16] + "..."), registers: (.additionalRegisters | length)}]' <<< "$ftx")"
    WALLET_FEE_TREE=$(jq -r '.outputs[] | select(.ergoTree | startswith("1005040004000e")) | .ergoTree' <<< "$ftx" | head -1)
  else echo "[os] FAIL: funding did not confirm"; rig_verdict=FAIL; fi
fi

# 3. forged, then valid, in A's namespace, same height and state file
if [[ "${rig_verdict:-}" != FAIL ]]; then
  H=$(full_height A)
  API="http://127.0.0.1:${REST[A]}"
  echo "[os] flow: ip netns exec ${NS[A]} node skunks/oneshot/scripts/flow.mjs --api $API --mode node --seed <seed> --to <A> --height $H --fee-delay $DELAY --state <wd>/state.json [--forge]"
  flow_in_A --api "$API" --mode node --seed "$SEED" --to "$ADDR_A" --height "$H" --fee-delay "$DELAY" \
    --state "$WD/state.json" --wait-box 60 --out "$WD/forged.json" --forge > "$WD/forged.out" 2>&1; frc=$?
  sed 's/^/[os] /' "$WD/forged.out"
  echo "[os] forged run exit status $frc"
  [[ $frc == 0 ]] && grep -q '^FLOW: FORGED-REJECTED' "$WD/forged.out" \
    && grep -q 'Scripts of all transaction inputs should pass verification' "$WD/forged.out" && forged_rejected=yes

  flow_in_A --api "$API" --mode node --seed "$SEED" --to "$ADDR_A" --height "$H" --fee-delay "$DELAY" \
    --state "$WD/state.json" --out "$WD/valid.json" --confirm-timeout 180 > "$WD/valid.out" 2>&1; vrc=$?
  sed 's/^/[os] /' "$WD/valid.out"
  echo "[os] valid run exit status $vrc"
  echo "[os] forged and valid signed the same message: $([[ "$(grep -o 'message [0-9a-f]*' "$WD/forged.out")" == "$(grep -o 'message [0-9a-f]*' "$WD/valid.out")" ]] && echo yes || echo no)"
  echo "[os] fee tree built by flow.mjs equals the wallet's own fee output: $([[ -n "$WALLET_FEE_TREE" && "$(jq -r '.outputs[1].ergoTree' "$WD/valid.json")" == "$WALLET_FEE_TREE" ]] && echo yes || echo no)"
  if [[ $vrc == 0 ]] && read -r _ _ vid _ vh < <(grep '^FLOW: CONFIRMED' "$WD/valid.out"); then
    vtx=$(tx_in_block A "$vh" "$vid")
    if [[ -n "$vtx" ]]; then valid_confirmed=yes
      hid=$(header_at A "$vh")
      echo "[os] node block at height $vh holds $vid: yes; block $hid, tx count $(block_txs A "$vh"), header version $(rest A "/blocks/$hid/header" | jq -r .version)"
      echo "[os] confirmed tx size (block /transactions .size): $(jq -r .size <<< "$vtx") bytes; extension keys $(jq -c '.inputs[0].spendingProof.extension | keys' <<< "$vtx"); outputs $(jq -c '[.outputs[] | {value, ergoTree: (.ergoTree[0:16] + "...")}]' <<< "$vtx")"
    else echo "[os] flow said confirmed but block $vh does not hold $vid"; fi
  fi
fi

echo "[os] /info: $(rest A /info | jq -c '{network, appVersion, fullHeight, blockVersion: .parameters.blockVersion}')"
if [[ "${rig_verdict:-}" != FAIL && $forged_rejected == yes && $valid_confirmed == yes ]]; then rig_verdict=PASS; else rig_verdict=FAIL; fi
echo "ONESHOT-FLOW: $rig_verdict (forged_rejected=$forged_rejected valid_confirmed=$valid_confirmed)"
