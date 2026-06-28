---
name: google-ads-setup
description: >
  Onboards a business into the claude-google-ads suite by producing account-context.yaml — the backbone
  every other skill reads. Detects the data source (Shopify/WooCommerce/BigCommerce/CSV via MCP),
  captures Google Ads account ids and conversion actions, GA4/GSC properties (shared vs per-site),
  brand and competitor terms, margins, and operator guardrails. Use when the user starts with Google
  Ads, has no context file yet, or says "set up", "onboard", "connect my store/account", "configure".
---

# Google Ads — Setup

You build `account-context.yaml`, the single source of business truth that every other skill in this
suite reads. Nothing downstream (audit, plan, builder, pusher, tracker, optimizer) runs without it.

## Operating rules
- **Establish ONE working folder per business and keep everything in it** — see
  `${CLAUDE_PLUGIN_ROOT}/references/workspace-layout.md`. On first run, agree the `<workdir>` path with the user,
  create it, and write `account-context.yaml` there. Every downstream output goes into its dated subfolder
  (`audits/`, `plans/`, `builds/`, `changes/`, `raw/`). NEVER scatter files into the plugin folder, `D:\tmp`,
  `/tmp`, or the cwd root — a user who installs the plugin must get ONE tidy folder, not sprinkled files.
- **Secrets are POINTERS, never copies.** Do NOT write raw API tokens/keys into the working folder, any output,
  or `account-context.yaml`. The `connections` registry records *where* each token lives (`via: env:/path#KEY`,
  `via: server:/path`, `via: mcp:<id>`) and it's read at runtime. If the user wants creds kept locally, a
  gitignored `secrets/` in the workdir — never committed, never in a report.
- (legacy) Write `account-context.yaml` to the working directory, NEVER inside the plugin folder.
  Business data lives with the user, not in the code. (Use `--context <path>` if the user names one.)
- **Detect by capability, not by hardcoded server ids.** Inspect the connected MCP tools and match them
  to roles. The same skill must work for any user's MCP setup.
- **Setup is the CONNECTION HUB.** Its job is to inventory EVERY data source the suite needs and consolidate
  how to reach each one into the context's `connections` block — ONE place every downstream skill reads, so no
  skill ever re-discovers a connector or silently runs without data.
- **NO-FABRICATE DATA GATE (non-negotiable, the whole point).** Missing data is *connected or flagged, NEVER
  invented.* If a source is missing: (a) **guide the user to connect or provide it** (concrete steps — link
  the account, point to a `.env`/secrets file, a data-hub script), and (b) if it stays missing, record it as
  MISSING in `connections` so every downstream skill that needs it labels that part of its output
  **`UNVERIFIED — connect <source>`** and EXCLUDES it from any number it reports. **Skip-then-guess produces
  wrong analysis; an honest gap is correct.** A blank field is honest; a fabricated AOV / store-revenue / feed
  status is dangerous.
- **Confirm before writing.** Show the assembled context, get a yes, then write.

## Inputs / Outputs
- Reads: connected MCP tools, the user's answers, the storefront URL, and `${CLAUDE_PLUGIN_ROOT}/templates/account-context.yaml`.
- Writes: `./account-context.yaml`. Then runs the validator and prints a context-health report.

---

## Model dispatch (run cheap, decide expensive) — see `${CLAUDE_PLUGIN_ROOT}/references/model-tier-dispatch.md`
- **Scout (`haiku`)** — individual detection pulls (`list_accessible_customers`, `get-shop-info`, currency/timezone GAQL, conversion-action list); STEP 4 `validate_context.py` run.
- **Routine (`sonnet`)** — STEP 1 capability scan across connectors; AOV derivation from store orders (pull, filter to Online-Store channel, compute). Dispatch as `general-purpose` sub-agents; **return raw values, don't judge them** (setup records facts).
- **Judge (main session)** — competitor research (understand the niche, name real rivals), the interview, smart-default choices, STEP 3 assemble + confirm with the user. Detection is mechanical; deciding what's *true* and talking to the user is not.

## STEP 1 — Connection inventory (gather EVERY source into one place)

