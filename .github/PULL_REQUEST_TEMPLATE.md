## What & why

<!-- What does this change and why? Link any issue. -->

## Checklist

- [ ] Tests added/updated; `pytest --cov=synk --cov-fail-under=80` passes
- [ ] `npm test`, `npx tsc --noEmit`, and `npm run build` pass (if client touched)
- [ ] `protocol/messages.md` updated (if the wire protocol changed) — Python + TS in sync
- [ ] `CHANGELOG.md` updated
- [ ] No LLM call added on the per-tick path (deliberation stays off-tick)
