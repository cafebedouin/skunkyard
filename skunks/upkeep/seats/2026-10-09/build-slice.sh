#!/usr/bin/env bash
# Build a public-only review slice from a PR worktree: build-slice.sh <worktree> <base> <head> <pr-text> <slice> [extra-context-files...]
set -euo pipefail
repo="$1"; base="$2"; head="$3"; prtext="$4"; slice="$5"; shift 5
rm -rf "$slice"; mkdir -p "$slice/new" "$slice/context"; cd "$repo"
git diff "$base".."$head" -- . ':!project/target' > "$slice/diff.patch"
cp "$prtext" "$slice/PR-DESCRIPTION.md"
git diff --name-only "$base".."$head" -- . ':!project/target' | while read -r f; do
  mkdir -p "$slice/new/$(dirname "$f")"; git show "$head:$f" > "$slice/new/$f"; done
for f in app/transactions/rent/StorageRentSource.scala app/transactions/rent/StorageRent.scala app/transactions/rent/RentVerifier.scala \
  app/transactions/candidate/CandidatePreparation.scala app/transactions/candidate/BlockTxMessages.scala \
  app/transactions/candidate/CandidateBundle.scala app/transactions/candidate/CandidateCapital.scala app/transactions/candidate/CapitalEntry.scala \
  app/mining/CandidateBuilder.scala app/configs/CandidateSourceConfig.scala app/configs/CandidateConfig.scala app/tasks/StartMiningServer.scala \
  lithos-lib/src/main/scala/node/NodeApi.scala lithos-lib/src/main/scala/mutations/Contract.scala lithos-lib/src/main/scala/mutations/TxBuilder.scala \
  lithos-lib/src/main/scala/mutations/UTXO.scala lithos-lib/src/main/scala/mutations/InputUTXO.scala lithos-lib/src/main/scala/mutations/Mutator.scala \
  lithos-lib/src/main/scala/lfsm/ScriptGenerator.scala test/support/FakeNodeContext.scala test/support/CanonicalNodeBox.scala \
  test/contracts/specs/harness/ContractSpecBase.scala test/transactions/rent/StorageRentSourceSpec.scala "$@"; do
  [ -z "$f" ] && continue
  mkdir -p "$slice/context/$(dirname "$f")"; git show "$base:$f" > "$slice/context/$f" 2>/dev/null || git show "$head:$f" > "$slice/context/$f"; done
cat > "$slice/README-SLICE.md" <<R
This directory is a review slice of one pull request to Lithos-Client (https://github.com/Lithos-Protocol/Lithos-Client,
Scala 2.12 / Play / Akka, an Ergo mining-pool client whose miners build their own block candidates).

- PR-DESCRIPTION.md : the pull request text as the maintainers will read it
- diff.patch        : the whole change against its base commit $base
- new/              : full copies of every file the PR adds or changes, at the PR head
- context/          : unchanged files the PR builds on, at the base (the storage-rent source it mirrors, the candidate
                      protocol, the node API wrapper, the transaction-building library, test support)
R
find "$slice" -type f | sort > "$slice/MANIFEST.txt"; wc -l "$slice/diff.patch"; wc -l < "$slice/MANIFEST.txt"
