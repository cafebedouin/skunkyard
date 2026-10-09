#!/usr/bin/env bash
# Build the public-only review slice for the upkeep PR from the lithos-upkeep clone at HEAD.
set -euo pipefail
repo=~/bin/lithos-upkeep; slice="$1"; rm -rf "$slice"; mkdir -p "$slice/new" "$slice/context"
cd "$repo"
base=da4a4666
git diff "$base"..HEAD -- . ':!CLAUDE.md' ':!UPKEEP-BRIEF.md' ':!prompts' ':!project/target' > "$slice/diff.patch"
cp prompts/PR-DESCRIPTION.md "$slice/PR-DESCRIPTION.md"
# full copies of every file the PR adds or changes
git diff --name-only "$base"..HEAD -- . ':!CLAUDE.md' ':!UPKEEP-BRIEF.md' ':!prompts' ':!project/target' | while read -r f; do
  mkdir -p "$slice/new/$(dirname "$f")"; cp "$f" "$slice/new/$f"; done
# the existing code the PR builds on, unchanged, for context
for f in app/transactions/rent/StorageRentSource.scala app/transactions/rent/StorageRent.scala app/transactions/rent/RentVerifier.scala \
  app/transactions/candidate/CandidatePreparation.scala app/transactions/candidate/BlockTxMessages.scala \
  app/transactions/candidate/CandidateBundle.scala app/transactions/candidate/CandidateCapital.scala app/transactions/candidate/CapitalEntry.scala \
  app/mining/CandidateBuilder.scala app/configs/CandidateSourceConfig.scala app/configs/CandidateConfig.scala \
  lithos-lib/src/main/scala/node/NodeApi.scala lithos-lib/src/main/scala/mutations/Contract.scala lithos-lib/src/main/scala/mutations/TxBuilder.scala \
  lithos-lib/src/main/scala/mutations/UTXO.scala lithos-lib/src/main/scala/mutations/InputUTXO.scala lithos-lib/src/main/scala/mutations/Mutator.scala \
  lithos-lib/src/main/scala/lfsm/ScriptGenerator.scala test/support/FakeNodeContext.scala test/support/CanonicalNodeBox.scala \
  test/contracts/specs/harness/ContractSpecBase.scala test/transactions/rent/StorageRentSourceSpec.scala; do
  mkdir -p "$slice/context/$(dirname "$f")"; cp "$f" "$slice/context/$f"; done
cat > "$slice/README-SLICE.md" <<'R'
This directory is a review slice of one pull request to Lithos-Client (https://github.com/Lithos-Protocol/Lithos-Client,
Scala 2.12 / Play / Akka, an Ergo mining-pool client whose miners build their own block candidates).

- PR-DESCRIPTION.md : the pull request text as the maintainers will read it
- diff.patch        : the whole change against upstream master da4a4666
- new/              : full copies of every file the PR adds or changes, at the PR head
- context/          : unchanged existing files the PR builds on (the storage-rent source it mirrors, the candidate
                      protocol, the node API wrapper, the transaction-building library, test support)
R
find "$slice" -type f | sort > "$slice/MANIFEST.txt"; wc -l "$slice/diff.patch"; wc -l < "$slice/MANIFEST.txt"