Probe every data role the suite needs, resolve HOW to reach each (the fallback chain below), and record the
result in the context's **`connections`** block — the single registry every downstream skill reads. Classify
each source: **connected** (record exactly how — MCP id / env path / script) · **available-not-wired** (the
user has it but it isn't connected yet → wire or guide) · **missing** (→ guide to connect; mark UNVERIFIED for
dependents). Don't leave a usable connection undiscovered, and don't let a skill run blind on a source you
could have wired here.

Look at the available tools and classify them. Examples of the signals to match (names vary per user):

| Role | How to recognize | What to pull |
|------|------------------|--------------|
| **Data source** | Tools for products/orders/collections (e.g. `get-shop-info`, `search_products`, `run-analytics-query` = Shopify; Woo/BigCommerce equivalents) | store name, currency, `catalog_url`, Merchant Center id |
| **Google Ads** | `list_accessible_customers`, GAQL `search` | accessible customer ids, currency, time_zone, conversion actions |
| **GA4** | analytics property/report tools, or the ga4-* skills | property_id |
| **GSC** | search-console/site tools, or the gsc-* skills | site_url |
| **Merchant Center** (ecom — REQUIRED for the product-feed audit) | a Google Merchant / Content-API connector (a Meta *catalog* MCP is NOT Google Merchant), or a custom merchant server runnable via its venv + ADC token | `merchant_center_id` per brand; feed/disapproval/OOS diagnostics |

**For ECOMMERCE, Merchant Center is REQUIRED, not optional** — product-feed health (out-of-stock, disapproved,
landing-page errors, price/GTIN) is the single biggest ROAS lever and the D14 audit needs it. If no Merchant
connector is detected, **instruct the user to connect one** (link Google Merchant Center + add the connector;
or point the audit at a runnable merchant server) and record `data_source.merchant_center_id`. Without it the
audit can do product PERFORMANCE (Ads `shopping_performance_view`) but must flag feed HEALTH as "connect
Merchant to verify OOS/disapproval".

### Fallback chain per data role (don't stop at "no MCP")
A connector being absent or disconnected does NOT mean the data is unreachable. For each role, try in order:
1. **MCP** connected for that role.
2. **API credentials in a local env file** (e.g. a Shopify Admin token, a Merchant Center key). Ask the
   user where their credentials live; many setups keep a `.env`/secrets file.
3. **A connected data hub / script** the user already runs (e.g. a Python GA4 client, a GSC pull script).
4. **Ask the user**, or read it from the Google Ads UI together.

When a source is **down or missing**: first **try to wire it** (the fallback chain above — most "missing"
sources are really "available but not connected": a Shopify token in a `.env`, a GA4 client script, a
Merchant account not yet linked). If it genuinely can't be wired now, record it as `status: missing` in
`connections` with a concrete `guide` (what to connect and how), tell the user exactly what's degraded
(e.g. "no live catalog → builder can't verify URLs; no store/GA4 → no true-ROAS or value cross-check"), and
**continue** — setup is not blocked by one offline connector.
**BUT the downstream rule is strict:** any skill that needs a missing source labels that output
`UNVERIFIED — connect <source>` and omits the number — it must **NOT** fabricate a value to fill the gap.
`data_source.type: none` / `measurement.ga4.enabled: false` are *honest* states that REDUCE what the suite
reports (no AOV, no true-ROAS, no feed health), not license to estimate them. The goal is real data in one
place — push to connect, never to guess.

### Google Ads detection (do this carefully)
1. Call `list_accessible_customers` → list customer ids. If several, ask which account runs campaigns
   (and which is the MCC / `login_customer_id`).
2. Run a small GAQL via `search` to read account currency + time zone:
   `SELECT customer.currency_code, customer.time_zone FROM customer`
3. Pull conversion actions (used by `measurement` later). Select name, category, primary_for_goal,
   counting_type, status FROM conversion_action WHERE status = 'ENABLED'.
   (Note: some MCPs reject `conversion_action.type` as a field — omit it if you get a field error.)
   **Capture verbatim. DO NOT judge whether a primary/secondary flag is "correct" here — that is
   `measurement`'s job, and only after a holistic check.** A "wrong" primary may be harmless if no
   campaign uses it; a second purchase action may be an intentional non-double-counting setup. Setup
   records the facts; it does not raise alarms about them.
