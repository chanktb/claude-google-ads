# Usage guide — claude-google-ads

How to run the suite day-to-day: what to prepare, how to start, and the command for each job.

## 1. Prepare — connect your data FIRST (the suite never guesses)
`setup` inventories these into the context `connections` block; `/claude-google-ads:google-ads` checks them before routing.
A missing source is flagged `UNVERIFIED` in the output, never fabricated.
- **Google Ads** — a read-only GAQL MCP. **MANDATORY** (nothing runs without it).
- **Store** (Shopify / WooCommerce / BigCommerce — an MCP or an Admin token in a local `.env`) —
  **required for full value:** real AOV, true-ROAS, landing-page checks, catalog for builders.
- **Merchant Center** (Content-API connector) — **required (ecom):** product-feed health (OOS / disapprovals).
- **GA4** (MCP or a client + property id) — recommended: channel mix + Ads-vs-GA4 value cross-check.
- **GSC** — optional: search visibility.
- The core audit + money-leak diagnostics run off the Google Ads MCP alone; Store/Merchant/GA4 unlock AOV,
  true-ROAS, feed health, and the value cross-check. Connect them for the full cost-cutting depth.
- **Python 3** with two libraries (the deterministic scripts use them):
  `python -m pip install pyyaml openpyxl`
- **A working folder per business** (e.g. `~/ads/acme/`). It holds `account-context.yaml` and every output in
  dated subfolders (`audits/`, `plans/`, `builds/`, `changes/`, `raw/`). Keep it OUTSIDE the plugin repo —
  business data never lives in the plugin, and the suite never scatters files elsewhere. Secrets are recorded
  as **pointers** (where the token lives), never copied in. Full spec: `references/workspace-layout.md`.

## 2. Install
- **Published:** `/plugin install claude-google-ads@chanktb/claude-google-ads` → the `/claude-google-ads:google-ads` command
  and all skills become available.
- **Local / dev (current):** add this project as a local plugin, or copy `skills/` into `~/.claude/skills/`.
  Or simply ask Claude in chat to run a skill against your folder (Claude reads the skill + runs the scripts).

## 3. Use the explicit commands (don't rely on plain language)
Every action has its own slash command, and each command invokes **only** its claude-google-ads skill. Use
them rather than natural language — that's what keeps it from colliding with other ads skills you may have
installed (`google-ads-optimizer`, `pmax-campaign-builder`, `ads-google`, `ads-meta`, `claude-growth`, …).

| You want to… | Command |
|---|---|
| Start / not sure where you are | `/claude-google-ads:google-ads` (router → tells you the next command) |
| Onboard a business | `/claude-google-ads:setup` |
| **Audit an account** | `/claude-google-ads:audit` |
| Validate conversion tracking | `/claude-google-ads:measurement` |
| Plan a launch / budget | `/claude-google-ads:plan` |
| Build a PMax campaign | `/claude-google-ads:pmax` |
| Build a Search campaign | `/claude-google-ads:search` |
| Build a Branded Search campaign | `/claude-google-ads:branded` |
| Build a Demand Gen campaign | `/claude-google-ads:demandgen` |
| Push / export to Google Ads | `/claude-google-ads:push` |
| Monitor a live campaign | `/claude-google-ads:track` |
| Optimize / weekly review | `/claude-google-ads:optimize` |
| **Daily/weekly routine (gated, remembers history)** | `/claude-google-ads:routine` |
| Design an A/B test | `/claude-google-ads:experiment` |
| Write ad copy / assets | `/claude-google-ads:assets` |

Each command reads `account-context.yaml` from the current working directory and writes outputs there.

## 4. Run an AUDIT — step by step
1. **Enter the business folder:** `cd ~/ads/acme`
2. **First time? Run setup** (produces `account-context.yaml`):
   - `/claude-google-ads:google-ads` (auto-runs setup when no context exists), answer the few questions, confirm.
   - Verify: `python <plugin>/skills/setup/scripts/validate_context.py ./account-context.yaml`
