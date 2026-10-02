#!/usr/bin/env bash
# gen.sh: regenerate the WOTS test vectors for skunks/oneshot/src/wots.ts from the Scala harness.
# Builds q2/devnet (q2/devnet/build.sh: Runner6.scala + Spend.scala, sigma-state 6.0.7, scalac 2.12.18), compiles
# q2/devnet/Vectors.scala against the classpath it writes (target/cp.txt), and writes one JSON file per (n, w).
# No node is needed. Usage: bash skunks/oneshot/vectors/gen.sh [seedHex32]
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../../.." && pwd)"
SEED="${1:-000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f}"
if command -v cs >/dev/null 2>&1; then CS=cs; elif [ -x "$HOME/.local/bin/cs" ]; then CS="$HOME/.local/bin/cs"; else echo "coursier (cs) not found" >&2; exit 1; fi
bash "$ROOT/q2/devnet/build.sh" >&2
CP="$(cat "$ROOT/q2/devnet/target/cp.txt")"
VT="$ROOT/q2/devnet/target/vectors"; mkdir -p "$VT"
"$CS" launch "scalac:2.12.18" -- -cp "$CP" -d "$VT" "$ROOT/q2/devnet/Vectors.scala"
cd "$ROOT"   # Runner6 reads q2/wots-constant.es by relative path
for nw in "32 16" "32 4" "32 256" "16 16" "16 4" "16 256"; do
  set -- $nw
  java -cp "$VT:$CP" q2.Vectors vectors "$SEED" "$1" "$2" > "$DIR/wots-n$1-w$2.json"
  echo "wrote skunks/oneshot/vectors/wots-n$1-w$2.json" >&2
done
