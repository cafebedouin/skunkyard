#!/usr/bin/env bash
# run-seats.sh <seatdir> <slice>: one Claude Opus Fidelity seat and two outside seats (grok, agy) in parallel on the
# slice. Fresh headless sessions, read tools only, under the login (ANTHROPIC_API_KEY unset). Never pattern-killed.
# Round 1 note: agy's first run produced no output (a shell command request auto-denied in headless mode); it was
# rerun with prompt-outside-agy.md, which opens with a read-only instruction.
S="$1"; slice="$2"; out="$S/out"; mkdir -p "$out"; cd "$slice"
echo "start $(date -u +%H:%M:%S)" >> "$out/STATUS"
( env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT -u ANTHROPIC_API_KEY timeout 40m claude -p --model opus --tools "Read,Glob,Grep" \
    --no-session-persistence --strict-mcp-config "$(cat "$S/prompt-fidelity.md")" > "$out/fidelity.md" 2> "$out/fidelity.stderr"; echo "fidelity done $(date -u +%H:%M:%S)" >> "$out/STATUS" ) &
( SEAT_ARGS='--max-turns 60' GROK_TIMEOUT=40m ~/bin/ergo_logic/tools/outside-seat grok "$slice" "$S/prompt-outside.md" "$out" > "$out/grok.log" 2>&1; echo "grok done $(date -u +%H:%M:%S) exit=$?" >> "$out/STATUS" ) &
( SEAT_ARGS='--effort high' SEAT_TIMEOUT=40m ~/bin/ergo_logic/tools/outside-seat agy "$slice" "$S/prompt-outside-agy.md" "$out" > "$out/agy.log" 2>&1; echo "agy done $(date -u +%H:%M:%S) exit=$?" >> "$out/STATUS" ) &
wait; echo "ALL DONE $(date -u +%H:%M:%S)" >> "$out/STATUS"
