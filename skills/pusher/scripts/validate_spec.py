#!/usr/bin/env python
"""
validate_spec.py — dry-run validator + safety gate for a campaign-spec.json

Usage:
    python validate_spec.py <campaign-spec.json> [--max-budget N]

Enforces the contract in references/campaign-spec.md. Exit 0 only if there are no ERRORS.
Business-agnostic. The pusher runs this BEFORE any export or API mutation.
"""
import argparse
import json
import re
import sys
import unicodedata

CAMPAIGN_TYPES = {"performance_max", "search", "branded_search", "demand_gen"}
LIMITS = {"headline": 30, "long_headline": 90, "description": 90, "sitelink_text": 25, "sitelink_desc": 35,
          "callout": 25, "snippet_value": 25}
MAXN = {"headlines": 15, "long_headlines": 5, "descriptions": 5, "search_themes": 50}
# Google's fixed structured-snippet header list (can change over time — warn, don't hard-fail).
SNIPPET_HEADERS = {"Amenities", "Brands", "Courses", "Degree programs", "Destinations", "Featured hotels",
                   "Insurance coverage", "Models", "Neighborhoods", "Service catalog", "Shows", "Styles", "Types"}
# Google's price-asset types + per-item char limits.
PRICE_TYPES = {"Brands", "Events", "Locations", "Neighborhoods", "Product categories", "Product tiers",
               "Services", "Service categories", "Service tiers"}
LIMITS.update({"price_header": 25, "price_desc": 25})

errors, warns = [], []
def err(m): errors.append(m)
def warn(m): warns.append(m)


def glen(s):
    """Character length the way Google counts: NFC-normalized, trimmed, CJK/full-width = 2."""
    s = unicodedata.normalize("NFC", str(s or "")).strip()
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def hidden(s):
    """Hidden/illegal chars that silently push copy over Google's limit."""
    return [hex(ord(c)) for c in str(s or "")
            if c == " " or unicodedata.category(c) in ("Cc", "Cf")]


def over(text, limit, name):
    """Flag a char-limit overflow (Google-accurate) + any hidden chars / stray whitespace."""
    if glen(text) > limit:
        err(f"{name}: {glen(text)} chars > {limit} (Google count): '{text}'")
    if hidden(text):
        err(f"{name}: hidden/illegal chars {hidden(text)} (remove non-breaking spaces / control chars)")
    if str(text) != str(text).strip():
        warn(f"{name}: leading/trailing whitespace -- trim it (Google counts it)")


def check_assets(ag, name, ctype="performance_max"):
    """Asset/creative limits. Demand Gen differs from PMax: headlines ≤40 (not 30), max 5 headlines (not 15),
    no PMax short-description-≤60 surface."""
    is_dg = ctype == "demand_gen"
    # (char limit, max count) per field
    fields = {
        "headlines": (40 if is_dg else 30, 5 if is_dg else 15),
        "long_headlines": (90, 5),
        "descriptions": (90, 5),
    }
    for field, (climit, nmax) in fields.items():
        items = ag.get(field) or []
        if len(items) > nmax:
            err(f"{name}: {len(items)} {field} (max {nmax} for {ctype})")
        for j, t in enumerate(items):
            over(t, climit, f"{name} {field}[{j+1}]")
    descs = ag.get("descriptions") or []
    if not is_dg and descs and glen(descs[0]) > 60:
        warn(f"{name}: description #1 is {glen(descs[0])} chars -- the short-description surface caps at 60")
    if len(ag.get("search_themes") or []) > MAXN["search_themes"]:
        err(f"{name}: >{MAXN['search_themes']} search themes")
    min_h = 3 if is_dg else 5
    if len(ag.get("headlines") or []) < min_h:
        warn(f"{name}: <{min_h} headlines -- weak ad strength")
    if ag.get("sitelinks"):
        warn(f"{name}: sitelinks found on an asset group -- in PMax sitelinks are CAMPAIGN-level "
             f"(move to spec.extensions.sitelinks)")


