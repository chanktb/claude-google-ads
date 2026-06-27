# Model-tier dispatch (run cheap, decide expensive)

How the suite spends compute. The expensive model is the scarce resource — reserve it for **judgment**
and push everything mechanical down to a cheaper tier. This is business-agnostic: it tiers work by
*cognitive load*, not by who the account belongs to.

## The one rule
**Collect cheap, decide expensive.** Fetching, looping, validating, formatting, and rendering are
mechanical — delegate them down. Interpreting, weighing trade-offs, drafting copy, and resolving guardrail
conflicts are judgment — keep them up. When a delegated step's output would change a verdict, the judge
re-reads the *raw* data; it never rubber-stamps a cheap tier's summary.

## Three tiers
Mapped to Claude models by default; on another setup, read them as cheapest / mid / top.

| Tier | Model (default) | Cognitive load | Use for |
|------|-----------------|----------------|---------|
| **S — Scout** | `haiku` | none — single deterministic op | one GAQL pull & return rows · run a script & return stdout · one HEAD/URL 200 check · validate a file vs schema · render HTML/xlsx from finished JSON · one MCP read (shop info, conversion-action list) |
| **R — Routine** | `sonnet` | a known procedure over many items, light reasoning | loop GAQL per-campaign & assemble the active set · pull + tabulate search terms from BOTH sources · batch char-count + listing-group validation across all AGs · derive AOV from store orders (filter channels, compute) · collect the full data bundle for audit/optimizer/tracker |
| **J — Judge** | main session (`opus`) | real judgment, trade-offs, drafting, dialogue | apply the six GUARDs & decide PASS/WARN/FAIL · root-cause + action-plan priority · choose the PMax split · write ad copy · the measurement holistic verdict · interpret the score · talk to the user · the approval gate |

## How to delegate (the idiom)
Dispatch a Scout/Routine step as a sub-agent with an explicit model:

```
Agent(subagent_type: "general-purpose", model: "haiku",
      description: "GAQL pull",
      prompt: "Run this one query via the Google Ads MCP `search` tool: <GAQL>.
               Return the rows verbatim as JSON. Do not interpret. Do not score.")
```

- Use **`general-purpose`** (tools `*`) for anything that touches the **Google Ads MCP, Shopify/GA4 MCP,
  or Bash** — the sub-agent inherits those connectors. The specialized `audit-google` / `audit-meta`
  agents only have Read/Bash/Write/Glob/Grep (**no MCP**), so they analyze already-pulled data offline —
  never hand them a live-pull job.
- Tell the Scout to **return raw, not conclude** ("return the rows; do not score / do not flag"). The
  judging stays in the main session.
- For a batch of independent pulls (per-campaign `campaign_search_term_insight` loops, many HEAD checks),
  fan out several Scouts in parallel rather than one slow serial pass.
- Pass the sub-agent an **explicit output path** when it writes a file (workspace hygiene): tell it the
  absolute target and that it must not write to a repo/plugin folder.

## What NEVER goes to a cheap tier
- **Any GUARD decision** (the checks that stop false positives — conversion holism, merged-negatives,
  cooldown, paused, margin-tier, false-absence). Guards are judgment; a Scout that "confirms" a guard
  defeats the purpose.
- **The verdict / score interpretation** — a Scout pulls the numbers, the Judge says what they mean.
- **Ad copy & the split choice** — voice and strategy are not mechanical.
- **The approval gate** in `pusher` — a human + the Judge, never delegated.

## Why this is safe
A Scout returning raw rows can't introduce a wrong *conclusion* — it has no conclusion to get wrong. The
risk only enters when a cheap tier is asked to *judge*; this policy never asks it to. The Judge still sees
the data and still owns every finding.
