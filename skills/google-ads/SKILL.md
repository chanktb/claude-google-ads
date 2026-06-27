---
name: google-ads
description: >
  Router / orchestrator for the claude-google-ads suite. Use when the user wants to do anything with Google
  Ads but hasn't named a specific step — "help me with Google Ads", "launch Google Ads for my store", "run
  google ads", or just /google-ads. Reads account-context.yaml, runs setup if missing, figures out where the
  account is in the lifecycle, and dispatches to the right sub-skill (setup, measurement, audit, plan,
  builder-*, pusher, tracker, optimizer, assets, experiments). It orchestrates; it does not do the work.
---

# Google Ads — Router

The single entry point. Find out where the user is in the campaign lifecycle and hand off to the right
sub-skill. Enforce the order so nothing runs on a broken foundation.

## STEP 0 — Locate context
Look for `account-context.yaml` in the working directory (or a `--context <path>` the user gives).
- **Missing →** run `claude-google-ads:setup` first. Nothing else runs without context.
- Present → continue.

## STEP 0b — Connection precheck (REQUIRED — don't run skills on a half-connected account)
Read the context `connections` block (or detect live). Before routing, confirm the prerequisites are set up;
the suite's value depends on real data, and it must never run on a gap silently (see the no-fabricate gate):

| Connection | Tier | If missing |
|---|---|---|
| **Google Ads** (read-only GAQL MCP) | **MANDATORY** | **STOP.** Nothing runs. Send the user to `setup` to connect a Google Ads MCP. |
| **Store** (Shopify/Woo/BigCommerce) | required for full value | Guide to connect (MCP or an Admin token in a `.env`). Without it: no real AOV / true-ROAS — those outputs render `UNVERIFIED — connect store`. |
| **Merchant Center** (ecom) | required for feed health | Guide to connect. Without it: product *performance* only, feed *health* (OOS/disapproval, D14-B) = `UNVERIFIED`. |
| **GA4** | recommended | Guide to connect. Without it: no Ads-vs-GA4 value cross-check. |
| **GSC** | optional | Note only. |

If **Google Ads** is missing → stop and run `setup`. If a value-tier source (store/Merchant/GA4) is missing →
**surface a one-line "connect these for full value" banner with the how-to, then proceed at reduced scope** —
every output that needed the missing source is flagged `UNVERIFIED`, never fabricated. Don't quietly skip.

## STEP 1 — Assess lifecycle stage
Run the context validator to read readiness, and scan the working dir for prior artifacts:
```
python ${CLAUDE_PLUGIN_ROOT}/skills/setup/scripts/validate_context.py ./account-context.yaml
```
Map state → the next sensible step:
| Readiness | Artifacts present | Likely next step |
|-----------|-------------------|------------------|
| not setup-complete | — | `setup` (finish context) |
| setup-complete, no audit | — | `audit` and/or `measurement` |
| measurement = FAIL | measurement report | back to tracking fixes (block plan/build) |
| measurement OK, no plan | audit + measurement | `plan` |
| plan exists, no spec | GOOGLE-ADS-PLAN.md | `builder-*` for the chosen types |
| spec exists, not pushed | campaign-spec.json | `pusher` |
| campaign live | — | `tracker` (new) / `optimizer` (mature) |

## STEP 2 — Route by intent
If the user named a task, map it and dispatch:
- "audit / score / what's wrong / wasted spend" → `audit`
- "tracking / conversions / GA4 import / double count" → `measurement`
- "plan / budget / what campaigns / media plan / forecast" → `plan`
- "build pmax / performance max" → `builder-pmax`
- "build search" → `builder-search`
- "branded / brand campaign / conquesting" → `builder-branded-search`
- "demand gen / youtube / discovery" → `builder-demand-gen`
- "push / export / upload / go live" → `pusher`
- "how's it doing / pacing / learning phase / anomaly" → `tracker`
- "optimize / improve ROAS / negatives / raise tROAS / weekly review" → `optimizer`
- "experiment / A/B / split test" → `experiments`
- "ad copy / headlines / assets / creative" → `assets`
If ambiguous, ask ONE clarifying question, then route.

## STEP 3 — Full launch (when the user wants the whole thing)
For "set up Google Ads for my business", run the pipeline in order, pausing for input where needed:
```
setup → measurement [GATE] → audit → plan → builder-* → pusher [approval] → tracker → optimizer
```
Hard gates (never skip):
- **No plan/build before `measurement` passes** (FAIL blocks; WARN carries a risk note).
- **`build-ready`** wants `brand_terms` (for branded search + PMax exclusion).
- **`pusher`** always: create PAUSED, human approval, spend cap.

## STEP 4 — "Where am I?" summary
When the user just says /google-ads (no task), produce a short status: readiness, what artifacts exist,
and the single recommended next action — then offer to run it. Don't dump everything; point to the next step.

## Model dispatch (run cheap, decide expensive)
Spend compute by cognitive load, not by habit — see `${CLAUDE_PLUGIN_ROOT}/references/model-tier-dispatch.md`.
The router itself is **Judge (J)** work (lifecycle reasoning, routing, gates). But the heavy *collection*
each sub-skill needs is **Scout/Routine** — so as orchestrator, push it down:
- **Scout (S, `haiku`)** — the `validate_context.py` run in STEP 1, a single status pull, one URL check.
- **Routine (R, `sonnet`)** — assembling the active-campaign set, full data-bundle pulls for audit/optimizer/tracker.
- **Judge (J, main session)** — picking the next lifecycle step, all gates, the "where am I" call.
Delegate S/R via `Agent(subagent_type: "general-purpose", model: …)` so the sub-agent keeps MCP + Bash; tell
it to **return raw, not conclude**. Each sub-skill carries its own per-STEP tier table.

## Notes
- The router orchestrates; each sub-skill reads the same `account-context.yaml` and writes to the working
  directory. Business data never lives in the plugin — it stays in your local `account-context.yaml`.
- Sub-skills are invoked by their namespaced names (`claude-google-ads:setup`, `claude-google-ads:audit`, …).
