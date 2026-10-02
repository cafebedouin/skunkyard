#!/usr/bin/env bash
# Measure the compact-verifier formulations (6.0.x only). Runs q2/run.sh 6.0.x's pins; compiles Runner6 first.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"
CS="$(command -v cs || echo "$HOME/.local/bin/cs")"
CP=$("$CS" fetch --classpath \
  "org.scala-lang:scala-library:2.12.18" \
  "org.scorexfoundation:sigma-state_2.12:6.0.7" \
  "org.slf4j:slf4j-nop:1.7.36" 2>/dev/null)
TARGET_DIR="q2/target/compact-variants"
mkdir -p "$TARGET_DIR"
"$CS" launch "scalac:2.12.18" -- -cp "$CP" -d "$TARGET_DIR" q2/Runner6.scala q2/compact-variants/Variants.scala 2>/dev/null
java -cp "$TARGET_DIR:$CP" q2v.Variants q2/compact-variants/fold.es q2/compact-variants/map-flatmap.es q2/compact-variants/map-fold.es q2/wots-compact.es

# The same scripts through the 5.0.2 compiler (compile only).
CP5=$("$CS" fetch --classpath \
  "org.scala-lang:scala-library:2.12.18" \
  "org.scorexfoundation:sigma-state_2.12:5.0.2" \
  "org.slf4j:slf4j-nop:1.7.36" 2>/dev/null)
TARGET5="q2/target/compact-variants-5.0.2"
mkdir -p "$TARGET5"
"$CS" launch "scalac:2.12.18" -- -cp "$CP5" -d "$TARGET5" q2/compact-variants/Compile5.scala 2>/dev/null
java -cp "$TARGET5:$CP5" q2v5.Compile5 q2/compact-variants/fold.es q2/compact-variants/map-flatmap.es q2/compact-variants/map-fold.es q2/wots-compact.es
