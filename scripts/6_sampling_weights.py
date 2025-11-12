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

    Uses allocation proportions from sampling plan as proxy for population.
    """
    weights = {}

    # Load products
    products = []
    with open(product_csv) as f:
        products = list(csv.DictReader(f))

    # Get R cohort products
    r_products = [p for p in products if p.get("sampling_cohort") == "R"]

    if not r_products:
        print("No R cohort products found")
        return weights

    # Build stratum -> allocation map from plan
    stratum_allocation = {}
    for stratum in plan["representative"]["strata"]:
        stratum_allocation[stratum["name"]] = stratum["allocation"]

    # Count observed samples per stratum
    stratum_counts = Counter(p.get("category_hint", p.get("stratum", "unknown")) for p in r_products)
    total_r = len(r_products)

    # Compute weights
    for p in r_products:
        stratum = p.get("category_hint", p.get("stratum", "unknown"))

        # Get target allocation (population proportion proxy)
        target_prop = stratum_allocation.get(stratum, 1.0 / len(stratum_allocation))

        # Get observed sample proportion
        sample_count = stratum_counts[stratum]
        sample_prop = sample_count / total_r if total_r > 0 else 0

        # Calculate weight
        if sample_prop > 0:
            weight = target_prop / sample_prop
        else:
            weight = 1.0

        weights[p["asin"]] = round(weight, 4)

    print(f"Computed weights for {len(r_products)} R cohort products")
    print(f"Strata distribution:")
    for stratum, count in stratum_counts.items():
        target = stratum_allocation.get(stratum, 0) * 100
        actual = (count / total_r) * 100
        avg_weight = sum(weights[p["asin"]] for p in r_products if p.get("category_hint", p.get("stratum")) == stratum) / count if count > 0 else 0
        print(f"  {stratum}: {count} samples ({actual:.1f}% vs target {target:.1f}%), avg_weight={avg_weight:.3f}")

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
