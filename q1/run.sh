#!/usr/bin/env bash
# Q1: full UTXO-set scan. Usage: bash q1/run.sh <ergo data dir>/state
# The node must be stopped. The state directory is copied and the copy is scanned,
# so the node's own database is never opened by this script.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${1:?usage: run.sh <path to .ergo/state>}"
NODE_JAR="${ERGO_JAR:-$HOME/bin/ergo-node/ergo-6.0.6.jar}"
JAR_SHA256="21b9023933b19b98b7eb4d50cb78bcb6c827a0fe65711a00ceaf1b83f8f3a323"
SCALA_VERSION="2.12.20"   # the scala-library version bundled in ergo-6.0.6.jar
OUT_DIR="$SCRIPT_DIR/out"
TARGET_DIR="$SCRIPT_DIR/target"
WORK_DIR="${Q1_WORK:-$SCRIPT_DIR/work}"

if command -v cs >/dev/null 2>&1; then CS=cs; elif [ -x "$HOME/.local/bin/cs" ]; then CS="$HOME/.local/bin/cs"; else
  echo "coursier (cs) not found" >&2; exit 1; fi

echo "$JAR_SHA256  $NODE_JAR" | sha256sum -c --quiet - >&2 || { echo "ergo jar hash mismatch" >&2; exit 1; }
if pgrep -f '^java .*ergo-6\.0\.6\.jar --mainnet' >/dev/null; then echo "the mainnet node (ergo-6.0.6.jar) is running; stop it first" >&2; exit 1; fi
[ -d "$STATE_DIR/ldb_main" ] && [ -d "$STATE_DIR/ldb_undo" ] || { echo "not a state dir: $STATE_DIR" >&2; exit 1; }

mkdir -p "$TARGET_DIR" "$OUT_DIR"
if [ ! -f "$TARGET_DIR/q1/Scan.class" ] || [ "$SCRIPT_DIR/Scan.scala" -nt "$TARGET_DIR/q1/Scan.class" ]; then
  "$CS" launch "scalac:${SCALA_VERSION}" -- -nowarn -cp "$NODE_JAR" -d "$TARGET_DIR" "$SCRIPT_DIR/Scan.scala" >&2
fi

t0=$(date +%s)
rm -rf "$WORK_DIR"; mkdir -p "$WORK_DIR"
cp -a "$STATE_DIR/." "$WORK_DIR/state/"
rm -f "$WORK_DIR/state/ldb_main/LOCK" "$WORK_DIR/state/ldb_undo/LOCK"   # copy only; originals untouched

copied=$(date +%s)
echo "copy of $STATE_DIR done" >&2
start=$(date +%s)
cd "$WORK_DIR"   # the node's logback config writes ergo.log to the working directory; keep it in the work dir
java -Xmx4g -Xss64m -cp "$TARGET_DIR:$NODE_JAR" q1.Scan "$WORK_DIR/state" "$OUT_DIR" "$SCRIPT_DIR/scan.conf"
end=$(date +%s)
echo "wall-clock seconds: copy $((copied - t0)), scan $((end - start))" >&2
rm -rf "$WORK_DIR"
