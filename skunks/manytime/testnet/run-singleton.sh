#!/usr/bin/env bash
# Public-testnet run of the v3 singleton design (state.es + deposit.es) through a public testnet node (API open).
# Mints the key set's token with the project's testnet wallet (Fleet), compiles the two scripts with its id, funds the
# singleton S (token, R4 = 0), two plain deposits D1, D2 and a plain box P at the state address without the token in one
# transaction, then posts the eight rounds of skunks/manytime/singleton.sh. Logs to stderr; artifacts in testnet/v3-artifacts/.
set -uo pipefail
NODE=${NODE:-http://128.253.41.110:9052}; REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"; TN="$REPO/skunks/manytime/testnet"; ART="$TN/v3-artifacts"; mkdir -p "$ART"
KEYS="${KEYS:-$TN/keys-v3}"; KEYSB="${KEYSB:-$TN/keys-v3B}"; TO=${TO_ADDR:-3WxtnwJojAm4C9DJtgNHs5zawzD44yE6cKyGM7NeHf7Cw1yP7XBU}   # the project's testnet wallet
FEE=1100000; AMT=50000000; DELAY=720; FUND_S=4000000000; FUND_D=100000000   # v3.3: the singleton must exceed 2.5M nanoERG per byte
cli(){ (cd "$REPO" && java -Dmanytime.dir=skunks/manytime -cp "$(cat skunks/manytime/target-tn/cp.txt)" "$@"); }
fund(){ (cd "$REPO/skunks/oneshot" && node scripts/fund-any.mjs "$@"); }
log(){ echo "[tn $(date -u +%H:%M:%SZ)] $*" >&2; }
post(){ curl -s --max-time 60 -o "$2.body" -w '%{http_code}' -X POST -H 'Content-Type: application/json' --data @"$1" "$NODE/transactions"; }
height(){ curl -s --max-time 10 "$NODE/info" | python3 -c 'import sys,json; print(json.load(sys.stdin)["fullHeight"])'; }
wait_box(){ local id="$1" end=$((SECONDS + ${2:-900})); while [[ $SECONDS -lt $end ]]; do curl -s --max-time 15 "$NODE/utxo/byId/$id" > "$ART/box-$id.json" 2>/dev/null; python3 -c "import json,sys; d=json.load(open('$ART/box-$id.json')); sys.exit(0 if d.get('boxId') else 1)" 2>/dev/null && return 0; sleep 20; done; return 1; }
gone(){ curl -s --max-time 15 "$NODE/utxo/byId/$1" | python3 -c 'import sys,json; d=json.load(sys.stdin); sys.exit(1 if d.get("boxId") else 0)' 2>/dev/null; }
round(){ # <stateFile|none> <depositFiles|none> <how> <tag> [leaf] -> HTTP code on stdout
  local sf="$1" df="$2" how="$3" tag="$4" leaf="${5:-}" code
  ROTATE_KEYS="$KEYSB" cli manytime.Singleton spend "${KEYS_DIR:-$KEYS}" "$sf" "$df" "$TO" "$FEE" "$AMT" "$how" "$DELAY" "$(height)" $leaf > "$ART/tx_$tag.json" 2> "$ART/spend_$tag.err"
  grep -v '^\s*at ' "$ART/spend_$tag.err" | cut -c1-420 | sed "s/^/[tn:$tag] /" >&2
  code=$(post "$ART/tx_$tag.json" "$ART/tx_$tag.json"); log "$tag POST -> HTTP $code: $(tr -d '\n' < "$ART/tx_$tag.json.body" | cut -c1-240)"
  echo "$code"
}
rejected(){ [[ "$1" == 400 ]] && grep -q 'should pass verification' "$ART/tx_$2.json.body" && echo yes || echo no; }
log "node $(curl -s --max-time 10 $NODE/info | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["appVersion"], "height", d["fullHeight"], "blockVersion", d["parameters"]["blockVersion"])')"
if [[ ! -s "$KEYS/token.hex" ]]; then
  cli manytime.ManyTime keygen "$KEYS" 32 16 4 manytime 2>&1 | sed 's/^/[tn] /' >&2
  mint=$(fund --mint --amount 100000000 --submit "$NODE" 2>&1 | tee "$ART/mint.log" | tail -1); TOKEN=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['tokenId'])" "$mint" 2>/dev/null)
  [[ "$TOKEN" =~ ^[0-9a-f]{64}$ ]] || { log "mint failed: $(tail -3 "$ART/mint.log" | tr '\n' ' ')"; exit 1; }
  MBOX=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['boxId'])" "$mint"); log "token $TOKEN minted in box $MBOX; waiting for it in the node's UTXO"
  wait_box "$MBOX" 1200 || { log "mint box not in UTXO"; exit 1; }
  end=$((SECONDS + 1200)); while [[ $SECONDS -lt $end ]]; do curl -s --max-time 20 "https://api-testnet.ergoplatform.com/api/v1/boxes/unspent/byAddress/$TO?limit=100" | grep -q "$TOKEN" && break; sleep 30; done
  curl -s --max-time 20 "https://api-testnet.ergoplatform.com/api/v1/boxes/unspent/byAddress/$TO?limit=100" | grep -q "$TOKEN" || { log "explorer does not list the token box yet"; exit 1; }
  cli manytime.Singleton address "$KEYS" "$TOKEN" 2>&1 | sed 's/^/[tn] /' >&2
  cli manytime.ManyTime keygen "$KEYSB" 32 16 4 manytime 2>&1 | sed 's/^/[tn:B] /' >&2
  cli manytime.Singleton address "$KEYSB" "$TOKEN" 2>&1 | sed 's/^/[tn:B] /' >&2
