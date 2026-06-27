# claude-google-ads

**Find where your Google Ads budget leaks, cut the waste, and scale your store with ads — safely.**

A Claude Code **plugin** that operates Google Ads end-to-end for **ecommerce** advertisers — any niche,
brand, or store (retail B2C, wholesale/B2B2C, DTC), not tied to one. It runs on your real account data
(never guesses), hunts the money leaks most accounts never see, and **never touches your account without your
approval** — it creates campaigns paused, caps spend, and respects bidding cooldowns.

Built by [Khue Tran](https://khuetran.com).

> **Scope:** built for **ecommerce / Shopping advertisers** — it assumes a product catalog, store revenue,
> AOV, and ROAS/value-based bidding (PMax/Shopping, Merchant Center). It is **not** built for leadgen, SaaS,
> or local-service accounts (no CPA/CRM/lead-value paths). Within ecommerce it is brand- and niche-agnostic.

> **Design principle:** every store is just one `account-context.yaml`. All business-specific facts
> (accounts, data source, brand terms, margins, guardrails, retail-vs-wholesale model) live in that file. The
> skills stay generic across ecommerce — fill a new context file and the whole suite works for a new store.

## Status

**Published and stable** (v0.1.0). Installable from GitHub — see [Install](#install) below. Active
development continues; see [`CHANGELOG.md`](CHANGELOG.md) for release history and what's new in each version.

## Architecture

```
/google-ads  ->  ROUTER skill (reads account-context, routes to the right sub-skill)
│
├─ PIPELINE (campaign lifecycle)
│   ├─ setup         -> produces account-context.yaml (MCP-agnostic; shared vs per-site)
│   ├─ measurement   -> validates conversion tracking            [GATE before plan/build]
│   ├─ audit         -> scores the account (forked from ads-google)
│   ├─ plan          -> budget + campaign mix + full launch roadmap
│   ├─ builder-*     -> per type: search / branded-search / pmax / demand-gen
│   ├─ pusher        -> Editor CSV export + approval gate + spend cap   [SAFETY]
│   ├─ tracker       -> monitor learning phase, pacing, anomalies (observe only)
│   └─ optimizer     -> act: search-term mining, budget/tROAS, asset refresh
│
├─ CROSS-CUTTING (shared by multiple skills)
│   ├─ assets        -> RSA / PMax asset group / image-video briefs
│   └─ experiments   -> A/B split design (campaign level + asset-group level)
│
├─ references/       -> ecommerce KB (brand/niche-agnostic): benchmarks, policy, char limits, bidding playbooks
└─ templates/account-context.yaml  -> the reusable backbone
```

## The skills (15) — what each one does

Each is a standalone slash command (e.g. `/google-ads-audit`); `/google-ads` routes you to the right one.

**① Start here (2):**
| Skill | Command | What it does |
|---|---|---|
| **google-ads** (router) | `/google-ads` | The entry point — checks your connections, tells you where you are in the lifecycle, runs the right step next. |
| **setup** | `/google-ads-setup` | Connects every data source into one registry and builds `account-context.yaml` (the backbone every skill reads). |

**② Diagnose & fix waste (the core value) (3):**
| Skill | Command | What it does |
|---|---|---|
| **measurement** | `/google-ads-measurement` | Validates conversion tracking holistically before you spend — primary/secondary, double-count, value cross-check (Ads vs GA4 vs store). The gate that blocks planning on broken tracking. |
| **audit** | `/google-ads-audit` | Scores the account and runs the **money-leak engine (D1–D14)** — bid/target health, geo & dayparting waste, 0-conversion products, PMax channel burn, weak assets/extensions, structure, Quality Score, feed health. Ranks leaks by $/month. |
| **optimizer** | `/google-ads-optimize` | Acts on the findings: search-term mining → negatives, geo/product exclusions, budget reallocation, target-ROAS steps, pausing dead weight. Emits a safe **change-set** with the Scaling Ladder discipline. |

**③ Plan & build campaigns (6):**
| Skill | Command | What it does |
|---|---|---|
| **plan** | `/google-ads-plan` | Budget split, campaign mix, learning-phase math, and a forecast from your real CPC/CVR/AOV. |
| **builder-pmax** | `/google-ads-pmax` | A complete Performance Max blueprint — split strategy, asset groups, listing groups, copy & search themes (grounded in converting data), audience signals, extensions, real price assets. |
| **builder-search** | `/google-ads-search` | A non-brand Search campaign that **harvests the proven converters PMax discovered** into exact-match control. |
| **builder-branded-search** | `/google-ads-branded` | Brand defense (Target Impression Share) + trademark-safe competitor conquesting, as separate campaigns. |
| **builder-demand-gen** | `/google-ads-demandgen` | Top-funnel YouTube/Discover/Gmail prospecting + retargeting with audience-led creative. |
| **assets** | `/google-ads-assets` | The shared creative generator (RSAs, PMax copy, image/video briefs, extensions) — char limits, brand voice, trademark safety, real products. |

**④ Push, monitor & operate (4):**
| Skill | Command | What it does |
|---|---|---|
| **pusher** | `/google-ads-push` | Exports the build (Editor CSV) or change-set (CHANGE-PLAN) — **always paused on create, behind an approval gate, with a spend cap**. Read-only-MCP friendly. |
| **tracker** | `/google-ads-track` | Observes learning phase, pacing, and anomalies (changes nothing). |
| **experiments** | `/google-ads-experiment` | Designs disciplined A/B tests with a **feasibility gate** — refuses tests too small to conclude. |
| **routine** | `/google-ads-routine` | The daily / weekly / monthly operating rhythm — calls tracker + optimizer at the right cadence and surfaces what's DUE / OVERDUE. |

## Locked structural decisions

1. **Distribution = plugin** (multiple independently-invokable skills), not a single mega-skill.
2. **`tracker` (observe) and `optimizer` (act) are separate skills** — different responsibilities.
3. **`pusher` v1 = Google Ads Editor CSV + human approval gate.** Auto-create via API is v2, gated on
   `google_ads.api_write: true` in the context. Most Google Ads MCPs are read-only.
4. **`account-context.yaml` is the single source of business truth.** No business detail is hardcoded
   in any skill.

## Prerequisites — connect your data FIRST

The suite runs on **real account data, never guesses.** Set these up before using the skills (`setup`
inventories them and tells you what's missing). It works on what you connect and flags the rest
`UNVERIFIED` — it will not fabricate a number to fill a gap.

| Connection | Tier | Gives you |
|---|---|---|
| **Google Ads** — a read-only GAQL MCP | **MANDATORY** | everything (audit, money-leak diagnostics, builders) |
| **Store** — Shopify / WooCommerce / BigCommerce (an MCP, or an Admin token in a local `.env`) | required for full value | real AOV, true-ROAS ground truth, live landing-page checks, catalog for builders |
| **Merchant Center** — Content-API connector | required (ecom) | product-feed health: out-of-stock / disapprovals / GTIN (the biggest ROAS lever) |
| **GA4** — an MCP or a GA4 client + property id | recommended | Ads-vs-GA4 value cross-check, channel mix |
| **GSC** — Search Console connector | optional | organic cross-read |

Without **Google Ads** nothing runs. Without **Store / Merchant / GA4** the core audit still works (off the
Google Ads MCP), but AOV, true-ROAS, feed health, and the value cross-check render `UNVERIFIED` until you
connect them. `/google-ads` checks this up front and guides you.

## Install

```
/plugin install claude-google-ads@chanktb/claude-google-ads
```

Then run `/google-ads` — it checks your connections, runs `setup` if there's no context, and points you to
the next step.

**Full usage guide (what to prepare, the command for each job, a first-run walkthrough):**
[`docs/USAGE.md`](docs/USAGE.md).
