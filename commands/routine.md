---
description: Run the daily/weekly/monthly Google Ads operating routine — gated actions, remembers history (claude-google-ads suite).
---

Use the `claude-google-ads:routine` skill to run the operating routine for the business in the current
working directory. Optional argument: `daily` / `weekly` / `monthly` / `quarterly` (default: run whatever
is due/overdue).

**Use ONLY `claude-google-ads:routine`.** Do not invoke other ads skills (google-ads-optimizer, ads-google,
etc.) — this command is dedicated to the claude-google-ads suite.

First run `${CLAUDE_PLUGIN_ROOT}/skills/routine/scripts/routine_state.py` to see what's due/overdue (it
remembers when each cadence last ran), then run those cadences — calling tracker/optimizer/measurement under
the hood — and apply the decision gates (only act when ALL preconditions hold, else WAIT). Stamp the run
with `--mark` when done.

$ARGUMENTS
