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
    Uses Google Custom Search API to discover Amazon products.
    """
    import os
    import re
    from googleapiclient.discovery import build

    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_CX")

    if not api_key or not cx:
        print("⚠️  GOOGLE_SEARCH_API_KEY or GOOGLE_SEARCH_CX not set")
        print("   Falling back to placeholder mode")
        return _generate_placeholder_urls(plan, cohort="R")

    urls = []
    target_n = plan["representative"]["target_n"]
    strata = plan["representative"]["strata"]

    service = build("customsearch", "v1", developerKey=api_key)

    for stratum in strata:
        name = stratum["name"]
        query = stratum.get("query", f"site:amazon.com {name}")
        allocation = stratum["allocation"]
        n_samples = int(target_n * allocation)

        print(f"  Searching {name}: {query} (target={n_samples})")

        collected = 0
        start_index = 1

        while collected < n_samples and start_index <= 100:  # Google CSE max 100 results
            try:
                result = service.cse().list(
                    q=query,
                    cx=cx,
                    start=start_index,
                    num=min(10, n_samples - collected)
                ).execute()

                for item in result.get("items", []):
                    url = item["link"]
                    asin = _extract_asin_from_url(url)

                    if asin and asin not in [u["asin"] for u in urls]:
                        urls.append({
                            "asin": asin,
                            "url": f"https://www.amazon.com/dp/{asin}",
                            "cohort": "R",
                            "method": "search",
                            "category_hint": name,
                            "stratum": name
                        })
                        collected += 1

                        if collected >= n_samples:
                            break

                start_index += 10

            except Exception as e:
                print(f"    ⚠️  Search error: {e}")
                break

        print(f"    ✓ Collected {collected}/{n_samples}")

    return urls


def _extract_asin_from_url(url: str) -> str:
    """Extract ASIN from Amazon URL."""
    import re

    # Match /dp/ASIN or /gp/product/ASIN
    patterns = [
        r'/dp/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
        r'/ASIN/([A-Z0-9]{10})'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return ""


def _generate_placeholder_urls(plan: dict, cohort: str) -> List[Dict]:
    """Generate placeholder URLs when API is not available."""
    urls = []

    if cohort == "R":
        target_n = plan["representative"]["target_n"]
        strata = plan["representative"]["strata"]

        for stratum in strata:
            name = stratum["name"]
            allocation = stratum["allocation"]
            n_samples = int(target_n * allocation)

            for i in range(n_samples):
                asin = f"R{name[:3].upper()}{i:05d}"
                urls.append({
                    "asin": asin,
                    "url": f"https://www.amazon.com/dp/{asin}",
                    "cohort": "R",
                    "method": "placeholder",
                    "category_hint": name,
                    "stratum": name
                })

    return urls


def generate_targeted_urls(plan: dict) -> List[Dict]:
    """
    Generate T cohort URLs (high-risk keywords/nodes).
    Uses Google Custom Search API for keyword-based discovery.
    """
    import os
    from googleapiclient.discovery import build

    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_CX")

    if not api_key or not cx:
        print("⚠️  GOOGLE_SEARCH_API_KEY or GOOGLE_SEARCH_CX not set")
        print("   Falling back to placeholder mode")
        return _generate_placeholder_urls_targeted(plan)

    urls = []
    nodes = plan["targeted"]["nodes"]
    target_n = plan["targeted"]["target_n"]
    samples_per_node = max(1, target_n // len(nodes))

    service = build("customsearch", "v1", developerKey=api_key)

    for node in nodes:
        name = node["name"]
        keywords = node.get("keywords", [])
        gate = node.get("gate", "unknown")

        print(f"  Searching {name} (gate={gate})")

        collected = 0

        for keyword in keywords:
            if collected >= samples_per_node:
                break

            query = f"site:amazon.com {keyword}"

            try:
                result = service.cse().list(
                    q=query,
                    cx=cx,
                    num=min(10, samples_per_node - collected)
                ).execute()

                for item in result.get("items", []):
                    url = item["link"]
                    asin = _extract_asin_from_url(url)

                    if asin and asin not in [u["asin"] for u in urls]:
                        urls.append({
                            "asin": asin,
                            "url": f"https://www.amazon.com/dp/{asin}",
                            "cohort": "T",
                            "method": "keyword",
                            "category_hint": name,
                            "stratum": name,
                            "gate_target": gate,
                            "keyword": keyword
                        })
                        collected += 1

                        if collected >= samples_per_node:
                            break

            except Exception as e:
                print(f"    ⚠️  Search error for '{keyword}': {e}")
                continue

        print(f"    ✓ Collected {collected}/{samples_per_node}")

    return urls


def _generate_placeholder_urls_targeted(plan: dict) -> List[Dict]:
    """Generate placeholder URLs for T cohort when API is not available."""
    urls = []
    nodes = plan["targeted"]["nodes"]

    for node in nodes:
        name = node["name"]
        keywords = node.get("keywords", [])
        gate = node.get("gate", "unknown")

        for i, kw in enumerate(keywords[:5]):
            asin = f"T{name[:3].upper()}{i:05d}"
            urls.append({
                "asin": asin,
                "url": f"https://www.amazon.com/dp/{asin}",
                "cohort": "T",
                "method": "placeholder",
                "category_hint": name,
                "stratum": name,
                "gate_target": gate,
                "keyword": kw
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
