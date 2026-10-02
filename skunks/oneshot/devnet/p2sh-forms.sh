# p2sh-forms: are the three P2SH box-script forms spendable on a node? (skunks/oneshot/RESULT.md, "P2SH forms on a
# node".) One P2SH address around proveDlog(pk); sigmastate-js writes a var-126 tree, Fleet a var-1 tree, ergo-lib-wasm
# a var-1 tree without OptionGet (scripts/p2sh-forms.mjs --plan prints them and the testnet P2S address of each).
# Run with oneshot-v4.json (one node, block version 4, extraIndex). Steps: wait for block version 4 and A's balance;
# A pays 1 ERG to the P2S address of each tree with /wallet/payment/send (six outputs: sigma x2, fleet x2, rust x2);
# then, inside A's namespace, scripts/p2sh-forms.mjs --spend for each box: build with Fleet, var = 08cd ++ pk, sign,
# POST /transactions, wait for the block. Spends:
#   sigma/sigmastate-js, fleet/sigmastate-js, rust/ergo-lib-wasm, rust/sigmastate-js   (the question)
#   sigma/ergo-lib-wasm --message-proof (control: a message-signing proof on a form that spends),
#   fleet/ergo-lib-wasm (whether ergo-lib-wasm's transaction signer handles Fleet's tree)
# The node's verdict is recorded verbatim. PASS = every spend got a verdict from the node (accepted and confirmed, or a
# rejection), whatever it is: this hook measures, it does not expect. Needs `npm ci` in skunks/oneshot/recon first.
FUND=${P2SH_FUND:-1000000000}
DEVDIR="$(dirname "$RIG_HOOK")"; PKG="$(cd "$DEVDIR/.." && pwd)"; REPO="$(cd "$PKG/../.." && pwd)"
WD="$SCRATCH/p2sh-forms"; mkdir -p "$WD"
DELAY="${REWARD_DELAY:-720}"
PF="$PKG/scripts/p2sh-forms.mjs"
find_tx(){ local n="$1" t="$2" k="$3" end=$((SECONDS + ${4:-120})) h hid
  while [[ $SECONDS -lt $end ]]; do h=$(full_height "$n")
    while [[ $k -le $h ]]; do hid=$(header_at "$n" "$k")
      [[ -n "$hid" ]] && rest "$n" "/blocks/$hid/transactions" | jq -e --arg t "$t" '.transactions[] | select(.id == $t)' >/dev/null 2>&1 \
        && { echo "$k"; return 0; }
      k=$((k + 1)); done
    sleep 1; done; return 1; }
tx_in_block(){ rest "$1" "/blocks/$(header_at "$1" "$2")/transactions" | jq -c --arg t "$3" '.transactions[] | select(.id == $t)'; }

verdicts=0; spends=0

# 0. block version 4, tools
end=$((SECONDS + 300)); bv=""
while [[ $SECONDS -lt $end ]]; do bv=$(rest A /info | jq -r '.parameters.blockVersion // empty' 2>/dev/null); [[ "$bv" == 4 ]] && break; sleep 3; done
echo "[pf] blockVersion=$bv at height $(full_height A)"
[[ "$bv" == 4 ]] || { echo "[pf] FAIL: block version 4 did not activate"; rig_verdict=FAIL; }
echo "[pf] repo $REPO ($(cd "$REPO" && git rev-parse --short HEAD 2>/dev/null)$(cd "$REPO" && [[ -n "$(git status --porcelain -- skunks/oneshot 2>/dev/null)" ]] && echo ', skunks/oneshot modified')); node $(node --version); chain minerRewardDelay=$DELAY"
[[ -d "$PKG/recon/node_modules/sigmastate-js" && -d "$PKG/recon/node_modules/ergo-lib-wasm-nodejs" ]] || { echo "[pf] FAIL: $PKG/recon/node_modules missing (npm ci there)"; rig_verdict=FAIL; }

# 1. the three trees and their P2S addresses; A's balance and address
declare -A TREE P2S VARID
if [[ "${rig_verdict:-}" != FAIL ]]; then
  node "$PF" --plan > "$WD/plan.txt" 2>&1 || { echo "[pf] FAIL: --plan"; rig_verdict=FAIL; }
  sed 's/^/[pf] /' "$WD/plan.txt"
  while read -r tag f v t a; do [[ "$tag" == FORM ]] && { TREE[$f]=$t; P2S[$f]=$a; VARID[$f]=$v; }; done < "$WD/plan.txt"
  if bal=$(wait_balance A $((FUND * 8)) 300); then echo "[pf] A balance $bal nanoERG at height $(full_height A)"
  else echo "[pf] FAIL: A never reached $((FUND * 8)) nanoERG (balance $bal)"; rig_verdict=FAIL; fi
  ADDR_A=""; end=$((SECONDS + 60)); while [[ -z "$ADDR_A" && $SECONDS -lt $end ]]; do ADDR_A=$(address A 2>/dev/null); [[ -n "$ADDR_A" ]] || sleep 2; done
  echo "[pf] A address ${ADDR_A:-(none)}"
  [[ -n "$ADDR_A" ]] || { echo "[pf] FAIL: no wallet address for A"; rig_verdict=FAIL; }
