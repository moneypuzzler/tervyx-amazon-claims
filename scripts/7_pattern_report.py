#!/usr/bin/env python3
"""
TERVYX Amazon Claims — Pattern Report
Generate top patterns for L/Φ/K gate validation.
"""

import argparse
import csv
import json
from pathlib import Path
from collections import Counter


def main():
    parser = argparse.ArgumentParser(description="Generate pattern report")
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    # Collect patterns
    phi_counter = Counter()
    k_counter = Counter()
    l_counter = Counter()

    with open(args.claims) as f:
        reader = csv.DictReader(f)
        for row in reader:
            phi_ids = json.loads(row.get("phi_hint_ids", "[]"))
            k_ids = json.loads(row.get("k_hint_ids", "[]"))
            l_tokens = json.loads(row.get("l_tokens", "[]"))

            phi_counter.update(phi_ids)
            k_counter.update(k_ids)
            l_counter.update(l_tokens)

    # Write report
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["gate", "pattern", "count"])

        for pattern, count in phi_counter.most_common():
            writer.writerow(["Φ", pattern, count])
        for pattern, count in k_counter.most_common():
            writer.writerow(["K", pattern, count])
        for pattern, count in l_counter.most_common():
            writer.writerow(["L", pattern, count])

    print(f"✓ Pattern report → {args.out}")
    print(f"  Φ patterns: {len(phi_counter)}")
    print(f"  K patterns: {len(k_counter)}")
    print(f"  L patterns: {len(l_counter)}")


if __name__ == "__main__":
    main()
