#!/usr/bin/env bash
# run-seats.sh <seatdir> <slice>: one Claude Opus Cryptography seat and two outside seats (grok, agy) in parallel on
# the gate slice. Fresh headless sessions, read tools only, under the login (ANTHROPIC_API_KEY unset). Seats are never
# pattern-killed: the timeouts end them.
S="$1"; slice="$2"; out="$S/out"; mkdir -p "$out"; cd "$slice"
echo "start $(date -u +%H:%M:%S)" >> "$out/STATUS"
( env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT -u ANTHROPIC_API_KEY timeout 45m claude -p --model opus --tools "Read,Glob,Grep" \
    --no-session-persistence --strict-mcp-config "$(cat "$S/prompt-crypto.md")" > "$out/crypto.md" 2> "$out/crypto.stderr" \
    || echo "seat crypto exit=$?" >> "$out/crypto.stderr"; echo "crypto done $(date -u +%H:%M:%S) $(wc -c < "$out/crypto.md") bytes" >> "$out/STATUS" ) &
( SEAT_ARGS='--max-turns 60' GROK_TIMEOUT=40m ~/bin/ergo_logic/tools/outside-seat grok "$slice" "$S/prompt-outside.md" "$out" > "$out/grok.log" 2>&1; echo "grok done $(date -u +%H:%M:%S) exit=$?" >> "$out/STATUS" ) &
( SEAT_ARGS='--effort high' SEAT_TIMEOUT=40m ~/bin/ergo_logic/tools/outside-seat agy "$slice" "$S/prompt-outside.md" "$out" > "$out/agy.log" 2>&1; echo "agy done $(date -u +%H:%M:%S) exit=$?" >> "$out/STATUS" ) &
wait; echo "ALL DONE $(date -u +%H:%M:%S)" >> "$out/STATUS"
