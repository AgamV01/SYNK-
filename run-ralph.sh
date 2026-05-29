#!/usr/bin/env bash
# Drive SYNK to completion with the Ralph Wiggum technique.
#
# Option A (recommended, in-session): the official Claude Code plugin.
#   /ralph-loop:ralph-loop "Build SYNK per PROMPT.md. Read PROMPT.md, fix_plan.md, specs/synk-spec.md. One fix_plan task per iteration." --completion-promise "SYNK_V1_COMPLETE" --max-iterations 400
#   A Stop hook re-injects the prompt each time Claude tries to exit, until the promise is emitted or the cap is hit.
#
# Option B (headless CLI): this bash loop. Fresh context each iteration; state lives in files and git.
#   ./run-ralph.sh [max_iterations]
set -euo pipefail
MAX_ITERS="${1:-400}"
PROMISE="SYNK_V1_COMPLETE"
LOG_DIR=".ralph"; mkdir -p "$LOG_DIR"
for f in PROMPT.md fix_plan.md specs/synk-spec.md CLAUDE.md; do
  [ -f "$f" ] || { echo "missing required file: $f"; exit 1; }
done
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || git init -q
echo "Ralph loop up to $MAX_ITERS iterations. Promise: $PROMISE"
for ((i=1; i<=MAX_ITERS; i++)); do
  ts="$(date +%Y%m%d-%H%M%S)"; out="$LOG_DIR/iter-$(printf '%03d' "$i")-$ts.log"
  echo "── iteration $i/$MAX_ITERS ($ts) ──"
  claude --print --dangerously-skip-permissions "$(cat PROMPT.md)" | tee "$out"
  if grep -q "<promise>${PROMISE}</promise>" "$out"; then
    echo "Promise emitted on iteration $i. SYNK v1 reported complete."; exit 0
  fi
  if [ -z "$(git status --porcelain)" ]; then
    echo "warning: no file changes in iteration $i; if this repeats, the prompt or plan needs attention."
  fi
done
echo "Hit max iterations without the promise. Inspect $LOG_DIR, PROGRESS.md, fix_plan.md."; exit 1
