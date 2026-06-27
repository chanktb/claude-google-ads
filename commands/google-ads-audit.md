---
description: Audit + score the current Google Ads account, render an HTML report (claude-google-ads suite).
---

Use the `claude-google-ads:audit` skill to audit the Google Ads account for the business in the current
working directory.

**Use ONLY `claude-google-ads:audit`.** Do not invoke other ads skills (google-ads-optimizer,
pmax-campaign-builder, ads-google, ads-meta, claude-growth, etc.) — this command is dedicated to the
claude-google-ads suite.

If no `account-context.yaml` exists here, run `/google-ads-setup` first. Build the active campaign set
(ENABLED + impressions in the window) before scoring, apply GUARD-1…6, then write `GOOGLE-ADS-AUDIT.md`,
`audit-result.json`, and `audit-report.html`.

$ARGUMENTS
