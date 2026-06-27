# Per-Campaign Report Template (the deep-dive blueprint)

The audit is **per-campaign deep-dives**, not a generic account summary. Every money-leak is localized to
the campaign it lives in (why + where + $), with a visual block per campaign. Only genuinely account-level
items go in the overview. Final document order: **Account Overview → one rich block per active campaign →
Action Plan**.

Render contract: each campaign produces ONE self-contained HTML block (visual + charts). The generator
concatenates `account_overview + Σ(campaign_block) + action_plan` into one big `AUDIT.html`.

**Visual-explainer rule (every item = 3 steps): ① DATA shown → ② VERDICT (GOOD / WATCH / FIX / VERIFY) →
③ ACTION (only if needed).** Each quantitative metric renders as its own CHART, not text:
- ROAS vs target → **semicircle gauge** (fill = ROAS, tick = target)
- Budget pacing → **radial ring** (spend ÷ budget/day)
- Channel mix → **donut** (Search/Shopping vs other surfaces)
- Device, Geo → **horizontal bars** colored by ROAS (green/amber/red vs the campaign's own ROAS)
- Schedule → **24-hour heatmap** (cell color = ROAS that hour; gray = off/low spend)
- Extension/signal counts → **meter bars** (vs the recommended count)
Each campaign card carries a **scorecard** (N good · N watch · N fix · N verify). The account panel lists
EVERY account-level setting (tracking, Consent, account/brand negatives, Content Suitability, structure,
conversion-lag) the same way — data → verdict → action. No separate "money-leak summary" block: the leak IS
the verdict+action on the relevant section, evaluated inline. Style is flat/modern (no heavy gradients).

---

## A. Account Overview (top — ONLY account-level things)
Truly account-wide; never duplicate per campaign.
- **Health score** donut + grade + the 6 weighted category bars (from `audit-result.json`).
- **KPIs**: spend, blended ROAS, total conv value, # active campaigns, quantified opportunity/mo.
- **Account-level findings only**: Enhanced Conversions recording · Consent Mode v2 · account-level
  placement-exclusion lists & Content Suitability · conversion-lag trust gate (if account-wide) ·
  structural gaps that span campaigns (e.g. "no dedicated non-brand Search campaign") · cross-campaign
  **budget misallocation** (move $ from low-ROAS camp → high-ROAS camp; names both, lives here because it's
  a reallocation *between* camps).
- **Leak map**: $/mo bar chart, each bar tagged with the campaign it belongs to.

## B. Per-Campaign Block (repeat for every active campaign)
Each block is a campaign's full story. Sections (mark every field **[API]** read-live or **[UI]**
verify-in-UI; never silently omit):

1. **Header** — name · channel-type pill · **decoded `system_status`** pill ([API]) · ROAS-vs-target bar
   with target tick · primary_status (LIMITED reason → [UI]).
2. **Performance** [API] — spend → conv value, conversions, budget/day vs spend/day, budget utilization,
   tROAS, bid strategy + `bidding_strategy_system_status` decoded (budget-capped vs tROAS-too-high vs
   starved vs learning).
3. **Channel distribution** [API] — `segments.ad_network_type` split bar (Search/Shopping vs YouTube /
   Gmail / Discover / Maps / Display). Name the real surface; flag non-Search 0-conv burn. (Why Display
   does/doesn't burn → Content Suitability / placement exclusions = **[UI]**.)
4. **Device** [API] — device split + ROAS; flag 0-conv device (e.g. Connected TV) to exclude.
5. **Geo** [API] — this campaign's top + bottom regions; 0-conv or weak-ROAS regions to bid-down/exclude;
   Presence-vs-Interest leak (`location_type` 2). Targeting method itself → **[UI]**.
6. **Schedule / dayparting** [API where pulled] — ad-schedule criteria + bid modifiers; weak hours/days.
7. **Products** (ecom) [API perf + Merchant] — this campaign's Shopping/PMax product burners (0-conv,
   ≥clicks) **cross-referenced with Merchant status**: OOS → restock/exclude; in-stock-but-0-conv →
   price/intent. Disapprovals affecting this camp.
8. **Audience signals & search themes** (PMax/DG) [API] — # audience signals, # search themes (list the
   themes); 0 signals = no seed to learn from.
9. **Ad copy / assets** [API] — RSA/PMax **headline + description text** with spend; 0-conv copy (read the
   pattern, don't pause singles); Ad Strength; pin discipline. Asset optimization / text customization /
   text & brand guideline content → **[UI]**.
10. **Extensions** [API counts + text] — sitelinks (link text), callouts (text), structured snippets
    (header:values), price/promo/image/call. Flag thin (<4 sitelinks, <4 callouts, 0 snippets) with the
    **actual current text** so the fix is concrete.
11. **Negatives** [API] — campaign-level negative keywords + attached **shared negative lists** (name +
    sample terms) + brand-exclusion brand lists. Confirms wrong-brand/competitor blocking for THIS camp.
12. **Final URLs / URL expansion** [API for Search final_urls; UI for PMax FUE] — final URLs in use; Final
    URL Expansion on/off + URL exclusions / page feed → **[UI]** for PMax.
13. **Change history** [API] — `change_event` for THIS campaign (30d); cooldown flag (changed <14d → don't
    scale); whipsaw flag (≥3 budget changes/30d).
14. **💸 Money-leak for this campaign** — the localized findings: each leak with **why** (root cause) +
    **where** (which setting/surface/region/product) + **$/mo** + exact fix + discipline + confidence.
15. **Verify-in-UI checklist** (this campaign) — the [UI] items above as explicit checkboxes.

## C. Action Plan (bottom)
Dated, three buckets, each item: what · exact UI/Editor step · why (data) · **which campaign** · $/impact ·
status box. Today (cooldown-safe + 5-min verify wins) · This week (geo/daypart/extensions/negatives) ·
Roadmap (structure: non-brand Search camp, asset diversification, consolidation). Respect Scaling Ladder +
change-event cooldown throughout.

---

## Bundle additions this template needs (extend the PULL MANIFEST)
Existing per-camp keys already cover §1-5,7-9,13 partially: `active_campaigns, channel, device, geo,
assets(headlines), extensions(counts), signals, products, change_events`. Add:
- `ext_text`: `[{campaign_id, field_type, text}]` — sitelink(13)/callout(11)/snippet(12) **text** via
  `campaign_asset` → `asset.sitelink_asset.link_text` / `asset.callout_asset.callout_text` /
  `asset.structured_snippet_asset.header+values`.
- `descriptions`: `[{campaign_id, text, cost_micros, conversions, clicks}]` — `asset_group_asset`
  field_type DESCRIPTION (PMax) + RSA descriptions.
- `negatives`: `[{campaign_id, source, text, match_type}]` — `campaign_criterion` negatives (source
  "campaign") + `campaign_shared_set`→`shared_criterion` (source = list name) + brand-list exclusions.
- `schedule`: `[{campaign_id, day_of_week, start_hour, end_hour, bid_modifier}]` — `campaign_criterion`
  type AD_SCHEDULE.
- `final_urls`: `[{campaign_id, url}]` — `ad_group_ad.ad.final_urls` (Search); PMax FUE = [UI].
- `dayparting` + `conversion_lag`: **re-pull WITH `campaign.id`** so §6 and the lag gate localize per camp.

Anything the read-only API can't see (Content Suitability, text/brand guideline content, asset
optimization toggle, FUE on/off, Enhanced-Conversions recording, Consent-Mode mode, primary_status LIMITED
reason) is rendered as a **[UI] checkbox**, never silently dropped (GUARD-6).
