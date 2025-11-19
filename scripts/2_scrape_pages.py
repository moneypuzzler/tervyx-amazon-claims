#!/usr/bin/env python3
"""
TERVYX Amazon Claims — Page Scraping (Ethics-First)
Fetch public product pages with robots.txt compliance and Wayback archival.
"""

import argparse
import csv
import hashlib
import time
import yaml
import requests
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup


def load_scraping_policy(policy_path: Path) -> dict:
    """Load scraping policy YAML."""
    with open(policy_path) as f:
        return yaml.safe_load(f)


def check_robots_txt(domain: str, user_agent: str) -> bool:
    """
    Check robots.txt compliance using urllib.robotparser.
    """
    from urllib.robotparser import RobotFileParser
    from urllib.parse import urlparse

    robots_url = f"https://{domain}/robots.txt"

    try:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()

        can_fetch = rp.can_fetch(user_agent, f"https://{domain}/dp/")

        if can_fetch:
            print(f"  [robots.txt] ✓ Allowed")
        else:
            print(f"  [robots.txt] ✗ Disallowed")

        return can_fetch

    except Exception as e:
        print(f"  [robots.txt] ⚠️  Error reading robots.txt: {e}")
        return False


def save_to_wayback(url: str, policy: dict) -> Optional[str]:
    """
    Save URL to Wayback Machine via API.
    """
    if not policy.get("wayback_save", False):
        return None

    wayback_api = policy.get("wayback_api_url", "https://web.archive.org/save/")

    try:
        save_url = f"{wayback_api}{url}"
        response = requests.get(save_url, timeout=30)

        if response.status_code == 200:
            # Extract archive URL from Content-Location header
            archive_url = response.headers.get("Content-Location")

            if archive_url:
                # Content-Location is a relative path, make it absolute
                if archive_url.startswith("/"):
                    archive_url = f"https://web.archive.org{archive_url}"
                print(f"  [wayback] ✓ Archived: {archive_url}")
                return archive_url
            else:
                print(f"  [wayback] ⚠️  Saved but no archive URL returned")
                return f"https://web.archive.org/web/*/{url}"
        else:
            print(f"  [wayback] ⚠️  Failed (status={response.status_code})")
            return None

    except Exception as e:
        print(f"  [wayback] ⚠️  Error: {e}")
        return None


