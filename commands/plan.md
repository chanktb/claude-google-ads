---
description: Plan a launch/expansion — budget split, campaign mix, forecast (claude-google-ads suite).
---

Use the `claude-google-ads:plan` skill to plan a Google Ads launch or expansion for the business in the
current working directory.

**Use ONLY `claude-google-ads:plan`.** Do not invoke other ads skills (google-ads-optimizer, ads-google,
claude-growth, etc.) — this command is dedicated to the claude-google-ads suite.

Require measurement = PASS first. Detect LAUNCH vs EXPANSION, recommend the campaign mix, split the budget
with learning minimums, and forecast bands with `${CLAUDE_PLUGIN_ROOT}/skills/plan/scripts/forecaster.py`.

$ARGUMENTS