4. **`api_write`**: default `false`. Most Google Ads MCPs expose read-only GAQL. Only set `true` if a
   mutate/write tool is actually present. This flag controls whether `pusher` may auto-create later.

---

## STEP 2 — Interview (fill the gaps detection can't)

**Derive first, then confirm — don't just ask.** For anything that exists in the data, pull a value,
show it, and ask the user to confirm or correct. Only ask cold when nothing is derivable. Offer smart
defaults from `${CLAUDE_PLUGIN_ROOT}/references/vertical-defaults.md` based on the vertical.

1. **Business**: name, vertical, model, primary market, languages.
   **AOV — derive it properly (see `${CLAUDE_PLUGIN_ROOT}/references/aov-and-sales-sourcing.md`).** Do NOT shortcut via Google
   Ads: that fails for new/low-spend accounts and is biased otherwise. Priority:
   (a) **Store sales first** — pull orders from the store connector/API and compute AOV from the
       **Online Store channel only**. Exclude draft orders, POS, TikTok/marketplace/social channels,
       cancelled/refunded — they distort AOV and aren't what Google Ads drives. Prefer net sales, 30-90d.
   (b) **Google Ads attributed** only as a cross-check/fallback (`conversions_value / conversions`).
   (c) **Ask** if no orders exist yet. Present the figure with its source + window; user confirms.
2. **Margin tiers** (optional but powerful): if some product lines are high-margin (e.g. house brand),
   capture `{name, gross_margin, min_roas}`. Look in Google Ads (campaign/label structure) for hints,
   then ask the user to confirm the numbers. This lets audit/optimizer avoid false "low ROAS" flags.
3. **Brand**: `brand_terms` (own brand + variants).
   **`competitor_terms` — research the business FIRST, then supplement.** Don't suggest from negatives
   alone (too narrow) or generically (useless). Procedure:
   (a) **Understand the business** — what it sells, niche, market/geo, positioning (from the store, site,
       category structure).
   (b) **Research real competitors** in that niche (web search for "<niche> + competitors / alternatives /
       vs", top retailers in the category and region). Produce a genuine shortlist of named rivals.
   (c) **Supplement from account data** — brand-like negatives (`campaign_criterion` where
       `negative = true`) and auction-insights domains, as additional candidates.
   (d) **Propose, then confirm/prune.** Beware: a negative may exist only to route traffic between the
       account's own campaigns (a brand it DOES sell), not a true competitor — confirm, never auto-add.
4. **Campaign defaults**: **derive the budget context** — list existing active campaign budgets
   (`campaign_budget.amount_micros`) and total daily spend so the user sees the real scale, then ask
   what budget the NEW campaign should start at. Capture target ROAS (null during learning is fine) and
   bidding ramp. (This scale figure matters: the builder must not assume a small account.)
5. **Guardrails**: any account-specific rule the operator wants enforced (free text + `applies_to`).
   Example: "PMax uses brand exclusion, never brand negatives."
6. **Multi-site?** If the business runs several sites/accounts, ask what is shared (e.g. one customer-match
   list, one GSC) vs split per site, and fill the `shared` block. Otherwise leave `shared.enabled: false`.

Keep it conversational — pre-fill everything you detected, only ask for what's genuinely unknown.

---

## STEP 3 — Assemble & confirm

1. Start from `${CLAUDE_PLUGIN_ROOT}/templates/account-context.yaml`.
2. Fill every field you have; leave unknowns blank/null (don't guess).
3. Show the user the assembled YAML and a short summary of what's set vs missing.
4. On confirmation, write `./account-context.yaml`.

---

## STEP 4 — Validate & report health

Run the validator:

```
python ${CLAUDE_PLUGIN_ROOT}/skills/setup/scripts/validate_context.py ./account-context.yaml
```

It checks schema/types/enums and prints readiness per stage:
- **setup-complete** — business + data_source + google_ads core present.
- **measurement-ready** — ≥1 primary purchase/lead conversion action.
- **plan-ready** — AOV (or live data) + a starting budget.
- **build-ready** — brand_terms present; guardrails reviewed.

Surface the report to the user and tell them the next step (usually `audit`, then `measurement`).

---

## Done when
- `./account-context.yaml` exists, validates, and the user has confirmed the detected values.
- The health report clearly lists any still-missing fields and which downstream skill needs them.
