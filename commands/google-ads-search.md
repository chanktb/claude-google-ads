---
description: Build a Search campaign blueprint + spec (claude-google-ads suite).
---

Use the `claude-google-ads:builder-search` skill to build a standard Search campaign for the business in
the current working directory.

**Use ONLY `claude-google-ads:builder-search`.** Do not invoke other ads skills (ads-google,
google-ads-optimizer, etc.) — this command is dedicated to the claude-google-ads suite.

Focus on keyword identification + match type (always output ready-to-copy: `[exact]` / `"phrase"` / broad).
Emit `blueprint.xlsx` + `campaign-spec.json` (campaign_type: search).

$ARGUMENTS
