#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

# Locate coursier
if command -v cs >/dev/null 2>&1; then
  CS="cs"
elif [ -x "$HOME/.local/bin/cs" ]; then
  CS="$HOME/.local/bin/cs"
else
  echo "Error: coursier (cs) not found in PATH or ~/.local/bin/cs" >&2
  exit 1
fi

SCALA_VERSION="2.12.18"
SLF4J_VERSION="1.7.36"

VERSION="${1:-}"

if [ "$VERSION" = "5.0.2" ]; then
  SIGMA_VERSION="5.0.2"
  TARGET_DIR="$SCRIPT_DIR/target/5.0.2"
  mkdir -p "$TARGET_DIR"

  CP=$("$CS" fetch --classpath \
    "org.scala-lang:scala-library:${SCALA_VERSION}" \
    "org.scorexfoundation:sigma-state_2.12:${SIGMA_VERSION}" \
    "org.slf4j:slf4j-nop:${SLF4J_VERSION}" 2>/dev/null)

  if [ ! -f "$TARGET_DIR/q2/Runner.class" ] || [ "$SCRIPT_DIR/Runner.scala" -nt "$TARGET_DIR/q2/Runner.class" ]; then
    "$CS" launch "scalac:${SCALA_VERSION}" -- -cp "$CP" -d "$TARGET_DIR" "$SCRIPT_DIR/Runner.scala" 2>/dev/null
  fi

  java -cp "$TARGET_DIR:$CP" q2.Runner

elif [ "$VERSION" = "6.0.x" ] || [ "$VERSION" = "6.0.7" ] || [ "$VERSION" = "6.0" ]; then
  SIGMA_VERSION="6.0.7"
  TARGET_DIR="$SCRIPT_DIR/target/6.0.x"
  mkdir -p "$TARGET_DIR"

  CP=$("$CS" fetch --classpath \
    "org.scala-lang:scala-library:${SCALA_VERSION}" \
    "org.scorexfoundation:sigma-state_2.12:${SIGMA_VERSION}" \
    "org.slf4j:slf4j-nop:${SLF4J_VERSION}" 2>/dev/null)

  if [ ! -f "$TARGET_DIR/q2/Runner6.class" ] || [ "$SCRIPT_DIR/Runner6.scala" -nt "$TARGET_DIR/q2/Runner6.class" ]; then
    "$CS" launch "scalac:${SCALA_VERSION}" -- -cp "$CP" -d "$TARGET_DIR" "$SCRIPT_DIR/Runner6.scala" 2>/dev/null
  fi

  java -cp "$TARGET_DIR:$CP" q2.Runner6

else
  echo "Usage: $0 <5.0.2|6.0.x>" >&2
  exit 1
fi
