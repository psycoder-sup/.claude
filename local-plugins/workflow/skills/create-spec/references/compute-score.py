#!/usr/bin/env python3
"""Compute SPEC quality score from severity-tagged issue counts.

Usage:
    python3 compute-score.py [--json]

Reads issue counts from stdin as lines of: "<section_id> <severity>"
Section id is an integer 1-15, or "13.5" for Test Skeletons.
Severity is one of: blocker, major, minor, nit (case-insensitive).

Example input:
    2 blocker
    9 major
    13.5 major
    4 minor

Outputs the overall weighted score and the per-section breakdown.
Section weights follow skills/create-spec/references/scoring-rubric.md.
"""

import sys
import json
from collections import defaultdict

SECTION_WEIGHTS = {
    "1":    0.03,  # Overview
    "2":    0.15,  # Database Schema
    "3":    0.12,  # API Layer
    "4":    0.08,  # State Management
    "5":    0.08,  # Component Architecture
    "6":    0.04,  # Navigation
    "7":    0.05,  # Type Definitions
    "8":    0.03,  # Analytics Implementation
    "9":    0.10,  # Permissions & Security
    "10":   0.07,  # Performance Considerations
    "11":   0.08,  # Migration & Deployment
    "12":   0.07,  # Implementation Phases
    "13":   0.01,  # Test Strategy (reduced from 5% to make room for 13.5)
    "13.5": 0.04,  # Test Skeletons (new section)
    "14":   0.03,  # Technical Risks & Mitigations
    "15":   0.02,  # Open Technical Questions
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
        return "Exceptional — ready to implement"
    if score >= 0.8:
        return "Strong — ready to implement with minor refinements"
    if score >= 0.7:
        return "Decent — address Major issues before implementing"
    if score >= 0.6:
        return "Weak — fix Blockers, significant revision needed"
    return "Poor — needs architectural rethink"


def normalize_section(raw):
    raw = raw.strip()
    if raw in SECTION_WEIGHTS:
        return raw
    try:
        as_int = int(raw)
        key = str(as_int)
        if key in SECTION_WEIGHTS:
            return key
    except ValueError:
        pass
    return None


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
        section = normalize_section(parts[0])
        sev = parts[1].lower()
        if section is None:
            print(f"Skipping unknown section: {line!r}", file=sys.stderr)
            continue
        if sev not in SEVERITY_PENALTY:
            print(f"Skipping unknown severity: {line!r}", file=sys.stderr)
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
    print(f"{'Sec':<6}{'Weight':<8}{'Score':<8}{'Contrib':<9}Counts")
    section_order = list(SECTION_WEIGHTS.keys())
    for section in section_order:
        s = result["per_section"][section]
        counts_str = ", ".join(f"{k}={v}" for k, v in s["counts"].items()) or "—"
        print(
            f"{section:<6}{s['weight']:<8.2f}{s['score']:<8.3f}"
            f"{s['contribution']:<9.4f}{counts_str}"
        )


if __name__ == "__main__":
    main()
