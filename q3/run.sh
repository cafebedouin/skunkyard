#!/usr/bin/env bash
# Q3: spends per P2PK key over a COPY of the node's history store (q3/work/history; the node may keep running).
# usage: bash q3/run.sh [maxHeight]
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; NODE_JAR="${ERGO_JAR:-$HOME/bin/ergo-node/ergo-6.0.6.jar}"
SCALA_VERSION=2.12.20; T="$D/target"; OUT="$D/out"; mkdir -p "$T" "$OUT"
CS=$(command -v cs || echo "$HOME/.local/bin/cs")
if [ ! -f "$T/q3/SpendsPerKey.class" ] || [ "$D/SpendsPerKey.scala" -nt "$T/q3/SpendsPerKey.class" ]; then
  "$CS" launch "scalac:${SCALA_VERSION}" -- -nowarn -cp "$NODE_JAR" -d "$T" "$D/SpendsPerKey.scala" >&2
fi
[ -d "$D/work/history/objects" ] || { echo "no copy at $D/work/history (copy the node's .ergo/history there while the node is stopped)" >&2; exit 1; }
java -Xmx1500m -cp "$T:$NODE_JAR" q3.SpendsPerKey "$D/work/history" "$OUT" "${1:-2147483647}" 2>&1 | tee "$OUT/run-$(date -u +%Y%m%dT%H%M%SZ).txt"
