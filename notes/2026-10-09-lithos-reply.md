# The Lithos lead developer's reply to the upkeep DM (2026-10-09)

Private message (Telegram); paraphrased here, quote publicly only with his say-so.

- He will review over the next two days and said to open the pull requests now. Opened the same day:
  Lithos-Protocol/Lithos-Client #14 (`deployment-override`), #15 (`upkeep-source`), #16 (`upkeep-space-option`),
  #17 (`snapshot-spec-wait`); overview issue #13.
- On the open question about rejected packages (question 4 in the issue): resending the package to every source,
  including ones whose transactions failed, is intended behaviour, because validation can and often does depend
  on height, especially for Lithos transactions. The design rule behind it: communication between the candidate
  builder and the individual sources is to be minimal, because the stratum and the whole mining path are the
  latency-critical part of the client. If a source ever needs package results, use a fire-and-forget Akka message
  or a shared thread-safe cache, never a round trip.

What that settles for the upkeep source: the "no learning from a rejected package" limit stays as designed; the
source's own `verifyWithNode` check is the right place for refusal knowledge, and any future feedback from the
builder would be a one-way message or a cache the source reads, which is the shape `UpkeepSource.Memory` already has.
