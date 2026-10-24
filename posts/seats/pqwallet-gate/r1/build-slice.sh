#!/usr/bin/env bash
# build-slice.sh <slice-dir>: the pqwallet assurance-gate slice (round 1), public material only, copied from the repo.
set -euo pipefail
S="$1"; R="$(cd "$(dirname "$0")/../../../.." && pwd)"; HERE="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$S"; mkdir -p "$S/slhdsa" "$S/wotsplus" "$S/pqwallet/diff"
cp "$HERE/README-SLICE.md" "$S/"
find "$R/skunks/policy/6-rekey/slhdsa" -maxdepth 1 -type f -exec cp {} "$S/slhdsa/" \;
cp "$R"/skunks/policy/6-rekey/{WotsPlus.es,results-wotsplus.json,results-wotsplus-fit.json,SCHEME-SIZING.md} "$S/wotsplus/"
cp "$R"/skunks/qvault/{QVault.es,QDay.es,README.md,devnet-results.json} "$S/wotsplus/"
for d in src test scripts vectors; do cp -r "$R/skunks/pqwallet/$d" "$S/pqwallet/"; done
cp "$R"/skunks/pqwallet/{CHARTER.md,DERIVATION.md,RESULT.md,package.json} "$S/pqwallet/"
find "$R/skunks/pqwallet/diff" -maxdepth 1 -type f ! -name 'grind-sigs.json' -exec cp {} "$S/pqwallet/diff/" \;
echo "slice at $S: $(find "$S" -type f | wc -l) files, $(du -sh "$S" | cut -f1)"
