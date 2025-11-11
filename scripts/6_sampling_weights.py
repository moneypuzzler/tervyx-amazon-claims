#!/usr/bin/env python3
"""
TERVYX Amazon Claims — Sampling Weights Calculation
Compute and assign sampling weights to R cohort for population estimation.
"""

import argparse
import csv
import yaml
from pathlib import Path
from collections import Counter


def load_sampling_plan(plan_path: Path) -> dict:
    """Load sampling plan."""
    with open(plan_path) as f:
        return yaml.safe_load(f)


def compute_weights(product_csv: Path, plan: dict) -> dict:
    """
    Compute sampling weights for R cohort.

    Weight = (population_proportion / sample_proportion)

    TODO: Implement proper weight calculation
    - Use external population estimates (e.g., Amazon category sizes)
    - Or post-stratification based on observed distributions
    - Handle edge cases (zero samples in stratum)
    """
    weights = {}

    # Load products
    products = []
    with open(product_csv) as f:
        products = list(csv.DictReader(f))

    # Count R cohort by stratum
    r_products = [p for p in products if p["sampling_cohort"] == "R"]
    stratum_counts = Counter(p.get("category_path", "unknown") for p in r_products)

    # FIXME: Use actual population proportions
    # For now, assume equal weighting (weight=1.0)
    for p in r_products:
        weights[p["asin"]] = 1.0

    print(f"Computed weights for {len(r_products)} R cohort products")
    print(f"Strata: {dict(stratum_counts)}")

    return weights


def main():
    parser = argparse.ArgumentParser(description="Compute sampling weights")
    parser.add_argument("--product", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()

    plan = load_sampling_plan(args.plan)
    weights = compute_weights(args.product, plan)

    # Update product CSV in-place
    rows = []
    with open(args.product) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["asin"] in weights:
                row["sampling_weight"] = str(weights[row["asin"]])
            rows.append(row)

    with open(args.product, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ Updated {args.product} with sampling weights")


if __name__ == "__main__":
    main()
