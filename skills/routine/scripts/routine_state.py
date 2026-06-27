#!/usr/bin/env python
"""
routine_state.py — remembers when each routine cadence last ran, and flags what's DUE / OVERDUE

Usage:
    python routine_state.py [--state routine-state.json] [--today YYYY-MM-DD]   # show agenda
    python routine_state.py --mark weekly [--actions "raised <campaign> +10%; added 4 negatives"]   # stamp a run

State file (auto-created in the working dir): routine-state.json
{
  "last_run": {"daily":"2026-06-20","weekly":"2026-06-10","monthly":"2026-05-01","quarterly":null},
  "log": [{"date":"2026-06-10","cadence":"weekly","actions":["..."]}]
}

Cadence intervals: daily 1d · weekly 7d · monthly 30d · quarterly 90d. The skill reads the agenda and runs
whatever is due/overdue — so if the user hasn't checked in a while, the overdue items surface automatically.
Business-agnostic.
"""
import argparse
import json
import os
import sys
from datetime import date, datetime

INTERVALS = {"daily": 1, "weekly": 7, "monthly": 30, "quarterly": 90}


def load(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"last_run": {k: None for k in INTERVALS}, "log": []}


def parse_d(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="routine-state.json")
    ap.add_argument("--today", default=None)
    ap.add_argument("--mark", choices=list(INTERVALS), default=None)
    ap.add_argument("--actions", default="")
    a = ap.parse_args()

    today = parse_d(a.today) if a.today else date.today()
    st = load(a.state)
    st.setdefault("last_run", {k: None for k in INTERVALS})
    st.setdefault("log", [])

    if a.mark:
        st["last_run"][a.mark] = today.isoformat()
        st["log"].append({"date": today.isoformat(), "cadence": a.mark,
                          "actions": [s.strip() for s in a.actions.split(";") if s.strip()]})
        with open(a.state, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=2)
        print(f"Marked {a.mark} run on {today.isoformat()} in {a.state}.")
        return

    print(f"\n=== Routine agenda (as of {today.isoformat()}) ===\n")
    rows = []
    for cad, interval in INTERVALS.items():
        last = parse_d(st["last_run"].get(cad))
        if last is None:
            rows.append((cad, "never", "DUE (never run)"))
            continue
        days = (today - last).days
        if days >= interval * 2:
            status = f"OVERDUE by {days - interval}d"
        elif days >= interval:
            status = "DUE"
        else:
            status = f"ok (in {interval - days}d)"
        rows.append((cad, f"{days}d ago ({last.isoformat()})", status))

    for cad, last, status in rows:
        flag = "->" if ("DUE" in status or "OVERDUE" in status) else "  "
        print(f"  {flag} {cad:<10} last: {last:<26} {status}")

    due = [c for c, _, s in rows if "DUE" in s or "OVERDUE" in s]
    print("\nRun now: " + (", ".join(due) if due else "nothing due — all current"))
    if a.state and not os.path.exists(a.state):
        print(f"(no state file yet — first run; it will be created when you --mark a cadence)")
    print()


if __name__ == "__main__":
    main()
