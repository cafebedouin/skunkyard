# wots-spend-v4: the same WOTS spend, but only after the devnet has activated block version 4 (the 6.0 rules
# mainnet runs; "v4": true in the topology shortens the soft-fork vote so v4 activates at about height 16).
# Waits for /info parameters.blockVersion == 4, then runs wots-spend.sh unchanged.
Q2DEV_V4="$(dirname "$RIG_HOOK")"
end=$((SECONDS + 300)); bv=""
while [[ $SECONDS -lt $end ]]; do bv=$(rest A /info | jq -r '.parameters.blockVersion // empty' 2>/dev/null); [[ "$bv" == 4 ]] && break; sleep 3; done
echo "[wots-v4] blockVersion=$bv at height $(full_height A) after waiting $((SECONDS - end + 300)) s"
if [[ "$bv" != 4 ]]; then echo "[wots-v4] FAIL: block version 4 did not activate"; rig_verdict=FAIL; echo "WOTS-SPEND: FAIL (v4 not active)"
else source "$Q2DEV_V4/wots-spend.sh"; fi
