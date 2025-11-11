#!/usr/bin/env python3
"""
TERVYX Amazon Claims — URL Generation (R/T Cohorts)
Generate product URL list based on sampling plan.
"""

import argparse
import csv
import hashlib
import yaml
from pathlib import Path
from typing import List, Dict
from datetime import datetime


def load_sampling_plan(plan_path: Path) -> dict:
    """Load sampling plan YAML."""
    with open(plan_path) as f:
        return yaml.safe_load(f)


def generate_representative_urls(plan: dict) -> List[Dict]:
    """
    Generate R cohort URLs (stratified random sampling).

    TODO: Implement actual sampling logic:
    - Use Amazon Product Advertising API (if available)
    - Or search-based discovery (e.g., Google Custom Search API)
    - Apply stratified random sampling per allocation
    - Ensure diversity across categories
    """
    urls = []
    target_n = plan["representative"]["target_n"]
    strata = plan["representative"]["strata"]

    for stratum in strata:
        name = stratum["name"]
        allocation = stratum["allocation"]
        n_samples = int(target_n * allocation)

        # FIXME: Replace with actual sampling
        for i in range(n_samples):
            asin = f"R{name[:3].upper()}{i:05d}"  # Placeholder ASIN
            urls.append({
                "asin": asin,
                "url": f"https://www.amazon.com/dp/{asin}",
                "cohort": "R",
                "method": "random",
                "category_hint": name,
                "stratum": name
            })

    return urls


def generate_targeted_urls(plan: dict) -> List[Dict]:
    """
    Generate T cohort URLs (high-risk keywords/nodes).

    TODO: Implement targeted discovery:
    - Browse node IDs (if available)
    - Keyword-based search
    - Manual seed list for known problematic products
    """
    urls = []
    nodes = plan["targeted"]["nodes"]

    for node in nodes:
        name = node["name"]
        keywords = node.get("keywords", [])
        gate = node.get("gate", "unknown")

        # FIXME: Replace with actual search
        for i, kw in enumerate(keywords[:5]):  # Max 5 per node for demo
            asin = f"T{name[:3].upper()}{i:05d}"
            urls.append({
                "asin": asin,
                "url": f"https://www.amazon.com/dp/{asin}",
                "cohort": "T",
                "method": "keyword",
                "category_hint": name,
                "stratum": name,
                "gate_target": gate
            })

    return urls


def main():
    parser = argparse.ArgumentParser(description="Generate product URL list")
    parser.add_argument("--plan", type=Path, required=True, help="Sampling plan YAML")
    parser.add_argument("--out", type=Path, required=True, help="Output CSV path")
    parser.add_argument("--sample", type=int, help="Limit to N samples (testing)")
    args = parser.parse_args()

    plan = load_sampling_plan(args.plan)

    print(f"Generating URLs from plan: {args.plan}")
    r_urls = generate_representative_urls(plan)
    t_urls = generate_targeted_urls(plan)

    all_urls = r_urls + t_urls

    if args.sample:
        all_urls = all_urls[:args.sample]
        print(f"Limited to {args.sample} samples")

    print(f"Generated {len(all_urls)} URLs (R={len(r_urls)}, T={len(t_urls)})")

    # Write CSV
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as f:
        fieldnames = ["asin", "url", "cohort", "method", "category_hint", "stratum"]
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_urls)

    print(f"Saved to {args.out}")


if __name__ == "__main__":
    main()