def check_extensions(spec):
    """PMax extensions attach at the CAMPAIGN level: sitelinks, callouts, structured snippets."""
    ext = spec.get("extensions") or {}
    sitelinks = ext.get("sitelinks") or []
    if not sitelinks:
        warn("no campaign-level sitelinks (extensions.sitelinks) -- free SERP real estate left on the table")
    for k, sl in enumerate(sitelinks):
        over(sl.get("text", ""), LIMITS["sitelink_text"], f"sitelink[{k+1}] text")
        for d in ("description1", "description2"):
            over(sl.get(d, ""), LIMITS["sitelink_desc"], f"sitelink[{k+1}] {d}")
        if not sl.get("final_url"):
            err(f"sitelink[{k+1}] '{sl.get('text')}': missing final_url")
    callouts = ext.get("callouts") or []
    if sitelinks and not callouts:
        warn("sitelinks present but no callouts -- audit flags missing callouts; add 4-10")
    for k, c in enumerate(callouts):
        over(c, LIMITS["callout"], f"callout[{k+1}]")
    for k, sn in enumerate(ext.get("structured_snippets") or []):
        hdr = sn.get("header", "")
        if hdr not in SNIPPET_HEADERS:
            warn(f"structured_snippet[{k+1}] header '{hdr}' not in Google's header list {sorted(SNIPPET_HEADERS)}")
        vals = sn.get("values") or []
        if len(vals) < 3:
            warn(f"structured_snippet[{k+1}] '{hdr}': {len(vals)} values (Google needs >=3)")
        for v in vals:
            over(v, LIMITS["snippet_value"], f"structured_snippet[{k+1}] value")
    for k, pa in enumerate(ext.get("prices") or []):
        ptype = pa.get("type", "")
        if ptype not in PRICE_TYPES:
            warn(f"price[{k+1}] type '{ptype}' not in Google's price-asset types {sorted(PRICE_TYPES)}")
        items = pa.get("items") or []
        if not (3 <= len(items) <= 8):
            err(f"price[{k+1}] '{ptype}': {len(items)} items (Google requires 3-8)")
        for j, it in enumerate(items):
            over(it.get("header", ""), LIMITS["price_header"], f"price[{k+1}] item[{j+1}] header")
            over(it.get("description", ""), LIMITS["price_desc"], f"price[{k+1}] item[{j+1}] description")
            if not str(it.get("price", "")).strip():
                err(f"price[{k+1}] item[{j+1}] '{it.get('header')}': missing price")
            if not it.get("final_url"):
                err(f"price[{k+1}] item[{j+1}] '{it.get('header')}': missing final_url")


def check_trademark(ag, name, avoid):
    """Block competitor trademarks in ad TEXT (headlines/descriptions/paths) — keywords are fine.
    Word-boundary, case-insensitive. This is the 'never a competitor TM in ad text' rule, enforced."""
    if not avoid:
        return
    rsa = ag.get("rsa") or {}
    texts = [h.get("text", "") for h in rsa.get("headlines") or []] \
        + [d.get("text", "") for d in rsa.get("descriptions") or []] \
        + list(rsa.get("paths") or [])
    for t in texts:
        low = str(t).lower()
        for term in avoid:
            tl = str(term).lower().strip()
            if tl and re.search(r"(?<![a-z0-9])" + re.escape(tl) + r"(?![a-z0-9])", low):
                err(f"{name}: ad text contains trademark-avoid term '{term}': '{t}' "
                    f"(competitor TM is OK as a keyword, NEVER in ad text)")


def check_ad_group(ag, name, avoid=None):
    check_trademark(ag, name, avoid)
    rsa = ag.get("rsa") or {}
    if not rsa.get("final_url"):
        err(f"{name}: rsa.final_url missing")
    heads = rsa.get("headlines") or []
    descs = rsa.get("descriptions") or []
    if len(heads) > 15:
        err(f"{name}: {len(heads)} RSA headlines (max 15)")
    if len(descs) > 4:
        err(f"{name}: {len(descs)} RSA descriptions (max 4)")
    if len(heads) < 3:
        warn(f"{name}: <3 RSA headlines -- weak ad strength")
    for i, h in enumerate(heads):
        over(h.get("text", ""), 30, f"{name} RSA headline[{i+1}]")
    for i, d in enumerate(descs):
        over(d.get("text", ""), 90, f"{name} RSA description[{i+1}]")
    for p in rsa.get("paths") or []:
        over(p, 15, f"{name} path")
    for kw in ag.get("keywords") or []:
        if kw.get("match_type") not in ("exact", "phrase", "broad"):
            err(f"{name}: keyword '{kw.get('text')}' bad match_type {kw.get('match_type')!r}")
    for n in ag.get("negatives") or []:
        if n.get("match_type") not in ("exact", "phrase"):
            err(f"{name}: negative '{n.get('text')}' must be exact/phrase (no broad)")


