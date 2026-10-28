# The Rust side of the SLH-DSA-SHA2-128s conformance rig

A thin wrapper over RustCrypto's `slh-dsa` crate (pinned 0.2.0-rc.5) that reads and writes the files of the Scala
harness (`skunks/policy/6-rekey/slhdsa/SlhDsaRunner.scala`: `digests`, `verify-ext`, `acvp`, `negatives`) and the noble
scripts (`../scripts/kat.ts`, `diff-sign.ts`, `noble-verify.ts`), so the three implementations judge one another's
signatures on the rig's message convention. The run and its result: `../RESULT.md`, "The three-way agreement run
(2026-10-28)". Commands and file shapes: the header of `src/main.rs`.

```
cargo build --release
cd ../../..   # the repository root; paths below are relative to it
R=skunks/pqwallet/rust/target/release/slhdsa-rust-rig; D=skunks/pqwallet/diff
$R kat <dir with the three ACVP internalProjection.json files>     # provenance: diff/acvp-provenance.txt
$R acvp-cases $D/acvp-cases.json $D/rust-acvp.json
$R verify $D/sigs.json $D/rust-verify-noble-sigs.json
$R sign $D/keys.json $D/digests.json $D/rust-sigs.json
bash skunks/policy/6-rekey/slhdsa/run.sh verify-ext $D/rust-sigs.json $D/verify-ext-rust.json
(cd skunks/pqwallet && npx tsx scripts/noble-verify.ts diff/rust-sigs.json diff/noble-verify-rust.json)
$R negatives $D/slh-negatives.json <two_outputs_digest> <second_box_digest> $D/slh-negatives-out.json $D/rust-negatives.json
```

The two digests for `negatives` are printed by the harness's `negatives` command (`diff/slh-negatives.log`, lines
`two_outputs_digest=` and `second_box_digest_for_signing=`). No new cryptography lives here; `sha2` and `sha3` are used
only to build the HashSLH-DSA framing for the pre-hash ACVP groups, which the crate does not expose.
