---
description: Push a campaign-spec.json OR an optimizer change-set.json safely (Editor CSV / guided UI) (claude-google-ads suite).
---

Use the `claude-google-ads:pusher` skill to push the spec in the current working directory into Google Ads.
**Auto-detect by `kind`:** a `change-set.json` (`kind: "change-set"`, from the optimizer) takes the change
path; otherwise a `campaign-spec.json` (from a builder) takes the build path.

**Use ONLY `claude-google-ads:pusher`.** Do not invoke other ads skills — this command is dedicated to the
claude-google-ads suite.

Safety invariants (both paths): validate first; human approval gate; spend cap; nothing is created enabled.
- **Build path** — `validate_spec.py`, create PAUSED. Search/Branded → Editor CSV (`spec_to_editor_csv.py`);
  PMax → guided checklist (`spec_to_pmax_checklist.py`) + ready-to-copy blocks (`spec_to_paste.py`).
- **Change path** — `validate_changeset.py` (cooldown gate · budget ≤+10% · tROAS ≤0.3x · never-block-brand)
  then `changeset_to_actions.py` → `CHANGE-PLAN.md` + negatives CSV/paste. Report any moves HELD by cooldown.
- API mutate only if `api_write`.

$ARGUMENTS
