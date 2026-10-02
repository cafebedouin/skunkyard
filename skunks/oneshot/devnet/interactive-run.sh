#!/usr/bin/env bash
# interactive-run.sh: start the interactive oneshot devnet (interactive.sh) under peeryard's lock, with the CORS proxy
# (scripts/devnet-proxy.mjs) on the host at 127.0.0.1:9099. Stop with: touch /tmp/oneshot-stop
# Env: PEERYARD (default /home/scott/bin/peeryard), PEERYARD_JAR (default /home/scott/bin/ergo-node/ergo-6.0.6.jar),
# and the hook's ONESHOT_SEED, ONESHOT_FUND, ONESHOT_MINUTES.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; PKG="$(cd "$HERE/.." && pwd)"
PEERYARD="${PEERYARD:-/home/scott/bin/peeryard}"
export PEERYARD_JAR="${PEERYARD_JAR:-/home/scott/bin/ergo-node/ergo-6.0.6.jar}"
node "$PKG/scripts/devnet-proxy.mjs" --port 9099 --socket /tmp/oneshot-A.sock & PROXY=$!
cd "$PEERYARD" && bash rig/preflight.sh | tail -1 \
  && bash review/with-lock.sh -- bash rig/rig.sh "$HERE/oneshot-v4.json" "$HERE/interactive.sh"; rc=$?
kill "$PROXY" 2>/dev/null; wait "$PROXY" 2>/dev/null
echo "[interactive-run] proxy stopped; exit $rc"
exit $rc
