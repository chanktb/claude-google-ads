# Google Ads audit — full check catalog (G01–G61 + extensions)

80 checks across 6 scored categories (PMax / AI Max / Demand Gen / CTV are scored *within* their parent
category). Severity drives the weighted score (`scoring-system.md`). Apply GUARD-1…6 (in SKILL.md) so no
check fires on an unverified assumption. "Verify-in-UI" items are NOT scored as FAIL.

| Category | Weight | Checks |
|----------|--------|--------|
| Conversion Tracking | 25% | G42–G49, G-CT1–G-CT3, G-CTV1 |
| Wasted Spend / Negatives | 20% | G13–G19, G-WS1 |
| Account Structure | 15% | G01–G12 |
| Keywords & Quality Score | 15% | G20–G25, G-KW1–G-KW2 |
| Ads & Assets | 15% | G26–G35, G-AD1–G-AD2, G-PM1–G-PM6, G-AI1, G-DG1–G-DG3 |
| Settings & Targeting | 10% | G36–G41 (bidding), G50–G61 |

---

## Conversion Tracking (25%)
| ID | Check | Sev | Pass / Warning / Fail |
|----|-------|-----|-----------------------|
| G42 | Conversion actions defined | Critical | ≥1 primary action / — / none active |
| G43 | Enhanced Conversions | Critical | active + verified (~10% uplift) / enabled-unverified / off · **verify-in-UI** |
| G44 | Server-side tracking | High | server-side GTM / API import active / planned / none |
| G45 | Consent Mode v2 | Critical | Advanced (EEA) / Basic only / not implemented · **verify-in-UI** |
| G46 | Conversion window matches sales cycle | Medium | matched (7d ecom, 30-90d B2B) / default unvalidated / mismatched |
| G47 | Micro vs macro separation | High | only macro (Purchase/Lead) primary / some micro primary / all micro primary |
| G48 | Attribution model | Medium | data-driven / Last Click (documented) / legacy rule-based |
| G49 | Conversion value assignment | High | dynamic (ecom) / static / none |
| G-CT1 | No duplicate counting | Critical | not double-counted / — / both GA4 import + native tag count same action |
| G-CT2 | GA4 linked & flowing | High | linked, data flows / discrepancies / not linked |
| G-CT3 | Google Tag firing | Critical | firing all pages / >90% / missing on key pages · **verify-in-UI** |
| G-CTV1 | CTV measurement | High | non-Floodlight (Floodlight doesn't work on CTV) / unverified / relies on Floodlight |

**GUARD-1 accuracy (G47 / G-CT1) — the holistic conversion check:** Do not flag from the account action
list alone. (1) Smart Bidding optimizes on the **campaign-level conversion goal**
(`campaign_conversion_goal` / `selective_optimization.conversion_actions`), not the account "Primary"
flag — if a campaign optimizes only on Purchase, do NOT flag G47 even if account-level has micro primaries.
(2) Two `PURCHASE` actions in parallel (e.g. a store *Google & YouTube channel* "App Purchase" + a GA4-import
purchase) is the CORRECT anti-double-count setup — only flag G-CT1 FAIL if BOTH are `primary_for_goal=true`
and both fire in the same campaigns. (3) Only ENABLED actions; exclude HIDDEN/REMOVED and Smart-Campaign
system-managed actions (locked attribution/counting). (4) **Before flagging any out-of-brand / micro /
duplicate action, check `primary_for_goal`** — a NON-primary action does not enter Smart Bidding and is
harmless (surface as a tidy-up NOTE, not a scored finding); only a PRIMARY one an active campaign optimizes
toward is real. See `${CLAUDE_PLUGIN_ROOT}/references/conversion-tracking-logic.md`.

---

## Wasted Spend / Negatives (20%)
| ID | Check | Sev | Pass / Warning / Fail |
|----|-------|-----|-----------------------|
| G13 | Search-term audit recency | Critical | ≤14d / ≤30d / >30d |
| G14 | Negative keyword lists exist | Critical | ≥3 themed lists / 1–2 / none |
| G15 | Account-level negatives applied | High | account/all-campaign / some / none |
| G16 | Wasted spend on irrelevant terms | Critical | <5% / 5–15% / >15% (30d) |
| G17 | Broad match + Smart Bidding pairing | Critical | no broad on Manual CPC / — / broad + Manual CPC |
| G18 | Close-variant pollution | High | clean / minor / significant irrelevant spend |
| G19 | Search-term visibility | Medium | >60% visible / 40–60% / <40% |
| G-WS1 | Zero-conversion keywords | High | none >100 clicks 0 conv / 1–3 / >3 |

**GUARD-2 (G14/G15):** count campaign-level negatives AND shared negative lists; don't flag a gap a shared
list covers. **(G16/G-WS1):** only flag a term "wasted" if >$10 spend AND 0 conversions (sub-$10 long-tail
= normal exploration). **(G17 legacy BMM):** BROAD + Manual CPC = legacy BMM (behaves as phrase) — do NOT
flag; only review BROAD on Smart Bidding. **(G19):** compute visible spend over ALL fetched terms (cost
DESC), not a truncated top-N. Respect the "what NOT to block" rules in `optimization-playbook.md`.

---

## Account Structure (15%)
| ID | Check | Sev | Pass / Warning / Fail |
|----|-------|-----|-----------------------|
| G01 | Campaign naming convention | Medium | consistent / partial / none |
| G02 | Ad group naming convention | Medium | consistent / partial / none |
| G03 | Single-theme ad groups | High | ≤10 kw, one theme / 11–20 / 20+ unrelated |
| G04 | Campaign count per objective | High | ≤5 / 6–8 / >8 (fragmented) |
| G05 | Brand vs non-brand separation | Critical | separated / — / mixed |
| G06 | PMax present for eligible accounts | Medium | active w/ conv history / paused / not tested |
| G07 | Search + PMax overlap | High | brand exclusions in PMax / partial / none |
| G08 | Budget matches priority | High | top performers not capped / minor / severely capped |
| G09 | Daily budget vs spend | Medium | no early cap / 1–2 cap early / many cap before noon |
| G10 | Ad schedule configured | Low | set if business hours / — / none despite hours |
| G11 | Geographic targeting | High | "Presence" for local / — / "Presence or Interest" for local |
| G12 | Network settings | High | Search Partners on, Display off for Search / partners off / Display on for Search |

**Accuracy:** (G03) count only impression>0 keywords, ENABLED ad groups, dedupe by text; (G04) strip geo
identifiers before counting objectives; (G05/G07) derive brand tokens from `brand_terms` + scan keyword
text, don't trust names alone (>50% brand keywords = brand campaign). **(G07/G-PM3) VERIFY brand blocking
before flagging:** pull the PMax campaigns' campaign-level negative keywords AND brand exclusion list, check
whether `brand_terms` are actually blocked. If blocked → PASS, re-score; only flag if genuinely unblocked
(corroborate with G-PM3: >15% of PMax conversions on brand terms). Don't just say "confirm exclusion".
**Brand-token matching must use WORD BOUNDARIES, never naive substring** — a reseller's product brands
often CONTAIN the own brand as a substring (e.g. own brand "AB" sits inside resold "F**AB**" / "C**AB**"; or
a short brand inside an unrelated word). A substring match counts resold-product searches as own-brand cannibalization and inflates
G-PM3 (e.g. "dnd nail polish" is product-category intent, not the advertiser's brand). Match on token/word
boundaries and exclude known resold product-brand names before computing brand share.

---

## Keywords & Quality Score (15%)
| ID | Check | Sev | Pass / Warning / Fail |
|----|-------|-----|-----------------------|
| G20 | Avg Quality Score (impression-weighted) | High | ≥7 / 5–6 / ≤4 |
| G21 | Critical-QS keywords | Critical | <10% QS≤3 / 10–25% / >25% |
| G22 | Expected CTR component | High | <20% Below Avg / 20–35% / >35% |
| G23 | Ad relevance component | High | <20% Below Avg / 20–35% / >35% |
| G24 | Landing page experience | High | <15% Below Avg / 15–30% / >30% |
| G25 | Top-keyword QS | Medium | top-20 spend all ≥7 / some 5–6 / any ≤4 |
| G-KW1 | Zero-impression keywords | Medium | none 30d / <10% / >10% |
| G-KW2 | Keyword-to-ad relevance | High | headlines contain keyword variants / partial / none |

---

## Ads & Assets (15%)
| ID | Check | Sev | Pass / Warning / Fail |
|----|-------|-----|-----------------------|
| G26 | RSA per ad group | High | ≥1 (≥2 rec) / 1 / none |
| G27 | RSA headline count | High | ≥8 (ideal 12–15) / 3–7 / <3 |
| G28 | RSA description count | Medium | ≥3 (ideal 4) / 2 / <2 |
| G29 | RSA Ad Strength | High | Good/Excellent / Average / any Poor |
| G30 | RSA pinning | Medium | strategic / over-pinned / — |
| G31 | PMax asset density | Critical | ≥20 img/≥5 logo/≥5 video + ≥30 conv/mo / partial / <5 img or 0 logo/video |
| G32 | PMax video formats | High | 16:9+1:1+9:16 native / 1–2 formats / none native |
| G33 | PMax asset-group count | Medium | ≥2 intent-segmented / 1 / — |
| G34 | PMax Final URL Expansion | High | intentional / — / default ON unreviewed |
| G35 | Ad copy relevance | High | keyword variants in headlines / partial / none |
| G-AD1 | Ad freshness | Medium | new copy <90d / — / none >90d |
| G-AD2 | CTR vs benchmark | High | ≥ industry avg / 50–100% / <50% |
| G-PM1 | PMax audience signals | High | custom per AG / generic / none |
| G-PM2 | PMax Ad Strength | High | Good/Excellent / Average / Poor |
| G-PM3 | PMax brand cannibalization | High | <15% conv from brand / 15–30% / >30% (use brand exclusion) |
| G-PM4 | PMax search themes | Medium | configured (up to 50/AG) / <5 / none |
| G-PM5 | PMax negatives (brand+irrelevant) | High | applied / some / none |
| G-PM6 | PMax campaign-level negatives | High | configured / account-only / none |
| G-AI1 | AI Max for Search evaluated | High | evaluated/active w/ strong negatives / — / not evaluated despite eligible |
| G-DG1 | Demand Gen image+video mix | High | both / video-only / no DG despite eligible |
| G-DG2 | VAC → Demand Gen migration | Critical | migrated / in progress / VAC still active |
| G-DG3 | DG frequency-cap loss handled | High | alt measurement / not monitored / relied on lost freq caps |

---

## Settings & Targeting (10%)
**Bidding & budget:**
| ID | Check | Sev | Pass / Warning / Fail |
|----|-------|-----|-----------------------|
| G36 | Smart Bidding active | High | all ≥15 conv/30d automated (ECPC deprecated Mar 2025) / partial or ECPC present / Manual CPC w/ data |
| G37 | Target CPA/ROAS reasonable | Critical | within 20% historical / 20–50% off / target <50% of actual |
| G38 | Learning-phase status | High | <25% learning / 25–40% / >40% |
| G39 | Budget-constrained campaigns | High | top "Eligible" / minor / severely "Limited by Budget" |
| G40 | Manual CPC justification | Medium | only <15 conv/mo / 15–30 / >30 |
| G41 | Portfolio bid strategies | Medium | low-volume grouped / — / many <15-conv running solo |

**Extensions, audiences, landing pages:**
| ID | Check | Sev | Pass / Warning / Fail |
|----|-------|-----|-----------------------|
| G50 | Sitelinks | High | ≥4/campaign / 1–3 / none |
| G51 | Callouts | Medium | ≥4 / 1–3 / none |
| G52 | Structured snippets | Medium | ≥1 set / — / none |
| G53 | Image extensions | Medium | active / — / none |
| G54 | Call extensions (if phone biz) | Medium | w/ tracking / no tracking / none |
| G55 | Lead form extensions (lead gen) | Low | tested / — / not tested |
| G56 | Audience segments (Observation) | High | remarketing + in-market / some / none |
| G57 | Customer Match lists | High | uploaded, <30d fresh / >30d old / none |
| G58 | Placement exclusions | High | account-level (games/apps/MFA) / campaign-only / none |
| G59 | Landing page mobile speed | High | LCP <2.5s / 2.5–4.0s / >4.0s |
| G60 | Landing page relevance | High | H1/title matches ad group / partial / none |
| G61 | Landing page schema | Medium | Product/FAQ/Service / — / none |

---

## Quick Wins (Critical/High AND <15 min)
| Check | Fix | Time |
|-------|-----|------|
| G43 | Enable Enhanced Conversions | 5 min |
| G11 | Switch location to "Presence" | 2 min |
| G14 | Create themed negative lists | 10 min |
| G17 | Move broad to Smart Bidding / Exact | 5 min |
| G12 | Disable Display on Search | 2 min |
| G05 | Split brand into its own campaign | 10 min |
| G50 | Add 4+ sitelinks | 10 min |
| G-PM6 | Add campaign-level negatives to PMax | 10 min |

## 2026 context notes
- ECPC fully deprecated (Mar 2025) → tCPA/tROAS/Max Conversions. Any ECPC = FAIL.
- Call campaigns: no new ones since Feb 2026; existing serve until Feb 2027 → migrate to Search + call assets.
- VAC auto-upgraded to Demand Gen (Apr 2026). Demand Gen has NO frequency capping.
- AI Max for Search: ~14% conv lift; needs strong negative lists first; DSA likely consolidating into it.
- PMax search themes raised to 50/asset group (2025). Brand exclusion + campaign-level negatives available to all.
