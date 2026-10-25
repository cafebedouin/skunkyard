# Result: storage rent is not a migration path; the dormant exposed stock is about a tenth of P2PK value

Run 2026-10-25 against `PREREG.md`. Script `rent_census.py`; walk of the whole unspent set at explorer height
**1,902,073** through `https://api.ergo.aap.cornell.edu/api/v1` (1,239 ranges, none missing, 4,778 s with 503
retries, `out/walk.log`). Every number below is a line printed by the script into `out/summary.md`;
`out/rent-census.json` holds the same numbers.

## Verdicts against the preregistered claims

| Claim | Threshold | Measured | Verdict |
|---|---|---|---|
| R1 one-year forward rent take on maturing P2PK value | below 5% | **0.74%** (59,895.8 of 8,107,170.0 ERG) | holds |
| R2a P2PK ERG in boxes three or more years old | below 10% | **10.44%** (8,106,930 of 77,640,212 ERG) | **misses by 0.44 points**; far from the 30% that would reverse the conclusion |
| R2b P2PK ERG past rent age now, share of non-protocol supply | below 5% (Node C) | **0.001%** (954.4 ERG, 92 boxes) | holds; legacy thread stays deferred |
| R3a P2PK ERG one rent cycle consumes whole | below 0.1% | **0.004%** (2,980.5 ERG, 817,375 boxes) | holds |
| R3b P2PK ERG surviving more than 1,000 cycles | above 90% | **93.67%** | holds |
| R3 counts-against: ERG exhausted within 10 cycles | 1% or more | 0.899% | not triggered, close |

## The tables

Unspent boxes 3,146,346 holding 96,460,767.4 ERG. P2PK 3,044,445 boxes, 77,640,211.8 ERG. Contracts 101,899 boxes,
4,206,057.3 ERG. Excluded as protocol boxes: EIP-27 re-emission (`ae9ac8d914dc`) 12,986,574.3 ERG and the SigmaUSD
bank (`246e14059ac2`) 1,627,924.0 ERG, which the 1,000,000-ERG rule caught although it is not a protocol box; the
non-protocol denominator (81,846,269.1 ERG) is therefore 1.6M low, which makes R2b conservative in the wrong
direction by a factor that cannot move 0.001% anywhere near 5%.

P2PK ERG by age of the box (settlement height):

| age | boxes | ERG | share |
|---|---|---|---|
| under 1 year | 979,109 | 31,954,549.8 | 41.16% |
| 1 to 2 years | 774,980 | 18,905,070.9 | 24.35% |
| 2 to 3 years | 532,623 | 18,673,660.8 | 24.05% |
| 3 to 4 years | 757,641 | 8,105,975.9 | 10.44% |
| 4 to 5 years | 91 | 954.4 | 0.00% |
| 5 years or more | 1 | 0.0 | 0.00% |

P2PK ERG by rent cycles to exhaustion (one cycle is four years; fee = 1,250,000 nanoERG × box bytes):

| cycles | boxes | ERG | share |
|---|---|---|---|
| 1, consumed whole | 817,375 | 2,980.5 | 0.004% |
| 2 to 10 | 1,160,890 | 694,517.9 | 0.895% |
| 11 to 100 | 963,018 | 1,741,973.0 | 2.244% |
| 101 to 1,000 | 75,469 | 2,474,613.3 | 3.187% |
| over 1,000 | 27,693 | 72,726,127.1 | 93.671% |

Rent eligibility by the box's own creation height: 92 boxes past rent age now (954.4 ERG). Reaching rent age within
365 days: 757,735 boxes, 8,107,170.0 ERG; one claim on each takes 59,895.8 ERG (0.74%); 163,188 of them (660.9 ERG)
are consumed whole; the other 594,547 boxes, 8,106,509 ERG, are recreated under the same P2PK tree.

## Reading

- **Rent moves no exposed value out of its exposed form.** By code (the recreated box must keep R1, the script) and
  by measurement (0.74% of maturing value taken, the rest re-emitted at the same key). The stock it will ever exhaust
  is dust: 0.004% of P2PK ERG now, under 1% within ten cycles, which is forty years.
- **Rent does keep the set clean.** Only 92 boxes sit past rent age; claims are taken within blocks of maturity (U1b).
  So "untouched for four years" is a state that does not persist on Ergo, which is why no box older than four years
  appears in the age table. Dormancy has to be read from the box's age below four years, not from rent eligibility.
- **The dormant exposed stock is about 8.1M ERG, a tenth of P2PK value, and it is one cohort.** The three-to-four-year
  bucket is the boxes from roughly heights 850,000 to 1,113,000 (2023). Whether those owners are gone or merely
  still cannot be told from the chain; box age is an upper bound on owner dormancy, since an active owner may hold
  an old box. A deadline rule of the rent-period shape, "exposed keys stop working four years after the flag", would
  act on at most this tenth if holders behaved as they do now, and on far less if the flag itself prompts moves.
- **Node C of `DECISIONS.md` resolves "below":** rent-eligible exposed ERG is 0.001% of non-protocol supply. The
  legacy-coins thread stays deferred; this file is the number to cite if the question is raised.

## Limits

- One mirror, not cross-checked against another explorer (as in U1c). The set moves during the walk (80 minutes);
  a box spent between its range's read and the end can be missing. Height pinned at the start and stated.
- Age is by settlement height, which is when the current box was created, not when its owner last acted on any
  coin. Both directions of error: an active owner's old box reads as dormant; a dormant owner's coins recreated by a
  rent claim would read as young (none exist today, since no box is past rent age).
- The protocol-box exclusion caught the SigmaUSD bank; stated above, with its direction.
- Nothing was built or submitted; read-only GETs at the mirror's rate limit.
