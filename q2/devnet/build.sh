#!/usr/bin/env bash
# build.sh: compile q2/devnet/Spend.scala together with q2/Runner6.scala against the pinned sigma-state 6.0.7
# classpath (the same coordinates as q2/run.sh), into q2/devnet/target; writes the classpath to target/cp.txt.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../.." && pwd)"
if command -v cs >/dev/null 2>&1; then CS=cs; elif [ -x "$HOME/.local/bin/cs" ]; then CS="$HOME/.local/bin/cs"; else echo "coursier (cs) not found" >&2; exit 1; fi
SCALA_VERSION=2.12.18; SIGMA_VERSION=6.0.7; SLF4J_VERSION=1.7.36
T="$DIR/target"; mkdir -p "$T"
CP=$("$CS" fetch --classpath "org.scala-lang:scala-library:${SCALA_VERSION}" \
  "org.scorexfoundation:sigma-state_2.12:${SIGMA_VERSION}" "org.slf4j:slf4j-nop:${SLF4J_VERSION}" 2>/dev/null)
"$CS" launch "scalac:${SCALA_VERSION}" -- -cp "$CP" -d "$T" "$ROOT/q2/Runner6.scala" "$DIR/Spend.scala"
printf '%s:%s\n' "$T" "$CP" > "$T/cp.txt"
echo "built $T (sigma-state $SIGMA_VERSION, scalac $SCALA_VERSION)"
