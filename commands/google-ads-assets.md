---
description: Generate ad copy / assets (RSA, PMax, Demand Gen, sitelinks) (claude-google-ads suite).
---

Use the `claude-google-ads:assets` skill to generate creative assets for the business in the current working
directory.

**Use ONLY `claude-google-ads:assets`.** Do not invoke other ads skills (toi-uu-pdp, claude-growth, etc.) —
this command is dedicated to the claude-google-ads suite.

Count characters the Google way (NFC + CJK×2 + trim hidden/trailing); enforce limits; trademark-safe;
real product names/prices. Keywords/negatives come back ready-to-copy wrapped.

$ARGUMENTS
