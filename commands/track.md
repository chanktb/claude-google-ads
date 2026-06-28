---
description: Monitor live campaigns — pacing, learning phase, anomalies (observe only) (claude-google-ads suite).
---

Use the `claude-google-ads:tracker` skill to monitor the live campaigns for the business in the current
working directory.

**Use ONLY `claude-google-ads:tracker`.** Do not invoke other ads skills (google-ads-optimizer, etc.) —
this command is dedicated to the claude-google-ads suite.

Observe-only: report pacing, learning-phase status, and real anomalies (apply the change-event cooldown;
no false absence). Scope to active campaigns. Change nothing — hand actions to `/google-ads-optimize`.

$ARGUMENTS