def walk_listing(node, name, includes):
    if not isinstance(node, dict):
        return
    if node.get("type") == "subdivision":
        children = node.get("children") or []
        has_other_exclude = any(
            c.get("type") == "unit" and c.get("action") == "exclude" and
            (c.get("dimension") == "other" or c.get("value") in (None, "", "other"))
            for c in children
        )
        if not has_other_exclude:
            err(f"{name}: listing subdivision '{node.get('value','')}' missing an Everything-Else=exclude node")
        for c in children:
            if c.get("type") == "unit" and c.get("action") == "include":
                includes.append((c.get("dimension"), c.get("value"), name))
            else:
                walk_listing(c, name, includes)
    elif node.get("type") == "unit" and node.get("action") == "include":
        includes.append((node.get("dimension"), node.get("value"), name))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--max-budget", type=float, default=None)
    args = ap.parse_args()

    try:
        with open(args.spec, encoding="utf-8") as f:
            spec = json.load(f)
    except FileNotFoundError:
        sys.exit(f"Not found: {args.spec}")
    except json.JSONDecodeError as e:
        sys.exit(f"Invalid JSON: {e}")

    ctype = spec.get("campaign_type")
    if ctype not in CAMPAIGN_TYPES:
        err(f"campaign_type must be one of {sorted(CAMPAIGN_TYPES)} (got {ctype!r})")
    if not spec.get("account", {}).get("customer_id"):
        err("account.customer_id missing")

    camp = spec.get("campaign", {})
    if camp.get("status") != "paused":
        err("campaign.status must be 'paused' on create (enable in UI after review)")
    if camp.get("conversion_goals", {}).get("scope") != "campaign":
        err("campaign.conversion_goals.scope must be 'campaign'")
    budget = camp.get("daily_budget")
    if budget is None:
        err("campaign.daily_budget missing")
    elif args.max_budget is not None and budget > args.max_budget:
        err(f"daily_budget {budget} exceeds spend cap {args.max_budget}")
    elif args.max_budget is None:
        warn("no --max-budget cap passed — spend-cap guard not enforced")
    if ctype == "performance_max" and not camp.get("brand_exclusion", {}).get("enabled"):
        warn("brand_exclusion.enabled is false for PMax — confirm this is an intentional override")

    for n in spec.get("campaign_negatives") or []:
        if n.get("match_type") not in ("exact", "phrase"):
            err(f"negative '{n.get('text')}': match_type must be exact or phrase (no broad)")

    includes = []
    ags = spec.get("asset_groups") or []
    if ctype in ("performance_max", "demand_gen"):
        if not ags:
            err("no asset_groups for a PMax/Demand Gen spec")
        for ag in ags:
            nm = ag.get("name", "AG?")
            if not ag.get("final_url"):
                err(f"{nm}: missing final_url")
            check_assets(ag, nm, ctype)
            if ag.get("listing_group"):
                walk_listing(ag["listing_group"], nm, includes)
        # Sitelinks/callouts/snippets are a PMax (campaign-level) thing; Demand Gen is creative/audience-led.
        if ctype == "performance_max":
            check_extensions(spec)
    elif ctype in ("search", "branded_search"):
        adgs = spec.get("ad_groups") or []
        if not adgs:
            warn("no ad_groups in a Search/Branded spec -- nothing to push")
        avoid = spec.get("trademark_avoid") or []
        for ag in adgs:
            check_ad_group(ag, ag.get("name", "AdGroup?"), avoid)
        if spec.get("extensions"):   # Search extensions are campaign-level too (optional)
            check_extensions(spec)

    # cross-AG product overlap
    seen = {}
    for dim, val, nm in includes:
        key = (dim, val)
        if key in seen and seen[key] != nm:
            err(f"listing overlap: {dim}={val} included in both '{seen[key]}' and '{nm}' (a product must be in one AG)")
        seen[key] = nm

    print(f"\n=== campaign-spec validation: {args.spec} ===\n")
    if errors:
        print("ERRORS (block push):")
        for e in errors: print(f"  X {e}")
    if warns:
        print("WARNINGS:")
        for w in warns: print(f"  ! {w}")
    if not errors and not warns:
        print("No issues.")
    print(f"\nResult: {'PASS -- safe to push (still PAUSED + approval gate)' if not errors else 'FAIL -- do not push'}")
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
