#!/usr/bin/env python
"""
validate_changeset.py — dry-run validator + safety gate for a change-set.json

Usage:
    python validate_changeset.py <change-set.json> [--context account-context.yaml]
                                 [--max-budget N] [--budget-step 0.10] [--troas-step 0.3]

Enforces the discipline in references/change-set.md (Scaling Ladder + tROAS step-up +
account guardrails). The pusher runs this BEFORE rendering or any API mutation.
Exit 0 only if there are no ERRORS. Business-agnostic — brand terms / cooldown come from
the change-set targets and the optional account-context.yaml, never hardcoded.
"""
import argparse
import json
import re
import sys

try:
    import yaml
except ImportError:
    yaml = None

SCALE_TYPES = {"adjust_budget", "adjust_target_roas"}
ACTION_TYPES = {
    "add_negatives", "exclude_geo", "exclude_products", "adjust_budget",
    "adjust_target_roas", "pause", "add_extensions", "add_audience_signal",
    "exclude_placements", "add_assets", "replace_asset",
}

errors, warns, notes = [], [], []
def err(m): errors.append(m)
def warn(m): warns.append(m)
def note(m): notes.append(m)


def brand_tokens(context_path):
    """Pull brand_terms from account-context.yaml (for the never-block-brand check).
    Each brand_term ENTRY is kept whole — a multi-word phrase like 'nd nail supply' is matched
    as the contiguous phrase, NOT split into generic tokens ('nail','supply') that would over-block
    legitimate category negatives."""
    if not context_path or not yaml:
        return []
    try:
        with open(context_path, encoding="utf-8") as f:
            ctx = yaml.safe_load(f) or {}
        terms = (ctx.get("brand") or {}).get("brand_terms") or []
        phrases = []
        for t in terms:
            p = re.sub(r"\s+", " ", str(t).lower().strip())
            if len(p) >= 2:
                phrases.append(p)
        return sorted(set(phrases))
    except FileNotFoundError:
        warn(f"context not found: {context_path} — brand-term protection skipped")
        return []


def carried_lists(context_path):
    """Carried (resold) brands + which already have a dedicated campaign, for the reseller guard.
    Returns (carried_phrases, own_campaign_set). A negative that blocks a brand you SELL is a false-positive:
    if the brand has no dedicated campaign the catch-all is its only home (never block); if it does, blocking
    is allowed only to ROUTE to the specialist campaign."""
    if not context_path or not yaml:
        return [], set()
    try:
        with open(context_path, encoding="utf-8") as f:
            ctx = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return [], set()
    br = ctx.get("brand") or {}
    raw = br.get("carried_brands") or br.get("brands_carried") or ctx.get("carried_brands") or []
    own = br.get("brands_with_own_campaign") or ctx.get("brands_with_own_campaign") or []
    norm = lambda xs: sorted({re.sub(r"\s+", " ", str(x).lower().strip()) for x in xs if len(str(x).strip()) >= 2})
    return norm(raw), set(norm(own))


def load_converters(path):
    """JSON list of converting query strings (or [{term/text/query,...}]). Lowercased."""
    if not path:
        return []
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        warn(f"converting-terms file not found: {path} — conflict check skipped")
        return []
    out = []
    for x in raw if isinstance(raw, list) else []:
        s = x if isinstance(x, str) else (x.get("term") or x.get("text") or x.get("query") or "")
        if s:
            out.append(str(s).lower().strip())
    return sorted(set(out))


def neg_blocks(neg_text, exact, query):
    q, n = str(query).lower().strip(), str(neg_text).lower().strip()
    if exact:
        return q == n
    pat = r"(?<![a-z0-9])" + r"\s+".join(re.escape(w) for w in n.split()) + r"(?![a-z0-9])"
    return re.search(pat, q) is not None


def check_conflict(a, name, converters):
    """A negative must NEVER block a CONVERTING query — that's cutting proven revenue."""
    if not converters:
        return
    for nrec in a.get("negatives") or []:
        text = nrec.get("text", "")
        exact = (nrec.get("match_type") == "exact")
        for cq in converters:
            if neg_blocks(text, exact, cq):
                err(f"{name}: negative '{text}' would BLOCK a converting query \"{cq}\" — never negate a term "
                    f"that converts (it cuts proven revenue). Tighten the negative or drop it.")
                break