def fetch_page(url: str, policy: dict) -> Dict:
    """
    Fetch product page with throttling, retries, and exponential backoff.
    """
    headers = {
        "User-Agent": policy["user_agent"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive"
    }
    timeout = policy["timeout_seconds"]
    max_retries = policy["max_retries"]
    backoff_factor = policy["backoff_factor"]

    print(f"  [fetch] {url}")

    # Respect throttle BEFORE fetching
    time.sleep(policy["throttle_seconds"])

    for attempt in range(max_retries + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True
            )

            html = response.text
            sha256 = hashlib.sha256(html.encode()).hexdigest()

            if response.status_code == 200:
                print(f"    ✓ Fetched ({len(html)} chars)")
                return {
                    "html": html,
                    "sha256": sha256,
                    "status_code": response.status_code,
                    "captured_at": datetime.utcnow().isoformat() + "Z"
                }
            else:
                print(f"    ⚠️  Status {response.status_code}")
                if attempt < max_retries:
                    wait_time = backoff_factor ** attempt
                    print(f"    Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    return {
                        "html": "",
                        "sha256": "",
                        "status_code": response.status_code,
                        "captured_at": datetime.utcnow().isoformat() + "Z"
                    }

        except Exception as e:
            print(f"    ⚠️  Error: {e}")

            if attempt < max_retries:
                wait_time = backoff_factor ** attempt
                print(f"    Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                return {
                    "html": "",
                    "sha256": "",
                    "status_code": 0,
                    "captured_at": datetime.utcnow().isoformat() + "Z"
                }

    return {
        "html": "",
        "sha256": "",
        "status_code": 0,
        "captured_at": datetime.utcnow().isoformat() + "Z"
    }


def extract_assets(html: str, base_url: str) -> list:
    """
    Extract product image URLs from HTML.
    Focus on product images (main image + gallery).
    """
    soup = BeautifulSoup(html, "lxml")
    images = []
    seen_urls = set()

    # Amazon-specific selectors for product images
    selectors = [
        "#landingImage",  # Main product image
        "#main-image",
        ".a-dynamic-image",  # Gallery images
        "#altImages img",  # Alternative images
        "[data-a-dynamic-image]"  # Dynamic image data
    ]

    for selector in selectors:
        for elem in soup.select(selector):
            # Try different attributes
            for attr in ["src", "data-old-hires", "data-a-dynamic-image"]:
                src = elem.get(attr, "")

                if src:
                    # Handle dynamic image JSON
                    if attr == "data-a-dynamic-image":
                        try:
                            import json
                            img_data = json.loads(src)
                            # Get highest resolution URL
                            urls = list(img_data.keys())
                            if urls:
                                src = urls[0]
                        except:
                            continue

                    full_url = urljoin(base_url, src)

                    # Filter out small/icon images
                    if full_url not in seen_urls and ("images-amazon.com" in full_url or "ssl-images-amazon.com" in full_url):
                        images.append({
                            "url": full_url,
                            "alt": elem.get("alt", "")
                        })
                        seen_urls.add(full_url)

    # Fallback: get all img tags if no specific images found
    if not images:
        for img in soup.find_all("img")[:5]:
            src = img.get("src", "")
            if src and src not in seen_urls:
                full_url = urljoin(base_url, src)
                images.append({
                    "url": full_url,
                    "alt": img.get("alt", "")
                })
                seen_urls.add(src)

    return images[:10]  # Limit to 10 images max


def main():
    parser = argparse.ArgumentParser(description="Scrape product pages")
    parser.add_argument("--in", dest="input_csv", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="SHA256 index CSV")
    parser.add_argument("--assets", type=Path, required=True, help="Assets index CSV")
    parser.add_argument("--html-dir", type=Path, required=True, help="HTML storage directory")
    parser.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args()

    policy = load_scraping_policy(args.policy)

    print(f"Scraping from {args.input_csv}")
    print(f"Policy: throttle={policy['throttle_seconds']}s, max_retries={policy['max_retries']}")

    # Create HTML storage directory
    args.html_dir.mkdir(parents=True, exist_ok=True)

    pages = []
    assets = []

    with open(args.input_csv) as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            asin = row["asin"]
            url = row["url"]

            print(f"\n[{i+1}] {asin}: {url}")

            # Check robots.txt
            if not check_robots_txt("www.amazon.com", policy["user_agent"]):
                print("  [SKIP] robots.txt disallows")
                continue

            # Fetch page
            result = fetch_page(url, policy)

            if result["status_code"] != 200 or not result["html"]:
                print("  [SKIP] Failed to fetch")
                continue

            # Save HTML to disk
            html_path = args.html_dir / f"{asin}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(result["html"])
            print(f"  [SAVE] HTML saved to {html_path}")

            # Wayback archive
            wayback_url = save_to_wayback(url, policy)

            pages.append({
                "asin": asin,
                "page_sha256": result["sha256"],
                "wayback_url": wayback_url or "",
                "captured_at": result["captured_at"],
                "status_code": result["status_code"]
            })

            # Extract assets
            page_assets = extract_assets(result["html"], url)
            for j, asset in enumerate(page_assets):
                assets.append({
                    "asin": asin,
                    "asset_id": f"{asin}_img{j:02d}",
                    "asset_type": "image",
                    "url": asset["url"],
                    "wayback_url": "",  # TODO: Archive images
                    "sha256": hashlib.sha256(asset["url"].encode()).hexdigest(),  # Full 64-char hash
                    "storage_uri": "",
                    "width": "",
                    "height": ""
                })

    # Write outputs
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as f:
        fieldnames = ["asin", "page_sha256", "wayback_url", "captured_at", "status_code"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(pages)

    args.assets.parent.mkdir(parents=True, exist_ok=True)
    with open(args.assets, "w", newline="") as f:
        fieldnames = ["asin", "asset_id", "asset_type", "url", "wayback_url", "sha256", "storage_uri", "width", "height"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(assets)

    print(f"\n✓ Scraped {len(pages)} pages")
    print(f"✓ Indexed {len(assets)} assets")
    print(f"✓ Saved to {args.out}, {args.assets}")


if __name__ == "__main__":
    main()
