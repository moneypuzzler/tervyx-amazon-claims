#!/usr/bin/env python3
"""
Quick Google Custom Search using requests (no google-api-python-client needed)
"""
import os
import sys
import json
import requests
import csv
from pathlib import Path

def search_amazon_products(query, api_key, cx, num_results=10):
    """Search Amazon using Google Custom Search API"""
    base_url = "https://www.googleapis.com/customsearch/v1"

    asins = []
    start_index = 1

    while len(asins) < num_results and start_index <= 100:
        params = {
            "key": api_key,
            "cx": cx,
            "q": query,
            "start": start_index,
            "num": min(10, num_results - len(asins))
        }

        try:
            response = requests.get(base_url, params=params, timeout=30)

            if response.status_code != 200:
                print(f"    ⚠️  API error: {response.status_code}")
                print(f"    Response: {response.text[:200]}")
                break

            data = response.json()

            if "items" not in data:
                break

            for item in data["items"]:
                url = item["link"]
                asin = extract_asin(url)
                if asin and asin not in asins:
                    asins.append(asin)

            start_index += 10

        except Exception as e:
            print(f"    ⚠️  Search error: {e}")
            break

    return asins


def extract_asin(url):
    """Extract ASIN from Amazon URL"""
    import re
    patterns = [
        r'/dp/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
        r'/ASIN/([A-Z0-9]{10})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def main():
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_CX")

    if not api_key or not cx:
        print("❌ API keys not set")
        sys.exit(1)

    sample_size = int(sys.argv[1]) if len(sys.argv) > 1 else 50

    print(f"🔍 Collecting {sample_size} Amazon products...")

    # R cohort queries
    queries = [
        ("HealthAndHousehold", "site:amazon.com Health & Household supplement", 0.35),
        ("Beauty", "site:amazon.com Beauty hair growth anti-aging", 0.20),
        ("Devices", "site:amazon.com Electric Massagers TENS Pain Relief", 0.15),
        ("Sleep", "site:amazon.com Sleep Aid Melatonin Relaxation", 0.10),
        ("WeightLoss", "site:amazon.com Weight Loss Supplements Fat Burner", 0.10),
        ("HairGrowth", "site:amazon.com Hair Regrowth Hair Growth Products", 0.10),
    ]

    products = []

    for name, query, allocation in queries:
        n_needed = int(sample_size * allocation)
        print(f"\n[{name}] Searching for {n_needed} products...")
        print(f"  Query: {query}")

        asins = search_amazon_products(query, api_key, cx, n_needed)

        for asin in asins:
            products.append({
                "asin": asin,
                "url": f"https://www.amazon.com/dp/{asin}",
                "cohort": "R",
                "method": "search",
                "category_hint": name,
                "stratum": name
            })

        print(f"  ✓ Found {len(asins)} products")

    # Save
    output_path = Path("data/raw/product_urls.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["asin", "url", "cohort", "method", "category_hint", "stratum"])
        writer.writeheader()
        writer.writerows(products)

    print(f"\n✅ Collected {len(products)} products")
    print(f"✅ Saved to {output_path}")


if __name__ == "__main__":
    main()
