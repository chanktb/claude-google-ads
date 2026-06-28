---
description: Audit + score the current Google Ads account, render an HTML report (claude-google-ads suite).
---

Use the `claude-google-ads:audit` skill to audit the Google Ads account for the business in the current
working directory.

**Use ONLY `claude-google-ads:audit`.** Do not invoke other ads skills (google-ads-optimizer,
pmax-campaign-builder, ads-google, ads-meta, claude-growth, etc.) — this command is dedicated to the
claude-google-ads suite.

If no `account-context.yaml` exists here, run `/google-ads-setup` first. Build the active campaign set
(ENABLED + impressions in the window) before scoring, apply GUARD-1…6, then write `audit-result.json` (the score)
and render the **single** client report `AUDIT.html` via `money_leak_report.py` (it also emits
`MONEY-LEAK-REPORT.md` + `DETAILED-ACCOUNT-REPORT.md`). There is ONE HTML report — `AUDIT.html`. Do not produce a
second HTML file.

$ARGUMENTS
