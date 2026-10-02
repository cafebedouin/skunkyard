# interactive: oneshot step 3, a devnet the page can be clicked through against (rig hook; topology oneshot-v4.json).
# Start it with interactive-run.sh, which also runs scripts/devnet-proxy.mjs on the HOST: this hook runs inside the
# rig's own network namespace, so a TCP listener started here would not be reachable from the host or from Windows.
# The hook: waits for block version 4 and A's matured balance; derives a oneshot address from ONESHOT_SEED (or a
# fresh seed it prints); funds it with a plain /wallet/payment/send (no registers); bridges A's REST API to the unix
# socket /tmp/oneshot-A.sock (socat inside A's namespace, or scripts/socket-bridge.mjs when socat is missing; a
# filesystem socket is not tied to a network namespace, so the host proxy can reach it); prints the proxy URL, the
# address, the seed, A's wallet address and ONESHOT-INTERACTIVE: READY; writes the same to /tmp/oneshot-interactive.txt;
# then keeps the network up until /tmp/oneshot-stop exists or ONESHOT_MINUTES (60) pass, polling every 5 s and printing
# the height every minute. On exit it stops the bridge and removes the socket.
# Env: ONESHOT_SEED, ONESHOT_FUND (1 ERG), ONESHOT_MINUTES (60), ONESHOT_PROXY (http://127.0.0.1:9099).
FUND=${ONESHOT_FUND:-1000000000}; MINUTES=${ONESHOT_MINUTES:-60}; PROXY=${ONESHOT_PROXY:-http://127.0.0.1:9099}
SOCK=/tmp/oneshot-A.sock; STOP=/tmp/oneshot-stop; INFO=/tmp/oneshot-interactive.txt
DEVDIR="$(dirname "$RIG_HOOK")"; PKG="$(cd "$DEVDIR/.." && pwd)"; FLOW="$PKG/scripts/flow.mjs"
DELAY="${REWARD_DELAY:-720}"
rm -f "$STOP" "$INFO"

end=$((SECONDS + 300)); bv=""
while [[ $SECONDS -lt $end ]]; do bv=$(rest A /info | jq -r '.parameters.blockVersion // empty' 2>/dev/null); [[ "$bv" == 4 ]] && break; sleep 3; done
echo "[oi] blockVersion=$bv at height $(full_height A); minerRewardDelay=$DELAY"
[[ "$bv" == 4 ]] || { echo "[oi] FAIL: block version 4 did not activate"; rig_verdict=FAIL; }

if [[ "${rig_verdict:-}" != FAIL ]]; then
  SEED="${ONESHOT_SEED:-$(node "$FLOW" --generate | awk '$1 == "seed" {print $2}')}"
  P2S=$(node "$FLOW" --seed "$SEED" --address)
  bal=$(wait_balance A $((FUND * 3)) 300) || { echo "[oi] FAIL: A balance $bal"; rig_verdict=FAIL; }
  ADDR_A=""; end=$((SECONDS + 60)); while [[ -z "$ADDR_A" && $SECONDS -lt $end ]]; do ADDR_A=$(address A 2>/dev/null); [[ -n "$ADDR_A" ]] || sleep 2; done
  [[ -n "$ADDR_A" ]] || { echo "[oi] FAIL: no wallet address for A"; rig_verdict=FAIL; }
fi
if [[ "${rig_verdict:-}" != FAIL ]]; then
  fund=$(wallet A /wallet/payment/send "[{\"address\":\"$P2S\",\"value\":$FUND}]" | jq -r 'if type == "string" then . else (.detail // .reason // tojson) end')
  echo "[oi] funding via /wallet/payment/send (no registers): $fund"
  [[ "$fund" =~ ^[0-9a-f]{64}$ ]] || { echo "[oi] FAIL: funding rejected"; rig_verdict=FAIL; }
fi
if [[ "${rig_verdict:-}" != FAIL ]]; then
  rm -f "$SOCK"
  if command -v socat >/dev/null; then
    ip netns exec "${NS[A]}" socat "UNIX-LISTEN:$SOCK,fork,unlink-early" "TCP:127.0.0.1:${REST[A]}" & BRIDGE=$!; BRIDGE_KIND=socat
  else
    echo "[oi] socat is not installed: using scripts/socket-bridge.mjs inside A's namespace"
    ip netns exec "${NS[A]}" node "$PKG/scripts/socket-bridge.mjs" "$SOCK" "${REST[A]}" & BRIDGE=$!; BRIDGE_KIND=node
  fi
  end=$((SECONDS + 20)); while [[ ! -S "$SOCK" && $SECONDS -lt $end ]]; do sleep 1; done
  [[ -S "$SOCK" ]] || { echo "[oi] FAIL: socket $SOCK did not appear"; rig_verdict=FAIL; }
  echo "[oi] bridge ($BRIDGE_KIND, pid $BRIDGE): unix:$SOCK -> A 127.0.0.1:${REST[A]}; through the socket /info fullHeight: $(curl -s --max-time 5 --unix-socket "$SOCK" http://localhost/info | jq -r .fullHeight)"
  # wait for the funding block (extra index), so the page finds the box at once
  end=$((SECONDS + 120)); fh=""
  while [[ -z "$fh" && $SECONDS -lt $end ]]; do fh=$(rest A "/blockchain/transaction/byId/$fund" | jq -r '.inclusionHeight // empty' 2>/dev/null); [[ -n "$fh" ]] || sleep 1; done
  echo "[oi] funding tx confirmed at height ${fh:-(not within 120 s)}"
fi
if [[ "${rig_verdict:-}" != FAIL ]]; then
  {
    echo "proxy $PROXY"
    echo "mode node"
    echo "fee_delay $DELAY"
    echo "seed $SEED"
    echo "address $P2S"
    echo "destination $ADDR_A"
  } > "$INFO"
  echo "[oi] proxy URL (API base, node mode): $PROXY   (scripts/devnet-proxy.mjs on the host, started by interactive-run.sh)"
  echo "[oi] miner-fee contract delay for the page: $DELAY"
  echo "[oi] oneshot seed: $SEED"
  echo "[oi] oneshot address (funded, $FUND nanoERG): $P2S"
  echo "[oi] A's wallet address (destination): $ADDR_A"
  echo "[oi] stop: touch $STOP (or wait $MINUTES minutes)"
  echo "ONESHOT-INTERACTIVE: READY"
  t0=$SECONDS; last=-1
  while [[ ! -e "$STOP" && $((SECONDS - t0)) -lt $((MINUTES * 60)) ]]; do
    m=$(( (SECONDS - t0) / 60 )); [[ $m != "$last" ]] && { echo "[oi] minute $m: height $(full_height A), mempool $(mempool_size A)"; last=$m; }
    sleep 5
  done
  echo "[oi] stopping ($([[ -e "$STOP" ]] && echo "stop file" || echo "$MINUTES minutes elapsed")) at height $(full_height A)"
  rig_verdict=PASS
fi
[[ -n "${BRIDGE:-}" ]] && { kill "$BRIDGE" 2>/dev/null; pkill -f "UNIX-LISTEN:$SOCK" 2>/dev/null; pkill -f "socket-bridge.mjs $SOCK" 2>/dev/null; }
rm -f "$SOCK" "$STOP"
echo "ONESHOT-INTERACTIVE: ${rig_verdict:-FAIL} (stopped)"
