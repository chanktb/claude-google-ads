---
description: Onboard a business — build account-context.yaml (claude-google-ads suite). Reads/writes the working dir.
---

Use the `claude-google-ads:setup` skill to onboard the business in the current working directory and write
`account-context.yaml`.

**Use ONLY `claude-google-ads:setup`.** Do not invoke other ads skills (google-ads-optimizer,
pmax-campaign-builder, ads-google, ads-meta, claude-growth, etc.) — this command is dedicated to the
claude-google-ads suite.

Detect connected MCPs by capability, derive what you can (AOV from store, account ids from Google Ads),
ask only the genuine gaps, confirm, then write and validate with
`${CLAUDE_PLUGIN_ROOT}/skills/setup/scripts/validate_context.py`.

$ARGUMENTS
