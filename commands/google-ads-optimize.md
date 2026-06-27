---
description: Optimize a running account — tiering, negatives, budget/tROAS, action plan (claude-google-ads suite).
---

Use the `claude-google-ads:optimizer` skill to optimize the account for the business in the current working
directory.

**Use ONLY `claude-google-ads:optimizer`.** Do not invoke other ads skills — especially NOT
`google-ads-optimizer` or `ads-google`. This command is dedicated to the claude-google-ads suite.

Scope to active campaigns. 3-source attribution (store = ground truth). Use
`${CLAUDE_PLUGIN_ROOT}/skills/optimizer/scripts/tiering.py` and `search_term_miner.py`. Propose changes; apply only via the
pusher (approval gate). Respect the tROAS step-up discipline.

$ARGUMENTS
