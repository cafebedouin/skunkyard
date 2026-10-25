#!/usr/bin/env bash
# build-slice.sh <slice-dir>: the derivation-post review slice (round 1), public material only, outside the repo.
# The thread's opening post is fetched from the forum's raw endpoint so the seats see what the reply answers.
set -euo pipefail
S="$1"; R="$(cd "$(dirname "$0")/../../../.." && pwd)"
rm -rf "$S"; mkdir -p "$S/pqwallet/testnet" "$S/thread"
cp "$R/posts/2026-10-derivation-reply-draft.md" "$S/DRAFT.md"
curl -s -m 30 -L "https://www.ergoforum.org/raw/5371" -o "$S/thread/5371-opening-post.md"
for d in src test vectors; do cp -r "$R/skunks/pqwallet/$d" "$S/pqwallet/"; done
cp "$R"/skunks/pqwallet/{CHARTER.md,DERIVATION.md,RESULT.md,package.json} "$S/pqwallet/"
cp "$R/skunks/pqwallet/testnet/RESULT-testnet.md" "$S/pqwallet/testnet/"
cp "$R/skunks/pqwallet/scripts/wotsplus_ref.py" "$S/pqwallet/"
rm -rf "$S/pqwallet/src/node_modules"
echo "slice at $S: $(find "$S" -type f | wc -l) files, $(du -sh "$S" | cut -f1)"
