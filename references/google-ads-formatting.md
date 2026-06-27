# Google Ads formatting — character counting, ready-to-copy keywords, final URLs

Reusable, business-agnostic reference. Fixes the recurring real-world problems: copy that "counts right"
but Google rejects, negatives that aren't paste-ready, and wrong landing pages per asset group.
Sources at the bottom.

## 1. How Google counts characters (match this exactly, or copy gets rejected)
Google counts by **Unicode code point**, with these rules:
- **Double-width characters count as 2.** Chinese/Japanese/Korean and other East-Asian *wide/fullwidth*
  glyphs (Unicode East_Asian_Width W or F) each count as 2. A 30-char headline ≈ 15 CJK characters.
- **Spaces, punctuation, symbols all count** (em-dash `—`, smart quotes `" " ' '`, ellipsis `…` = 1 code
  point each — fine).
- **Leading/trailing whitespace counts** — the #1 cause of "looks fine but exceeds." Always trim.
- **Hidden characters count** — non-breaking spaces (U+00A0), zero-width joiners, and control characters
  pasted from Word/Docs/PDF silently push copy over. Strip/normalize them.
- **Combining accents**: a decomposed `é` (e + U+0301) counts as 2 code points though it looks like 1.
  **Normalize to NFC** so it counts as 1.

Practical counting algorithm (what `validate_spec.py` now does):
```
glen(s) = sum over chars of (2 if East_Asian_Width in {W,F} else 1),
          after NFC-normalizing and trimming leading/trailing whitespace.
Also flag any U+00A0 / control / zero-width chars as hidden (remove them).
```
Python `len()` ≈ code points for plain ASCII, but it does NOT double-count CJK, does NOT trim, and does
NOT normalize — so the old skill passed copy that Google then rejected. `glen()` matches Google.

## 2. Exact character limits (2026)
| Asset | Min–Max count | Char limit |
|-------|---------------|-----------|
| RSA headline | 3–15 | 30 |
| RSA description | 2–4 | 90 |
| RSA path (×2) | 0–2 | 15 each |
| PMax headline | 3–15 | 30 |
| PMax long headline | 1–5 | 90 |
| PMax description | 1–5 | 90 (the first/"short" description shows a **60** cap on some surfaces — keep #1 ≤60 to be safe) |
| PMax search themes | up to **50** per asset group (raised from 25 in 2025) | short phrases |
| Business name | 1 | 25 |
| Sitelink text | ≥2 sitelinks | 25 |
| Sitelink description 1 & 2 | — | 35 each |
| Callout | ≥2 | 25 |

## 3. Ready-to-copy keyword & negative format (paste straight into UI/Editor)
Wrap by match type, ONE per line, grouped. The Google Ads UI and Editor both parse these wrappers:
- **Exact** → `[keyword]`
- **Phrase** → `"keyword"`
- **Broad** → `keyword` (no wrapper)
- **Negatives** use the SAME wrappers (in the negative section). Default negative = broad if unwrapped.

So every keyword/negative output block must already carry the wrapper — never a bare list the user has to
re-format. `spec_to_paste.py` renders these blocks per ad group + campaign negatives + PMax search themes.

## 4. Final URL per asset group / ad group (don't guess, don't use the homepage)
- Map each group to the **most specific live category/collection page** for its products — never the
  homepage (the FIGS rule: "Women's Scrubs" group → /womens-scrubs, not /).
- **Verify the URL is live**: HTTP 200, no redirect chain, no 404, mobile-friendly. Pull candidates from
  the data-source catalog or sitemap; HEAD-check before it enters the spec.
- Keep it **consistent with the listing group** (the AG's products and its landing page must match).
- PMax: **Final URL Expansion OFF** so the asset-group URL is authoritative (else Google reroutes traffic).
- If no specific page exists, flag it — don't silently fall back to a generic page.

## 5. PMax negatives & search themes
- PMax negative keywords are **campaign-level** (available to all advertisers) — format with the wrappers
  above. They are NOT per-asset-group.
- **Search themes** are per-asset-group (up to 50), additive hints toward queries — short phrases, no
  match-type wrappers.

## Sources
- [About responsive search ads — Google Ads Help](https://support.google.com/google-ads/answer/7684791)
- [About text assets for Performance Max — Google Ads Help](https://support.google.com/google-ads/answer/14528373)
- [Google Ads Character Limits 2026 — TypeCount](https://typecount.com/blog/google-ads-character-limit)
- [About keyword matching options — Google Ads Help](https://support.google.com/google-ads/answer/7478529)
- [Performance Max ecommerce guide 2026 — Store Growers](https://www.storegrowers.com/performance-max-campaigns/)
- [PMax asset specs 2026 — AdNabu](https://blog.adnabu.com/google-ads/performance-max-ad-specs/)
