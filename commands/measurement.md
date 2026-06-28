---
description: Validate conversion tracking before spend — the gate (claude-google-ads suite).
---

Use the `claude-google-ads:measurement` skill to validate conversion tracking for the business in the
current working directory.

**Use ONLY `claude-google-ads:measurement`.** Do not invoke other ads skills (google-ads-optimizer,
ads-google, ads-meta, etc.) — this command is dedicated to the claude-google-ads suite.

Do the holistic check (actions + per-campaign usage + source/double-count) before any verdict. Output
PASS / WARN / FAIL; a FAIL gates `/google-ads-plan` and the builders.

$ARGUMENTS
