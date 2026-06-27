---
name: google-ads-assets
description: >
  Generates Google Ads creative assets shared across campaign types: responsive search ad headlines and
  descriptions, Performance Max asset-group copy and search themes, Demand Gen image/video briefs, and
  sitelinks/callouts. Enforces character limits, brand voice from account-context.yaml, and policy/
  trademark safety. Use when the user says "ad copy", "headlines", "descriptions", "assets", "creative",
  "rsa", "asset group copy", "sitelinks", "callouts".
---

# Google Ads — Assets (shared creative)

One creative generator used by every builder, so copy rules and voice live in one place. Reads
`account-context.yaml` (voice, brand, offers, vertical) and the data source (best sellers, real prices).

## Operating rules
- Pull voice/positioning/offers from context — no generic filler, no off-brand claims.
- Enforce character limits and policy/trademark rules. Never put a competitor trademark in ad text.
- Use REAL product names/prices/stock from the data source; don't invent.

## Model dispatch (run cheap, decide expensive) — see `${CLAUDE_PLUGIN_ROOT}/references/model-tier-dispatch.md`
- **Scout (`haiku`)** — pulling real product names/prices/stock from the data source; the Google-accurate char-count + ready-to-copy wrapping pass.
- **Judge (main session)** — **all copywriting** (headlines, descriptions, long headlines, search themes, sitelinks, briefs), voice/positioning, policy/trademark safety, pin discipline. Creative is the one thing that never goes to a cheap tier; only the *inputs* (product facts) and the *validation* (char count) do.

## STEP 1 — RSA (Search / Branded)
Per ad group: up to **15 headlines (≤30)** and **4 descriptions (≤90)**, themed to the ad group's intent.
Mix angles: keyword/intent · offer (shipping, selection, in-stock) · qualifier (professional/wholesale/
bulk or value, per vertical) · best-seller names · trust/social proof · CTA. Pin only must-include/legal
claims (over-pinning kills RSA flexibility). Aim for Good/Excellent ad strength.

## STEP 2 — PMax asset-group copy
Per asset group: **15 headlines (≤30)**, **5 long headlines (≤90)**, **5 descriptions (≤90; #1 ≤60)**, and
up to **50 search themes** (raised from 25 in 2025; distinct per AG, no overlap). Use the angle mix in
`${CLAUDE_PLUGIN_ROOT}/references/pmax-best-practices.md`.

## STEP 3 — Demand Gen briefs
Image + video briefs by spec (sizes + shot list + CTA). Combined image+video outperforms video-only.
Provide concrete direction (subject, context, composition, lighting, on-screen text/CTA) per format.

## STEP 4 — Extensions
Sitelinks (text ≤25; two descriptions ≤35 each; live URL), callouts (≤25), structured snippets (value ≤25).
**Level depends on campaign type:** in **PMax** these attach at the **campaign** level (`spec.extensions`),
never the asset group. In **Search**, they may be campaign- or ad-group-level (ad-group only when groups
differ enough to warrant distinct links). See `builder-pmax` STEP 7b.

## Validation
**Count characters the Google way** (NFC-normalized, CJK/full-width = 2, no trailing/hidden whitespace) per
`${CLAUDE_PLUGIN_ROOT}/references/google-ads-formatting.md` — not naive `len()`, which lets copy pass here but get rejected on
entry. Flag off-brand/banned phrasing or competitor trademark in text; confirm product references are real
(in stock, correct price). Keywords/negatives come back **ready-to-copy wrapped** (`[exact]` / `"phrase"` /
broad). Return assets keyed by campaign type + group for the builder to drop into `campaign-spec.json`.

## To build / refine later
- [ ] Optional AI image generation hook for Demand Gen / PMax visuals.
- [ ] Shared char-limit/policy validator reused by builders.
