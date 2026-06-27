# Conversion tracking logic — sources, double-count, holistic check

Reusable, business-agnostic reference for the `measurement` (and `audit`) skills. The recurring mistake is
concluding a conversion setup is broken from the action list alone. Don't. Use the source matrix and the
holistic procedure below.

## Source matrix (where a purchase/lead conversion can come from)
A single store often has SEVERAL purchase conversion actions from different sources. They are not
duplicates by default — the question is which are **primary** and which actually **fire in campaigns**.

| Source | Typical action name | Notes |
|---|---|---|
| Shopify **Google & YouTube channel** (auto) | "Google Shopping App Purchase" | The channel's own conversion; commonly the legitimate primary for Shopping/PMax. |
| **GA4 import** | "<domain> - GA4 (web) purchase" | Imported from GA4. If kept primary ALONGSIDE the channel purchase -> double count. Secondary is the safe anti-double-count setup. |
| **gtag / GTM** site tag | custom purchase | Another web-side source; same double-count caveat vs GA4 import. |
| **Merchant Center** | store sales | Separate surface. |
| Engagement / local / calls | menu views, directions, calls, store visits | Often auto-created and flagged primary; usually harmless if no campaign optimizes for them. |

## Double-count rule
Two value-carrying purchase actions are a problem **only if both are PRIMARY and both fire in the same
campaigns**. One primary + one secondary (or one unused) is correct, not a bug.

## Holistic check procedure (do all four before any verdict)
1. **Actions**: enabled conversion actions with name, category, primary_for_goal, counting_type, source.
2. **Usage**: segment conversions by `segments.conversion_action_name` per active campaign over 30-90 days
   — this reveals which actions campaigns *actually* optimize toward. An action no campaign fires is inert.
3. **Source & double-count**: map each value-carrying action to a source; check for two primaries firing
   together.
4. **Verdict**: apply the "what is / isn't a problem" rules in the measurement skill. Output harmless
   findings as notes; reserve FAIL for genuine 🔴 cases.

## Worked example (why isolation lies)
An account shows ~20 ENABLED actions; many engagement actions are `primary_for_goal = true`, and the GA4
web purchase is `primary_for_goal = false`. Read in isolation this looks broken ("real purchase isn't
primary!"). But the per-campaign segmentation shows **every active campaign converts only via the channel
"App Purchase"**, and none fire the engagement actions. Verdict: **healthy** — the channel purchase is the
working primary, the GA4 purchase is correctly secondary (anti-double-count), and the engagement primaries
are inert. The isolated read would have raised a false alarm.
