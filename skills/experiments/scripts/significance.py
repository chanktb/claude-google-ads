#!/usr/bin/env python
"""
significance.py — is an A/B test powered enough to conclude?

Usage:
    python significance.py --conv-per-arm 200 --mde 0.15
    python significance.py --conv-per-arm 200            # report smallest detectable lift

Approximation for conversion-COUNT experiments (two arms). Detectable relative lift d at ~95% confidence /
~80% power needs roughly conv_per_arm >= 2 * z^2 / d^2  (z ~= 2.8). Use to avoid running a test too small to
conclude. Honest approximation, not a substitute for the platform's own experiment significance.
"""
import argparse
import math
import sys

Z = 2.8  # ~combined 95% confidence + 80% power for a two-arm count test


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--conv-per-arm", type=float, required=True,
                    help="expected conversions PER ARM over the whole run")
    ap.add_argument("--mde", type=float, default=None, help="relative lift you want to detect, e.g. 0.15")
    a = ap.parse_args()

    c = a.conv_per_arm
    detectable = Z * math.sqrt(2.0 / c) if c > 0 else float("inf")
    print(f"\n=== Experiment power (approx) ===")
    print(f"Conversions per arm: {c:.0f}")
    print(f"Smallest reliably detectable relative lift: ~{detectable*100:.0f}%")

    if a.mde:
        required = 2 * Z * Z / (a.mde ** 2)
        powered = c >= required
        print(f"\nTarget lift to detect: {a.mde*100:.0f}%")
        print(f"Conversions per arm needed: ~{required:.0f}")
        print(f"Verdict: {'POWERED — safe to run' if powered else 'UNDERPOWERED — extend runtime / raise budget / pick a higher-volume variable, or skip'}")
    else:
        print("\nPass --mde <relative lift> to check whether your run is powered for a specific effect.")
    print("\nApproximation for count-based A/B; confirm with the platform's own experiment readout.\n")


if __name__ == "__main__":
    main()
