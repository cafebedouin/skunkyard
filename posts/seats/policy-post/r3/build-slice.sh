#!/usr/bin/env bash
# build-slice.sh <slice-dir>: the round-three slice for the policy-post seats, copied from the repository.
# The slice is public material only: no CLAUDE.md, no prompts/, no private attack harnesses. The explorer JSONs
# come from round one's slice (fetched 2026-10-10) if present, else from the explorer.
set -euo pipefail
S="$1"; R="$(cd "$(dirname "$0")/../../../.." && pwd)"; R2="$R/posts/seats/policy-post/r3"
rm -rf "$S"; mkdir -p "$S/evidence"; E="$S/evidence"
cp "$R/posts/2026-10-policy-vaults-forum-draft.md" "$S/POST-DRAFT.md"
cp "$R2/README-SLICE.md" "$S/README-SLICE.md"
awk '/^# Round 2: seven seats/{f=1} f' "$R/posts/seats/policy-post/REVIEW.md" > "$S/REVIEW-ROUND2.md"
cp "$R2/../r2/template-hash.out" "$S/evidence/template-hash.out"
# keepalive
mkdir -p "$E/keepalive/tx"
cp "$R"/skunks/keepalive/{KeepAlive.es,KeepAliveAddress.es,README.md,address-results.json,devnet-results.json,kaa-mainnet-wallet.tree,kaa-mainnet-wallet.address,ka-mainnet.tree,mainnet-demo.py,devnet-test-address.py} "$E/keepalive/"
cp "$R"/skunks/keepalive/tx/*.json "$E/keepalive/tx/"
# qvault
mkdir -p "$E/qvault"; cp "$R"/skunks/qvault/{QDay.es,QVault.es,README.md,devnet-results.json,devnet-test.py} "$E/qvault/"
# policy experiments
for d in 1-template 2-twostep 3-extension 4-inherit 5-canary 7-cheque-bank; do
  mkdir -p "$E/policy/$d"
  find "$R/skunks/policy/$d" -maxdepth 1 -type f \( -name '*.es' -o -name 'README.md' -o -name 'results*.json' -o -name '*.tree' \) -exec cp {} "$E/policy/$d/" \;
done
mkdir -p "$E/policy/2-twostep/mainnet/tx"
cp "$R/skunks/policy/2-twostep/mainnet/README.md" "$E/policy/2-twostep/mainnet/"
cp "$R"/skunks/policy/2-twostep/mainnet/tx/*.json "$E/policy/2-twostep/mainnet/tx/"
cp "$R"/skunks/policy/2-twostep/devnet-test.py "$R"/skunks/policy/2-twostep/devnet-test-cancel2.py "$E/policy/2-twostep/"
# 6-rekey whole, slhdsa without the build dir
mkdir -p "$E/policy/6-rekey/slhdsa"
find "$R/skunks/policy/6-rekey" -maxdepth 1 -type f -exec cp {} "$E/policy/6-rekey/" \;
find "$R/skunks/policy/6-rekey/slhdsa" -maxdepth 1 -type f -exec cp {} "$E/policy/6-rekey/slhdsa/" \;
cp "$R/skunks/policy/probe-sign-height.json" "$R/skunks/policy/probe-sign-height.py" "$E/policy/"
cp "$R/research/policy/EXPERIMENTS.md" "$R/research/policy/evidence/ergo-capabilities.md" "$E/policy/"
# oneshot signers
mkdir -p "$E/oneshot"; cp "$R/skunks/oneshot/SIGNERS.md" "$R"/skunks/oneshot/scripts/{mainnet-sign.mjs,mainnet-sign-cancel.mts,twostep-trees.mjs} "$E/oneshot/"
# research
mkdir -p "$E/research"
awk '/^## Update 2026-10-10/{f=1} f' "$R/research/pq/ROADMAP.md" > "$E/research/ROADMAP-update.md"
cp "$R/q2/RESULT.md" "$E/research/q2-RESULT.md"; cp "$R/research/lattice/RESULT.md" "$E/research/lattice-RESULT.md"
# mainnet explorer JSONs
mkdir -p "$E/mainnet-tx"
OLD="${OLD_SLICE:-}"
if [[ -n $OLD && -d $OLD/evidence/mainnet-tx ]]; then cp "$OLD"/evidence/mainnet-tx/*.json "$E/mainnet-tx/"; else
  for id in 8ab9fe8f525a934c3a4c0e9803581153b4d8d21e678defb32d2e50958e947941 92386e998c6cbafc7da31aafc244bed08b7f5414417c5ac502382c92416f6546 6e1c55f9fbf41f7bc93579d221e9be1225a61749c1e161eda46f713dc9dc6f26 029fc1e8f901cd98a88f27c629d3bf0f6e8e1581ae94a3a29a7fbaeece11acd8 7e20f56920cd0e5b5880438c892964b42a5ccc15c5be0ec600ac4a82f1c187e0 5f4c29d28a752f7d5ec73c722878c5eba3bdd767909600eb99ddd840cfaefa5f 1304806181bb3c6d0bf389bc5a2536ec07f321b32a2fb7a8c04add7c7b5a8875 b25c7550a6a36f7ee887c03089ff825769afe7b3c39872eb3f39a94eca3e6be1; do
    curl -sS "https://api.ergoplatform.com/api/v1/transactions/$id" -o "$E/mainnet-tx/$id.json"; done
fi
# leak check: nothing from the apparatus, nothing private
! find "$S" \( -name CLAUDE.md -o -name 'issues.json' -o -path '*prompts*' -o -name '*.pyc' -o -name '__pycache__' \) | grep . 
! grep -rl "skunkyard-private/policy-attacks/[^ ]*\.py" "$S" >/dev/null 2>&1 || true
find "$S" -type f | wc -l; du -sh "$S"
