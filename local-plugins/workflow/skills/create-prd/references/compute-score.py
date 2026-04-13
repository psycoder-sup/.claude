#!/usr/bin/env python3
"""Compute PRD quality score from severity-tagged issue counts.

Usage:
    python3 compute-score.py [--json]

Reads issue counts from stdin as lines of: "<section_number> <severity>"
Severity is one of: blocker, major, minor, nit (case-insensitive).

Example input:
    5 blocker
    5 major
    2 minor
    11 nit

Outputs the overall weighted score and the per-section breakdown.
Section weights follow skills/create-prd/references/scoring-rubric.md.
"""

import sys
import json
from collections import defaultdict

SECTION_WEIGHTS = {
    1: 0.05,   # Overview
    2: 0.12,   # Problem Statement
    3: 0.12,   # Goals & Non-Goals
    4: 0.12,   # User Stories
    5: 0.22,   # Functional Requirements
    6: 0.17,   # UX & Design
    7: 0.05,   # Permissions & Privacy
    8: 0.05,   # Analytics & Instrumentation
    9: 0.05,   # Release Strategy
    10: 0.03,  # Open Questions
    11: 0.02,  # Appendix
}

SEVERITY_PENALTY = {
    "blocker": 0.30,
    "major":   0.10,
    "minor":   0.03,
    "nit":     0.005,
}


def compute(counts_by_section):
    per_section = {}
    for section, weight in SECTION_WEIGHTS.items():
        sev_counts = counts_by_section.get(section, {})
        penalty = sum(
            SEVERITY_PENALTY[sev] * n for sev, n in sev_counts.items()
        )
        section_score = max(0.0, 1.0 - penalty)
        per_section[section] = {
            "weight": weight,
            "counts": dict(sev_counts),
            "score": round(section_score, 4),
            "contribution": round(section_score * weight, 4),
        }
    overall = sum(s["contribution"] for s in per_section.values())
    return {
        "overall_score": round(overall, 3),
        "per_section": per_section,
    }


def verdict(score):
    if score >= 0.9:
        return "Exceptional — ready to build"
    if score >= 0.8:
        return "Strong — ready to build with minor refinements"
    if score >= 0.7:
        return "Decent — address Major issues before building"
    if score >= 0.6:
        return "Weak — fix Blockers, significant revision needed"
    return "Poor — needs fundamental rethink"


def main():
    as_json = "--json" in sys.argv
    counts = defaultdict(lambda: defaultdict(int))
    for line in sys.stdin:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            print(f"Skipping malformed line: {line!r}", file=sys.stderr)
            continue
        try:
            section = int(parts[0])
        except ValueError:
            print(f"Skipping non-integer section: {line!r}", file=sys.stderr)
            continue
        sev = parts[1].lower()
        if sev not in SEVERITY_PENALTY:
            print(f"Skipping unknown severity: {line!r}", file=sys.stderr)
            continue
        if section not in SECTION_WEIGHTS:
            print(f"Skipping unknown section: {line!r}", file=sys.stderr)
            continue
        counts[section][sev] += 1

    result = compute(counts)
    result["verdict"] = verdict(result["overall_score"])

    if as_json:
        print(json.dumps(result, indent=2))
        return

    print(f"Overall score: {result['overall_score']:.3f}")
    print(f"Verdict: {result['verdict']}")
    print()
    print("Per-section breakdown:")
    print(f"{'Sec':<4}{'Weight':<8}{'Score':<8}{'Contrib':<9}Counts")
    for section in sorted(result["per_section"]):
        s = result["per_section"][section]
        counts_str = ", ".join(f"{k}={v}" for k, v in s["counts"].items()) or "—"
        print(
            f"{section:<4}{s['weight']:<8.2f}{s['score']:<8.3f}"
            f"{s['contribution']:<9.4f}{counts_str}"
        )


if __name__ == "__main__":
    main()