def check_carried(a, name, carried, own_camp):
    if not carried:
        return
    for n in a.get("negatives") or []:
        for h in hits_brand(n.get("text", ""), carried):
            if h in own_camp:
                warn(f"{name}: negative '{n.get('text')}' blocks CARRIED brand '{h}' — allowed ONLY to route to "
                     f"the dedicated {h} campaign; confirm it targets the catch-all, not the {h} campaign itself.")
            else:
                err(f"{name}: negative '{n.get('text')}' blocks CARRIED brand '{h}' which has NO dedicated "
                    f"campaign — NEVER block a brand you sell (the catch-all is its only home). Split it into its "
                    f"own campaign when it scales, or fix stock/PDP/feed; do not negate it.")


def hits_brand(text, phrases):
    """Word-boundary phrase match (NOT substring) — own 'nd' must not match resold 'dnd';
    'nd nail supply' matches the whole phrase, not the generic word 'nail' on its own."""
    low = str(text or "").lower()
    hits = []
    for p in phrases:
        pat = r"(?<![a-z0-9])" + r"\s+".join(re.escape(w) for w in p.split(" ")) + r"(?![a-z0-9])"
        if re.search(pat, low):
            hits.append(p)
    return hits


def check_negatives(a, name):
    for n in a.get("negatives") or []:
        mt = n.get("match_type")
        if mt not in ("exact", "phrase"):
            err(f"{name}: negative '{n.get('text')}' match_type must be exact/phrase (no broad)")


def check_brand(a, name, toks):
    if not toks:
        return
    for n in a.get("negatives") or []:
        h = hits_brand(n.get("text", ""), toks)
        if h:
            err(f"{name}: negative '{n.get('text')}' contains brand term {h} — NEVER block brand "
                f"(brand intent is not waste, even at 0 conv)")


def check_budget(a, name, tgt, cap, step):
    cur, new = a.get("current_daily"), a.get("new_daily")
    if cur is None or new is None:
        err(f"{name}: adjust_budget needs current_daily and new_daily")
        return
    if tgt.get("campaign_type") == "performance_max" and a.get("direction") == "down":
        err(f"{name}: PMax scales DOWN by pausing low-ROAS asset groups, NOT a budget cut "
            f"(cutting starves asset-group exploration) — use a pause action instead")
    if new > cur and new > round(cur * (1 + step) + 1e-9, 2):
        err(f"{name}: budget step {cur}->{new} exceeds +{int(step*100)}% (max {round(cur*(1+step),2)}) "
            f"— scale gently so Smart Bidding doesn't re-forecast")
    if cap is not None and new > cap:
        err(f"{name}: new_daily {new} exceeds spend cap {cap}")


def check_troas(a, name):
    cur, new = a.get("current"), a.get("new")
    if cur is None or new is None:
        err(f"{name}: adjust_target_roas needs current and new")
        return
    if new - cur > 0.3 + 1e-9:
        err(f"{name}: tROAS step {cur}->{new} (+{round(new-cur,2)}x) exceeds +0.3x — raise in small steps")
    if new > cur:
        cpw = a.get("conv_per_week")
        if cpw is None:
            warn(f"{name}: tROAS raise with no conv_per_week — confirm >=15 conv/wk before raising")
        elif cpw < 15:
            err(f"{name}: tROAS raise at {cpw} conv/wk (<15) — consolidate for volume BEFORE raising "
                f"(too-fast a raise shrinks the audience → the algorithm goes blind)")