fi

# 2. fund: one payment, two outputs per form (exactly the tree bytes, through the P2S address of those bytes)
declare -A BOXES
if [[ "${rig_verdict:-}" != FAIL ]]; then
  req=$(jq -cn --arg s "${P2S[sigma]}" --arg f "${P2S[fleet]}" --arg r "${P2S[rust]}" --argjson v "$FUND" \
    '[$s,$s,$f,$f,$r,$r] | map({address: ., value: $v})')
  h0=$(full_height A)
  fund=$(wallet A /wallet/payment/send "$req" | jq -r 'if type == "string" then . else tojson end')
  echo "[pf] funding via /wallet/payment/send (6 outputs, no registers): $fund"
  if [[ "$fund" =~ ^[0-9a-f]{64}$ ]] && fh=$(find_tx A "$fund" "$h0" 120); then
    ftx=$(tx_in_block A "$fh" "$fund")
    echo "[pf] funding tx confirmed at height $fh"
    for f in sigma fleet rust; do
      BOXES[$f]=$(jq -r --arg t "${TREE[$f]}" '[.outputs[] | select(.ergoTree == $t) | .boxId] | join(" ")' <<< "$ftx")
      echo "[pf] form $f: tree in the funded boxes equals the plan's tree bytes: $([[ $(wc -w <<< "${BOXES[$f]}") == 2 ]] && echo 'yes (2 boxes)' || echo "NO ($(jq -c '[.outputs[].ergoTree]' <<< "$ftx"))"); boxes ${BOXES[$f]}"
    done
    WALLET_FEE_TREE=$(jq -r '.outputs[] | select(.ergoTree | startswith("1005040004000e")) | .ergoTree' <<< "$ftx" | head -1)
  else echo "[pf] FAIL: funding did not confirm"; rig_verdict=FAIL; fi
fi

# 3. the spends, inside A's namespace
declare -a ROWS
spend(){ local form="$1" signer="$2" box="$3"; shift 3; local out="$WD/spend-$form-$signer$([[ $# -gt 0 ]] && echo -control).out" res
  spends=$((spends + 1))
  ip netns exec "${NS[A]}" node "$PF" --spend --api "http://127.0.0.1:${REST[A]}" --form "$form" --signer "$signer" --box "$box" \
    --to "$ADDR_A" --fee-delay "$DELAY" --confirm-timeout 120 "$@" > "$out" 2>&1
  grep -v '^TX ' "$out" | sed 's/^/[pf] /'
  echo "[pf] tx json: $(grep '^TX ' "$out" | cut -c4- | cut -c1-2000)"
  res=$(grep '^RESULT ' "$out" | tail -1)
  [[ "$res" =~ outcome=(confirmed|rejected|accepted-not-confirmed) ]] && verdicts=$((verdicts + 1))
  local via; [[ $signer == sigmastate-js ]] && via="reduce + signReduced" || via="Wallet.sign_transaction"
  if grep -q -- '--message-proof' "$out"; then via="$(grep '^PROOFVIA' "$out" | awk '{print $3}' | tr -d ';') over the bytes to sign, control"
  elif grep -q '^PROOFVIA' "$out"; then via="$(grep '^PROOFVIA' "$out" | awk '{print $3}' | tr -d ';') over the bytes to sign; transaction signing failed locally"; fi
  local resp; resp=$(grep '^SUBMIT ' "$out" | cut -d' ' -f2- ); local hgt; hgt=$(grep -o 'height=[0-9]*' <<< "$res" | cut -d= -f2)
  ROWS+=("$form|${VARID[$form]}|$signer ($via)|${resp:-(not submitted)}|${hgt:--}")
}
if [[ "${rig_verdict:-}" != FAIL ]]; then
  read -r s1 s2 <<< "${BOXES[sigma]}"; read -r f1 f2 <<< "${BOXES[fleet]}"; read -r r1 r2 <<< "${BOXES[rust]}"
  spend sigma sigmastate-js "$s1"
  spend fleet sigmastate-js "$f1"
  spend rust ergo-lib-wasm "$r1"
  spend rust sigmastate-js "$r2"
  spend sigma ergo-lib-wasm "$s2" --message-proof
  spend fleet ergo-lib-wasm "$f2"
fi

echo "[pf] table: form | writer | var | signed by | node response (POST /transactions, verbatim) | confirmed height"
declare -A WRITER=([sigma]=sigmastate-js [fleet]=Fleet [rust]=ergo-lib-wasm)
for r in "${ROWS[@]}"; do IFS='|' read -r f v s n h <<< "$r"; echo "[pf] $f | ${WRITER[$f]} | $v | $s | $n | $h"; done
echo "[pf] /info: $(rest A /info | jq -c '{network, appVersion, fullHeight, blockVersion: .parameters.blockVersion}')"
if [[ "${rig_verdict:-}" != FAIL && $spends -gt 0 && $verdicts == $spends ]]; then rig_verdict=PASS; else rig_verdict=FAIL; fi
echo "P2SH-FORMS: $rig_verdict (node verdicts $verdicts of $spends spends)"
