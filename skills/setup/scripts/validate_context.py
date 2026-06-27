#!/usr/bin/env python
"""
validate_context.py — schema + readiness validator for account-context.yaml

Usage:
    python validate_context.py [path]      # default: ./account-context.yaml

Checks structure/types/enums and reports readiness per lifecycle stage:
    setup-complete -> measurement-ready -> plan-ready -> build-ready

Exit code 0 if setup-complete, else 1. Business-agnostic; no brand specifics here.
"""
import sys

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency: PyYAML. Install with:  python -m pip install pyyaml")

VERTICALS = {"ecommerce", "leadgen", "local", "saas", "b2b-services"}
MODELS = {"b2c", "b2b", "b2b2c"}
DATA_TYPES = {"shopify", "woocommerce", "bigcommerce", "csv", "none"}

errors, warns = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warns.append(msg)


def get(d, path, default=None):
    cur = d
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    path = sys.argv[1] if len(sys.argv) > 1 else "./account-context.yaml"
    try:
        with open(path, "r", encoding="utf-8") as f:
            ctx = yaml.safe_load(f) or {}
    except FileNotFoundError:
        sys.exit(f"Not found: {path}  (run the setup skill first)")
    except yaml.YAMLError as e:
        sys.exit(f"YAML parse error in {path}: {e}")

    if not isinstance(ctx, dict):
        sys.exit("Top-level YAML is not a mapping. Start from templates/account-context.yaml.")

    # ---- schema / enums ----
    if get(ctx, "schema_version") != 1:
        warn("schema_version should be 1.")

    if not get(ctx, "business.name"):
        err("business.name is required.")
    v = get(ctx, "business.vertical")
    if not v:
        err("business.vertical is required.")
    elif v not in VERTICALS:
        warn(f"business.vertical '{v}' not in {sorted(VERTICALS)} (allowed but unusual).")
    m = get(ctx, "business.model")
    if m and m not in MODELS:
        warn(f"business.model '{m}' not in {sorted(MODELS)}.")

    dt = get(ctx, "data_source.type")
    if dt not in DATA_TYPES:
        err(f"data_source.type must be one of {sorted(DATA_TYPES)} (got {dt!r}).")
    if dt and dt != "none" and not get(ctx, "data_source.catalog_url"):
        warn("data_source.catalog_url is empty — needed to verify landing-page URLs are live.")

    if not get(ctx, "google_ads.customer_id"):
        err("google_ads.customer_id is required.")
    if not get(ctx, "google_ads.time_zone"):
        warn("google_ads.time_zone is empty.")
    if get(ctx, "google_ads.api_write") not in (True, False):
        warn("google_ads.api_write should be true/false (controls whether pusher may auto-create).")

    # ---- conversion actions ----
    actions = get(ctx, "google_ads.conversion_actions") or []
    primary = [a for a in actions if isinstance(a, dict) and a.get("primary")]
    if not actions:
        warn("No conversion_actions yet -- measurement skill must populate these before spend.")
    elif not primary:
        warn("No primary conversion action flagged — measurement-ready will fail.")

    # ---- readiness gates ----
    setup_complete = not errors
    measurement_ready = setup_complete and bool(primary)
    plan_ready = measurement_ready and bool(
        get(ctx, "business.aov") or dt not in (None, "none")
    ) and bool(get(ctx, "campaign_defaults.daily_budget"))
    build_ready = plan_ready and bool(get(ctx, "brand.brand_terms"))

    # ---- report ----
    print(f"\n=== account-context health: {path} ===\n")
    if errors:
        print("ERRORS (block setup-complete):")
        for e in errors:
            print(f"  X {e}")
    if warns:
        print("WARNINGS:")
        for w in warns:
            print(f"  ! {w}")
    if not errors and not warns:
        print("No issues found.")

    plan_need = []
    if not (get(ctx, "business.aov") or dt not in (None, "none")):
        plan_need.append("AOV or live data source")
    if not get(ctx, "campaign_defaults.daily_budget"):
        plan_need.append("campaign_defaults.daily_budget")

    gates = [
        ("setup-complete", setup_complete, "fix errors above"),
        ("measurement-ready", measurement_ready, "a primary purchase/lead conversion action"),
        ("plan-ready", plan_ready, " + ".join(plan_need) or "ready"),
        ("build-ready", build_ready, "brand.brand_terms (branded search + PMax exclusion)"),
    ]
    print("\nReadiness:")
    first_fail = True
    for label, ok, need in gates:
        if ok:
            print(f"  [x] {label}")
        elif first_fail:
            print(f"  [ ] {label}   -> needs: {need}")
            first_fail = False
        else:
            print(f"  [ ] {label}   (blocked by an earlier gate)")

    # ---- connections registry (prerequisite check) ----
    conns = get(ctx, "connections") or {}
    tiers = [("google_ads", "MANDATORY"), ("store", "full-value"), ("merchant", "full-value (ecom)"),
             ("ga4", "recommended"), ("gsc", "optional")]
    print("\nConnections (real data — missing sources render UNVERIFIED, never fabricated):")
    ga_ok = True
    for key, tier in tiers:
        c = conns.get(key) or {}
        st = (c.get("status") or "missing").lower()
        mark = "[x]" if st == "connected" else ("[~]" if st == "available" else "[ ]")
        via = f" via {c.get('via')}" if c.get("via") and st != "missing" else ""
        hint = "" if st == "connected" else f"   -> {tier}: {c.get('guide', 'connect this source')}"
        print(f"  {mark} {key:11} {st}{via}{hint}")
        if key == "google_ads" and st != "connected":
            ga_ok = False
    if not ga_ok:
        print("  !! Google Ads is MANDATORY and not connected — run setup to connect a Google Ads MCP first.")

    nxt = ("setup (connect Google Ads)" if not ga_ok else
           "setup" if not setup_complete else
           "measurement" if not measurement_ready else
           # plan-ready fails on a MISSING prerequisite (AOV/live data, budget) — point at the
           # fix (connect store / add the value via setup), not at `plan`, which would hit the gap.
           ("setup — provide " + " + ".join(plan_need)) if not plan_ready else
           # build-ready wants brand_terms; guide to add them rather than into a half-ready build.
           "setup — add brand.brand_terms" if not build_ready else
           "ready to build")
    print(f"\nNext step: {nxt}\n")

    sys.exit(0 if setup_complete else 1)


if __name__ == "__main__":
    main()
