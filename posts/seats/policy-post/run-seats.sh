#!/usr/bin/env bash
# run-seats.sh <seatdir> <slice>: three Claude seats (derivation, fidelity, wallet) and one outside seat (grok), in parallel
S="$1"; slice="$2"; out="$S/out"; mkdir -p "$out"; cd "$slice"
run_claude() {
  ( env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT -u ANTHROPIC_API_KEY timeout 40m claude -p --model opus --tools "Read,Glob,Grep" \
      --no-session-persistence --strict-mcp-config "$(cat "$S/prompt-$1.md")" ) > "$out/$1.md" 2> "$out/$1.stderr" \
    || echo "seat $1 exit=$?" >> "$out/$1.stderr"
  echo "$1 done $(date -u +%H:%M:%S) $(wc -c < "$out/$1.md") bytes" >> "$out/STATUS"
}
echo "start $(date -u +%H:%M:%S)" >> "$out/STATUS"
run_claude derivation & run_claude fidelity & run_claude wallet &
( SEAT_ARGS='--max-turns 60' GROK_TIMEOUT=35m ~/bin/ergo_logic/tools/outside-seat grok "$slice" "$S/prompt-outside.md" "$out" > "$out/grok.log" 2>&1; echo "grok done $(date -u +%H:%M:%S) exit=$?" >> "$out/STATUS" ) &
wait; echo "ALL DONE $(date -u +%H:%M:%S)" >> "$out/STATUS"
