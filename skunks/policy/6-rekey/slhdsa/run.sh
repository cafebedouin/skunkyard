#!/usr/bin/env bash
# SK-053 step 3: build and run the SLH-DSA-SHA2-128s verifier stages (no node). From the repository root:
#   bash skunks/policy/6-rekey/slhdsa/run.sh            # all stages, results.json
#   bash skunks/policy/6-rekey/slhdsa/run.sh stage 3    # one harness command
#
# Classpath: sigma-state_2.12 6.0.7 (the q2 pin) ahead of a jar that supplies its dependencies and BouncyCastle
# with SLH-DSA. With coursier (`cs`) reachable this is fetched as q2/run.sh does; the cloud session of 2026-10-10
# could not run coursier through its proxy (README.md, "Environment") and used the Ergo 6.0.7 node jar for the
# dependencies instead, with the pinned sigma-state jar first. Set SLHDSA_CP (sigma + deps + BC) and SCALAC_CP
# (scala-compiler, scala-reflect, scala-library, scala-xml) to override.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
cd "$ROOT_DIR"

SCALA_VERSION="2.12.18"
if [ -z "${SLHDSA_CP:-}" ]; then
  CS="${CS:-cs}"
  SLHDSA_CP=$("$CS" fetch --classpath "org.scala-lang:scala-library:${SCALA_VERSION}" \
    "org.scorexfoundation:sigma-state_2.12:6.0.7" "org.slf4j:slf4j-nop:1.7.36" "org.bouncycastle:bcprov-jdk18on:1.86")
fi
if [ -z "${SCALAC_CP:-}" ]; then
  SCALAC_CP=$("${CS:-cs}" fetch --classpath "org.scala-lang:scala-compiler:${SCALA_VERSION}")
fi

TARGET="$SCRIPT_DIR/target"
mkdir -p "$TARGET"
if [ ! -f "$TARGET/slhdsa/SlhDsaRunner.class" ] || [ "$SCRIPT_DIR/SlhDsaRunner.scala" -nt "$TARGET/slhdsa/SlhDsaRunner.class" ]; then
  java -cp "$SCALAC_CP" scala.tools.nsc.Main -cp "$SLHDSA_CP" -d "$TARGET" "$SCRIPT_DIR/SlhDsaRunner.scala"
fi
run() { java -cp "$TARGET:$SLHDSA_CP" slhdsa.SlhDsaRunner "$@"; }

if [ $# -gt 0 ]; then run "$@"; exit; fi

LOG="$SCRIPT_DIR/run.log"
{
  echo "# $(date -u +%Y-%m-%dT%H:%M:%SZ) sigma-state 6.0.7 (pinned jar first on the classpath)"
  run pin
  [ -f "$SCRIPT_DIR/vectors.json" ] || run gen
  python3 -I "$SCRIPT_DIR/slhdsa_ref.py" "$SCRIPT_DIR/vectors.json" --write
  for n in 2 3 4 5 6; do run stage "$n"; done
  run full
  echo "# the reference on the spend the full verifier checked (hash-call counts for the hashing share):"
  python3 -I "$SCRIPT_DIR/slhdsa_ref.py" "$SCRIPT_DIR/vectors-spend.json"
  echo "# the reference on every measured spend: chain steps against cost, and the worst case by linear fit:"
  python3 -I "$SCRIPT_DIR/slhdsa_ref.py" "$SCRIPT_DIR/spends.json"
} 2>&1 | grep -v "Picked up JAVA_TOOL_OPTIONS" | tee "$LOG"
python3 -I - "$LOG" "$SCRIPT_DIR/results.json" <<'EOF'
import json, sys
rows = [json.loads(l[len("RESULT "):]) for l in open(sys.argv[1]) if l.startswith("RESULT ")]
json.dump({"experiment": "6-rekey-slhdsa", "stages": rows}, open(sys.argv[2], "w"), indent=1)
print(f"results {sys.argv[2]}: {len(rows)} stage rows")
EOF
