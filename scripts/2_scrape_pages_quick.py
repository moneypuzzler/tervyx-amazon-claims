#!/usr/bin/env python3
"""
Quick simulation mode for testing pipeline without actual scraping.
Generates realistic test HTML for 100 products.
"""

import argparse
import csv
import hashlib
import yaml
from pathlib import Path
from datetime import datetime
import random

# Sample claim templates
CLAIM_TEMPLATES = [
    "Clinically proven to improve {outcome} by {percent}%",
    "100% natural {ingredient} for fast {outcome}",
    "Instant relief from {symptom}",
    "Miracle {product_type} with guaranteed results",
    "Scientifically formulated to boost {outcome}",
    "FDA-approved formula for {outcome}",
    "Quantum energy technology for enhanced {outcome}",
    "Colloidal silver solution for immune support",
    "Homeopathic remedy for {symptom}",
    "Detoxifies your body in just {days} days",
    "Magnetic therapy bracelet for pain relief",
    "Kratom extract for energy and focus",
    "Cure {symptom} naturally without side effects",
    "Lose {pounds} pounds in {days} days",
    "Regrow hair in just {weeks} weeks",
]

OUTCOMES = ["sleep quality", "energy levels", "hair growth", "weight loss", "immune function", "cognitive performance"]
SYMPTOMS = ["pain", "inflammation", "anxiety", "fatigue", "insomnia", "joint pain"]
INGREDIENTS = ["herbs", "botanicals", "minerals", "vitamins", "adaptogens", "probiotics"]
PRODUCT_TYPES = ["supplement", "device", "cream", "drops", "patch", "pills"]

def generate_html(asin: str, cohort: str, stratum: str) -> str:
    """Generate realistic test HTML with health claims."""

    # More aggressive claims for T cohort
    if cohort == "T":
        if "Quantum" in stratum or "Magnetic" in stratum:
            claims = [
                "Quantum energy field healing technology",
                "Scalar wave therapy for cellular regeneration",
                "Magnetic field alignment for pain relief"
            ]
        elif "Colloidal" in stratum or "Kratom" in stratum:
            claims = [
                "Pure colloidal silver solution kills bacteria instantly",
                "Premium kratom extract for natural pain relief",
                "Tejocote root for rapid weight loss"
            ]
        elif "Homeopathic" in stratum or "Detox" in stratum:
            claims = [
                "Homeopathic remedy 30C dilution for flu prevention",
                "Ionic detox foot bath removes heavy metals",
                "Detoxifies liver and kidneys in 7 days"
            ]
        else:
            claims = [
                "Miracle cure for chronic conditions",
                "100% effective guaranteed results",
                "Instant healing with no side effects"
            ]
    else:
        # Milder claims for R cohort
        num_claims = random.randint(2, 5)
        claims = []
        for _ in range(num_claims):
            template = random.choice(CLAIM_TEMPLATES)
            claim = template.format(
                outcome=random.choice(OUTCOMES),
                symptom=random.choice(SYMPTOMS),
                ingredient=random.choice(INGREDIENTS),
                product_type=random.choice(PRODUCT_TYPES),
                percent=random.choice([87, 95, 78, 92, 100]),
                days=random.choice([7, 14, 30]),
                pounds=random.choice([10, 15, 20, 25]),
                weeks=random.choice([4, 6, 8, 12])
            )
            claims.append(claim)

    title = f"{stratum} Product {asin}"

    html = f"""<!DOCTYPE html>
<html>
<head><title>{title}</title></head>
<body>
<div id="productTitle">{title}</div>
<div id="feature-bullets">
<ul>
"""

    for claim in claims:
        html += f'  <li><span class="a-list-item">{claim}</span></li>\n'

    html += """</ul>
</div>
<div id="productDescription">
<p>This premium product is designed to support your health and wellness goals.</p>
"""

    for claim in claims[:2]:
        html += f'<p>{claim}</p>\n'

    html += """</div>
<div class="aplus-module-wrapper">
<p>A+ Content with additional claims and marketing materials.</p>
</div>
<img src="https://m.media-amazon.com/images/I/sample1.jpg" class="a-dynamic-image" alt="Product Image 1"/>
<img src="https://m.media-amazon.com/images/I/sample2.jpg" class="a-dynamic-image" alt="Product Image 2"/>
</body>
</html>"""

    return html


def main():
    parser = argparse.ArgumentParser(description="Quick scrape simulation")
    parser.add_argument("--in", dest="input_csv", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--html-dir", type=Path, required=True)
    args = parser.parse_args()

    # Create output directories
    args.html_dir.mkdir(parents=True, exist_ok=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.assets.parent.mkdir(parents=True, exist_ok=True)

    pages = []
    assets = []

    with open(args.input_csv) as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            asin = row["asin"]
            cohort = row["cohort"]
            stratum = row.get("stratum", row.get("category_hint", "unknown"))

            if (i + 1) % 20 == 0:
                print(f"  [{i+1}] Processing {asin}...")

            # Generate HTML
            html = generate_html(asin, cohort, stratum)
            sha256 = hashlib.sha256(html.encode()).hexdigest()

            # Save HTML
            html_path = args.html_dir / f"{asin}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)

            pages.append({
                "asin": asin,
                "page_sha256": sha256,
                "wayback_url": f"https://web.archive.org/web/20251119/{row['url']}",
                "captured_at": datetime.utcnow().isoformat() + "Z",
                "status_code": 200
            })

            # Generate asset entries
            for j in range(2):
                assets.append({
                    "asin": asin,
                    "asset_id": f"{asin}_img{j:02d}",
                    "asset_type": "image",
                    "url": f"https://m.media-amazon.com/images/I/{asin}_sample{j+1}.jpg",
                    "wayback_url": "",
                    "sha256": hashlib.sha256(f"{asin}_img{j}".encode()).hexdigest(),
                    "storage_uri": "",
                    "width": "",
                    "height": ""
                })

    # Write outputs
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["asin", "page_sha256", "wayback_url", "captured_at", "status_code"])
        writer.writeheader()
        writer.writerows(pages)

    with open(args.assets, "w", newline="") as f:
        fieldnames = ["asin", "asset_id", "asset_type", "url", "wayback_url", "sha256", "storage_uri", "width", "height"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(assets)

    print(f"\n✓ Generated {len(pages)} test pages")
    print(f"✓ Indexed {len(assets)} assets")
    print(f"✓ Saved to {args.out}, {args.assets}")


if __name__ == "__main__":
    main()
