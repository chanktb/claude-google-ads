---
description: Build a Performance Max campaign blueprint + spec (claude-google-ads suite).
---

Use the `claude-google-ads:builder-pmax` skill to build a Performance Max campaign for the business in the
current working directory.

**Use ONLY `claude-google-ads:builder-pmax`.** Do not invoke other ads skills — especially NOT
`pmax-campaign-builder`, `google-ads-optimizer`, or `ads-google`. This command is dedicated to the
claude-google-ads suite.

Present the split-strategy menu and recommend objectively (budget-aware). Emit both `blueprint.xlsx`
(via `${CLAUDE_PLUGIN_ROOT}/skills/builder-pmax/scripts/spec_to_xlsx.py`) and `campaign-spec.json` for the pusher.

$ARGUMENTS
