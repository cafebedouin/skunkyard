#!/usr/bin/env bash
# C1 unit test: compiles Scan.scala + C1Test.scala against the pinned node jar and runs the synthetic-tree cases.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_JAR="${ERGO_JAR:-$HOME/bin/ergo-node/ergo-6.0.6.jar}"
JAR_SHA256="21b9023933b19b98b7eb4d50cb78bcb6c827a0fe65711a00ceaf1b83f8f3a323"
if command -v cs >/dev/null 2>&1; then CS=cs; elif [ -x "$HOME/.local/bin/cs" ]; then CS="$HOME/.local/bin/cs"; else
  echo "coursier (cs) not found" >&2; exit 1; fi
echo "$JAR_SHA256  $NODE_JAR" | sha256sum -c --quiet - >&2 || { echo "ergo jar hash mismatch" >&2; exit 1; }
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
"$CS" launch "scalac:2.12.20" -- -nowarn -cp "$NODE_JAR" -d "$T" "$SCRIPT_DIR/Scan.scala" "$SCRIPT_DIR/C1Test.scala" >&2
cd "$T" && java -Xss64m -cp "$T:$NODE_JAR" q1.C1Test 2>/dev/null