3. **Run the audit:** say **"audit my account"** (or `/claude-google-ads:google-ads` → audit). It will:
   - build the **active campaign set** (ENABLED + impressions in the window — dormant campaigns excluded),
   - pull data via the Google Ads MCP, apply the 6 guards, score the 80-check catalog,
   - write the outputs.
4. **Outputs land in the folder:**
   - `audit-result.json` — the structured result (the score)
   - `AUDIT.html` — the single, polished, shareable client report (open in a browser): score + full check +
     money-leaks + per-campaign visuals in one file
   - `MONEY-LEAK-REPORT.md` + `DETAILED-ACCOUNT-REPORT.md` — the markdown companions

**Prepare for the best audit:** know the customer id (or let setup detect it), pick the window (default 30d),
and link GA4 + the store connector if you can. Missing connectors don't block — the audit flags what it
couldn't verify rather than guessing.

## 5. A full first run (copy-paste mental model)
```
cd ~/ads/acme
/claude-google-ads:setup        # detect MCPs, write account-context.yaml
/claude-google-ads:audit        # -> audit-result.json + AUDIT.html (single report) + MONEY-LEAK-REPORT.md
/claude-google-ads:measurement  # tracking gate (do this before spend)
/claude-google-ads:plan         # -> GOOGLE-ADS-PLAN.md (campaign mix + forecast)
/claude-google-ads:pmax         # -> blueprint.xlsx + campaign-spec.json
/claude-google-ads:push         # -> Editor CSV (Search) or guided checklist (PMax) + ready-to-copy
# later, once live:
/claude-google-ads:track        # pacing / learning
/claude-google-ads:optimize     # weekly review + action plan
```
You can pass extra context after any command, e.g. `/claude-google-ads:pmax OPI gel, $80/day`.

## 6. The runnable scripts (the skills call these; you rarely run them by hand)
| Script | Purpose |
|---|---|
| `skills/setup/scripts/validate_context.py` | validate account-context.yaml + readiness gates |
| `skills/audit/scripts/money_leak_report.py` | bundle.json (+ audit-result.json) → the single `AUDIT.html` + MD reports |
| `skills/plan/scripts/forecaster.py` | budget → conversions / CPA / ROAS bands |
| `skills/builder-pmax/scripts/spec_to_xlsx.py` | campaign-spec.json → styled Excel blueprint |
| `skills/pusher/scripts/validate_spec.py` | pre-push validation + spend-cap gate (Google-accurate char counts) |
| `skills/pusher/scripts/spec_to_editor_csv.py` | Search/Branded spec → Google Ads Editor import CSV |
| `skills/pusher/scripts/spec_to_paste.py` | ready-to-copy keywords/negatives ( [exact] / "phrase" / broad ) |
| `skills/pusher/scripts/spec_to_pmax_checklist.py` | PMax spec → ordered, paste-ready UI build checklist |
| `skills/pusher/scripts/validate_changeset.py` | change-set.json safety gate (cooldown · ±10% · ≤0.3x tROAS · never-block-brand) |
| `skills/pusher/scripts/changeset_to_actions.py` | change-set.json → CHANGE-PLAN.md + negatives CSV/paste |
| `skills/optimizer/scripts/tiering.py` | campaigns → Gold/Silver/Bronze/Dead (margin-tier aware) |
| `skills/optimizer/scripts/search_term_miner.py` | wasted terms → categorized ready-to-copy negatives |
| `skills/experiments/scripts/significance.py` | conversions-per-arm → is the A/B test powered? |

## 7. Multiple businesses
One folder per business, each with its own `account-context.yaml`. Run the same commands in each folder —
the skills always read the context from the current working directory.

## Notes
- **Writes are gated.** `pusher` never changes the account silently: it creates campaigns PAUSED, behind a
  human approval gate and a spend cap. With a read-only MCP it exports files for you to import/review.
- **Audit/optimize only touch live campaigns** (ENABLED + impressions in the window). Long-off campaigns
  are excluded.
