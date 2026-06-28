---
description: Entry point for the claude-google-ads suite — routes to setup, audit, plan, build, push, track, or optimize based on what you ask for.
---

# /google-ads

Router / "where am I" entry point. For a specific step, prefer the **dedicated command**:
`/claude-google-ads:setup`, `:audit`, `:measurement`, `:plan`, `:pmax`, `:search`, `:branded`, `:demandgen`,
`:push`, `:track`, `:optimize`, `:routine`, `:experiment`, `:assets`. (Type `/claude-google-ads` to see them
all in the menu — you don't memorize the names.)

Use this `/google-ads` command when the user is unsure where they are: read the context, report the stage,
and tell them the single dedicated command to run next.

Route the user's request to the correct sub-skill of the claude-google-ads plugin.

## Routing logic

1. **Check for `account-context.yaml`** in the working directory (or the path the user gives).
   - If missing -> invoke `claude-google-ads:setup` first. Nothing else runs without context.
2. Match intent -> skill:
   - "audit", "score my account", "what's wrong" -> `claude-google-ads:audit`
   - "is my tracking right", "conversions", "GA4 import" -> `claude-google-ads:measurement`
   - "plan", "budget", "what campaigns should I run", "launch" -> `claude-google-ads:plan`
   - "build pmax", "performance max" -> `claude-google-ads:builder-pmax`
   - "build search" -> `claude-google-ads:builder-search`
   - "branded search", "brand campaign" -> `claude-google-ads:builder-branded-search`
   - "demand gen" -> `claude-google-ads:builder-demand-gen`
   - "push", "export", "upload to google ads" -> `claude-google-ads:pusher`
   - "how's it doing", "pacing", "learning phase" -> `claude-google-ads:tracker`
   - "optimize", "improve roas", "negatives", "raise tROAS" -> `claude-google-ads:optimizer`
   - "experiment", "A/B test", "split test" -> `claude-google-ads:experiments`
   - "ad copy", "assets", "headlines", "creative" -> `claude-google-ads:assets`
3. If ambiguous, ask one clarifying question, then route.

$ARGUMENTS