def check_scale_gates(a, name, tgt):
    """Cooldown + whipsaw gates apply to every budget/target move."""
    within = bool(tgt.get("within_cooldown"))
    if within:
        err(f"{name}: target '{tgt.get('campaign')}' is WITHIN COOLDOWN (recent change_event) — "
            f"do not scale/move budget or target yet; let Smart Bidding stabilize")
    last = tgt.get("last_change_direction")
    direction = a.get("direction") or ("up" if (a.get("new") or 0) > (a.get("current") or 0) else None)
    if within and last and direction and last != direction:
        err(f"{name}: direction reversal ({last}->{direction}) inside cooldown — whipsaws the algorithm")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("changeset")
    ap.add_argument("--context", default=None, help="account-context.yaml for brand-term protection")
    ap.add_argument("--max-budget", type=float, default=None, help="daily spend cap")
    ap.add_argument("--budget-step", type=float, default=0.10, help="max budget step fraction (default 0.10)")
    ap.add_argument("--converting-terms", default=None,
                    help="JSON list of CONVERTING query strings (conv>0). If given, a negative that would block "
                         "any of them is a conflict ERROR. Optimizer can pass terms.json's converters here.")
    args = ap.parse_args()

    try:
        with open(args.changeset, encoding="utf-8") as f:
            cs = json.load(f)
    except FileNotFoundError:
        sys.exit(f"Not found: {args.changeset}")
    except json.JSONDecodeError as e:
        sys.exit(f"Invalid JSON: {e}")

    if cs.get("kind") != "change-set":
        err("kind must be 'change-set' (a campaign-spec goes through validate_spec.py instead)")
    if not (cs.get("account") or {}).get("customer_id"):
        err("account.customer_id missing")

    toks = brand_tokens(args.context)
    carried, own_camp = carried_lists(args.context)
    converters = load_converters(args.converting_terms)
    if args.max_budget is None:
        warn("no --max-budget cap passed — spend-cap guard not enforced")

    actions = cs.get("actions") or []
    if not actions:
        err("no actions in the change-set")

    seen_ids = set()
    for i, a in enumerate(actions):
        aid = a.get("id") or f"#{i+1}"
        name = f"action[{aid}]"
        if a.get("id"):
            if a["id"] in seen_ids:
                err(f"{name}: duplicate action id")
            seen_ids.add(a["id"])
        t = a.get("type")
        if t not in ACTION_TYPES:
            err(f"{name}: unknown type {t!r}")
            continue
        if not str(a.get("reason") or "").strip():
            err(f"{name}: missing reason (every action needs data backing)")
        tgt = a.get("target") or {}
        if not tgt.get("campaign") and t not in ("exclude_placements",):
            warn(f"{name}: target.campaign missing — operator can't locate the entity")

        if t == "add_negatives":
            check_negatives(a, name)
            check_brand(a, name, toks)
            check_carried(a, name, carried, own_camp)
            check_conflict(a, name, converters)
        elif t == "adjust_budget":
            check_budget(a, name, tgt, args.max_budget, args.budget_step)
            check_scale_gates(a, name, tgt)
        elif t == "adjust_target_roas":
            check_troas(a, name)
            check_scale_gates(a, name, tgt)
        elif t == "pause":
            ent = a.get("entity")
            if ent not in ("campaign", "asset_group", "ad_group"):
                err(f"{name}: pause needs entity = campaign|asset_group|ad_group")
            r = str(a.get("reason") or "").lower()
            if not re.search(r"\d", r):
                warn(f"{name}: pause with no number in the reason — don't pause blind (cite ROAS/spend/conv)")
        # is_scale sanity: a scale-tagged action that isn't a move, or vice-versa
        if a.get("is_scale") and t not in SCALE_TYPES:
            warn(f"{name}: is_scale=true but type {t} isn't a budget/target move")

    print(f"\n=== change-set validation: {args.changeset} ===\n")
    if notes:
        print("NOTES:")
        for n in notes: print(f"  - {n}")
    if errors:
        print("ERRORS (block push):")
        for e in errors: print(f"  X {e}")
    if warns:
        print("WARNINGS:")
        for w in warns: print(f"  ! {w}")
    if not errors and not warns:
        print("No issues.")
    n_blocked = sum(1 for e in errors if "WITHIN COOLDOWN" in e)
    print(f"\n{len(actions)} actions · {len(errors)} errors · {len(warns)} warnings"
          + (f" · {n_blocked} blocked by cooldown" if n_blocked else ""))
    print(f"Result: {'PASS — safe to render (still approval gate + PAUSED-on-create)' if not errors else 'FAIL — fix errors before push'}")
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
