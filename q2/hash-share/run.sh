#!/usr/bin/env bash
# Hashing versus interpretation in q2/wots-constant.es (6.0.x only). Pins of q2/run.sh 6.0.x; compiles Runner6 first.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"
CS="$(command -v cs || echo "$HOME/.local/bin/cs")"
CP=$("$CS" fetch --classpath \
  "org.scala-lang:scala-library:2.12.18" \
  "org.scorexfoundation:sigma-state_2.12:6.0.7" \
  "org.slf4j:slf4j-nop:1.7.36" 2>/dev/null)
TARGET_DIR="q2/target/hash-share"
mkdir -p "$TARGET_DIR"
"$CS" launch "scalac:2.12.18" -- -cp "$CP" -d "$TARGET_DIR" q2/Runner6.scala q2/hash-share/HashShare.scala
java -cp "$TARGET_DIR:$CP" q2h.HashShare