fi
TOKEN=$(cat "$KEYS/token.hex"); SADDR=$(cat "$KEYS/state-address"); DADDR=$(cat "$KEYS/deposit-address"); STREE=$(cat "$KEYS/state-tree.hex"); DTREE=$(cat "$KEYS/deposit-tree.hex")
if [[ ! -s "$ART/funding.json" ]]; then
  fund --out "$SADDR,$FUND_S,r4=0400,token=$TOKEN" --out "$DADDR,$FUND_D" --out "$DADDR,$FUND_D" --out "$DADDR,$FUND_D" --out "$SADDR,$FUND_D" --submit "$NODE" 2>&1 | tee "$ART/fund.log" | tail -1 > "$ART/funding.json"
  grep -q '"txId"' "$ART/funding.json" || { log "funding failed: $(tail -3 "$ART/fund.log" | tr '\n' ' ')"; rm -f "$ART/funding.json"; exit 1; }
fi
pick(){ python3 - "$ART/funding.json" "$1" "$2" "$3" <<'PY'
import json,sys; d=json.load(open(sys.argv[1])); tree=sys.argv[2]; want=sys.argv[3]=='token'; k=int(sys.argv[4])
m=[o['boxId'] for o in d['outputs'] if o['ergoTree']==tree and (len(o['assets'])>0)==want]; print(m[k] if k < len(m) else '')
PY
}
S0=$(pick "$STREE" token 0); P0=$(pick "$STREE" plain 0); D1=$(pick "$DTREE" plain 0); D2=$(pick "$DTREE" plain 1); D3=$(pick "$DTREE" plain 2)
log "funding tx $(python3 -c "import json; print(json.load(open('$ART/funding.json'))['txId'])"): S0 $S0 P0 $P0 D1 $D1 D2 $D2 D3 $D3"
wait_box "$S0" 1200 || { log "S0 not in UTXO"; exit 1; }; for b in $P0 $D1 $D2 $D3; do wait_box "$b" 120 || { log "$b not in UTXO"; exit 1; }; done
log "S0 in UTXO: creationHeight $(python3 -c "import json; d=json.load(open('$ART/box-$S0.json')); print(d['creationHeight'], 'R4', d['additionalRegisters'].get('R4'), 'assets', d['assets'])")"
SF="$ART/box-$S0.json"; PF="$ART/box-$P0.json"; D1F="$ART/box-$D1.json"; D2F="$ART/box-$D2.json"; D3F="$ART/box-$D3.json"
R1=$(rejected "$(round "$SF" none forged forged)" forged)
R2=$(rejected "$(round "$SF" "$D1F" wrongindex wrongindex)" wrongindex)
R3=$(rejected "$(round none "$D1F" nostate nostate)" nostate)
R4=$(rejected "$(round "$SF" "$D1F" addinput addinput)" addinput)
R5=$(rejected "$(round "$PF" none valid notoken)" notoken)
C1=no; R6=n/a; C2=no; G1=n/a; G2=n/a; R7=n/a; R8=n/a; R9=n/a; C3=no; C4=no; G3=n/a
c=$(round "$SF" "$D1F" valid valid0)
if [[ "$c" == 200 ]]; then S1=$(grep -o 'out0_id=[0-9a-f]*' "$ART/spend_valid0.err" | cut -d= -f2); log "waiting for S1 $S1"
  if wait_box "$S1" 1200; then C1=yes; log "S1 in UTXO: $(python3 -c "import json; d=json.load(open('$ART/box-$S1.json')); print('creationHeight', d['creationHeight'], 'R4', d['additionalRegisters'].get('R4'), 'assets', d['assets'])")"
    gone "$D1" && G1=yes || G1=no; log "D1 spent: $G1"
    R6=$(rejected "$(round "$ART/box-$S1.json" none staleleaf staleleaf)" staleleaf)
    c=$(round "$ART/box-$S1.json" "$D2F" valid skip 3)
    if [[ "$c" == 200 ]]; then S2=$(grep -o 'out0_id=[0-9a-f]*' "$ART/spend_skip.err" | cut -d= -f2); log "waiting for S2 $S2 (leaf 3 used; R4 should read 4)"
      if wait_box "$S2" 1200; then C2=yes; log "S2 in UTXO: $(python3 -c "import json; d=json.load(open('$ART/box-$S2.json')); print('creationHeight', d['creationHeight'], 'R4', d['additionalRegisters'].get('R4'), 'assets', d['assets'])")"; gone "$D2" && G2=yes || G2=no; log "D2 spent: $G2"
        S2F="$ART/box-$S2.json"
        R7=$(rejected "$(round "$S2F" none overindex overindex)" overindex)
        R8=$(rejected "$(round "$S2F" none lastsame lastsame 15)" lastsame)
        R9=$(rejected "$(round "$S2F" none lastdeposit lastdeposit 15)" lastdeposit)
        c=$(round "$S2F" none rotate rotate 15)
        if [[ "$c" == 200 ]]; then S3=$(grep -o 'out0_id=[0-9a-f]*' "$ART/spend_rotate.err" | cut -d= -f2); log "waiting for S3 $S3 (key set B's singleton, index 0)"
          if wait_box "$S3" 1200; then C3=yes; log "S3 in UTXO: $(python3 -c "import json; d=json.load(open('$ART/box-$S3.json')); print('creationHeight', d['creationHeight'], 'R4', d['additionalRegisters'].get('R4'), 'assets', d['assets'], 'tree_is_B', d['ergoTree'] == open('$KEYSB/state-tree.hex').read().strip())")"
            c=$(KEYS_DIR="$KEYSB" round "$ART/box-$S3.json" "$D3F" valid after)
            if [[ "$c" == 200 ]]; then S4=$(grep -o 'out0_id=[0-9a-f]*' "$ART/spend_after.err" | cut -d= -f2); log "waiting for S4 $S4"
              if wait_box "$S4" 1200; then C4=yes; log "S4 in UTXO: $(python3 -c "import json; d=json.load(open('$ART/box-$S4.json')); print('creationHeight', d['creationHeight'], 'R4', d['additionalRegisters'].get('R4'), 'assets', d['assets'])")"; gone "$D3" && G3=yes || G3=no; log "D3 spent by key set B: $G3"; fi
            fi
          fi
        fi
      fi
    fi
  fi
fi
log "TESTNET-SINGLETON: forged_rejected=$R1 wrongindex_rejected=$R2 nostate_rejected=$R3 addinput_rejected=$R4 notoken_rejected=$R5 valid0_confirmed=$C1 deposit1_spent=$G1 staleleaf_rejected=$R6 skip_leaf3_confirmed=$C2 deposit2_spent=$G2 overindex_rejected=$R7 lastleaf_same_script_rejected=$R8 lastleaf_to_deposit_rejected=$R9 rotate_confirmed=$C3 sweep_after_rotation_confirmed=$C4 deposit3_spent=$G3"
