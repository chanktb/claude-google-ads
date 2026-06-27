---
description: Design a disciplined A/B split test (one variable, powered) (claude-google-ads suite).
---

Use the `claude-google-ads:experiments` skill to design an A/B test for the business in the current working
directory.

**Use ONLY `claude-google-ads:experiments`.** Do not invoke other ads skills — this command is dedicated to
the claude-google-ads suite.

One variable at a time. Run the feasibility check with `${CLAUDE_PLUGIN_ROOT}/skills/experiments/scripts/significance.py` (is the
test powered?) before committing. 50/50, defined runtime, pre-stated decision rule.

$ARGUMENTS
