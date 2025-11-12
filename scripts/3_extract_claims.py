#!/usr/bin/env python3
"""
TERVYX Amazon Claims — Claim Extraction (LLM = Extraction Only, temp=0)
Extract claims from HTML/images (verbatim text, no judgment).
"""

import argparse
import json
import hashlib
import yaml
from pathlib import Path
from typing import List, Dict
from datetime import datetime


def load_extraction_policy(policy_path: Path) -> dict:
    """Load extraction policy YAML."""
    with open(policy_path) as f:
        return yaml.safe_load(f)


def extract_from_html(html: str, asin: str, policy: dict) -> List[Dict]:
    """
    Extract claims from HTML using Gemini API (temp=0).
    """
    import os
    from bs4 import BeautifulSoup

    # Parse HTML to extract relevant sections
    soup = BeautifulSoup(html, "lxml")

    # Extract text sections (Amazon-specific)
    sections = []

    # Product title
    title = soup.select_one("#productTitle")
    if title:
        sections.append(("title", title.get_text(strip=True)))

    # Feature bullets
    for bullet in soup.select("#feature-bullets-btf li span.a-list-item, #feature-bullets li span.a-list-item"):
        text = bullet.get_text(strip=True)
        if text:
            sections.append(("bullet", text))

    # Product description
    desc = soup.select_one("#productDescription")
    if desc:
        sections.append(("description", desc.get_text(strip=True)[:2000]))  # Limit length

    # A+ content
    for aplus in soup.select("[data-template-name] .aplus-module-wrapper"):
        text = aplus.get_text(strip=True)[:1000]
        if text:
            sections.append(("aplus", text))

    if not sections:
        return []

    # Use LLM for extraction if enabled
    if policy.get("use_llm", True):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print(f"    ⚠️  GEMINI_API_KEY not set, using rule-based extraction")
            return _extract_rules_based(sections, policy)

        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(policy["model"])

            # Build prompt
            text_content = "\n\n".join([f"[{source.upper()}]\n{text}" for source, text in sections])

            prompt = f"""Extract ALL health, efficacy, or medical claims from this Amazon product page.

RULES:
- Return verbatim claim text (no paraphrasing)
- Include quantifiers (percentages, numbers, timeframes)
- Classify claim_type: efficacy | safety | mechanism | medical
- Extract implied_outcome if obvious (sleep, hair_growth, weight_loss, pain_relief, etc.)
- Extract quantifier values
- DO NOT make judgments or evaluations
- DO NOT add claims that are not in the text

Return JSON array:
[
  {{
    "text": "verbatim claim text",
    "claim_type": "efficacy",
    "implied_outcome": "sleep_quality",
    "quantifier": "87%",
    "has_numeric_quantifier": true
  }}
]

Product text:
{text_content}
"""

            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": policy["temperature"],
                    "response_mime_type": "application/json" if policy.get("json_mode", True) else "text/plain",
                    "max_output_tokens": policy.get("max_tokens", 2048)
                }
            )

            # Parse response
            import json
            claims_data = json.loads(response.text)

            # Add metadata
            claims = []
            for claim in claims_data:
                claims.append({
                    "text": claim.get("text", ""),
                    "source": "html",
                    "confidence": 0.9,  # High confidence for LLM extraction at temp=0
                    "bbox": None,
                    "claim_type": claim.get("claim_type", "unknown"),
                    "implied_outcome": claim.get("implied_outcome", ""),
                    "quantifier": claim.get("quantifier", ""),
                    "has_numeric_quantifier": claim.get("has_numeric_quantifier", False)
                })

            return claims

        except Exception as e:
            print(f"    ⚠️  LLM extraction error: {e}")
            return _extract_rules_based(sections, policy)
    else:
        return _extract_rules_based(sections, policy)


def _extract_rules_based(sections: List[tuple], policy: dict) -> List[Dict]:
    """
    Fallback: rule-based claim extraction.
    """
    import re

    claims = []
    claim_keywords = [
        r"proven", r"clinically", r"guaranteed", r"effective", r"results",
        r"cure", r"treat", r"prevent", r"relieve", r"reduce",
        r"improve", r"boost", r"enhance", r"support", r"promote",
        r"\d+%", r"instant", r"fast", r"quick", r"immediate"
    ]

    pattern = re.compile("|".join(claim_keywords), re.IGNORECASE)

    for source, text in sections:
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)

        for sentence in sentences:
            sentence = sentence.strip()

            # Check for claim keywords
            if pattern.search(sentence) and len(sentence) >= policy.get("min_claim_length", 10):
                claims.append({
                    "text": sentence,
                    "source": "html",
                    "confidence": 0.6,  # Lower confidence for rule-based
                    "bbox": None,
                    "claim_type": "unknown",
                    "implied_outcome": "",
                    "quantifier": "",
                    "has_numeric_quantifier": bool(re.search(r'\d+', sentence))
                })

    return claims[:20]  # Limit to 20 claims max


def extract_from_image(image_url: str, asset_id: str, policy: dict) -> List[Dict]:
    """
    Extract claims from product images using OCR (Tesseract).
    """
    import os
    import requests
    from PIL import Image
    from io import BytesIO

    try:
        import pytesseract
    except ImportError:
        print(f"    ⚠️  pytesseract not available, skipping image {asset_id}")
        return []

    try:
        # Download image
        response = requests.get(image_url, timeout=10)
        img = Image.open(BytesIO(response.content))

        # Run OCR
        ocr_data = pytesseract.image_to_data(
            img,
            lang=policy.get("ocr_lang", "eng"),
            output_type=pytesseract.Output.DICT
        )

        # Extract text with confidence filtering
        texts = []
        bboxes = []
        threshold = policy.get("ocr_confidence_threshold", 0.7) * 100

        for i, conf in enumerate(ocr_data["conf"]):
            if int(conf) > threshold:
                text = ocr_data["text"][i].strip()
                if text:
                    texts.append(text)
                    bbox = [
                        ocr_data["left"][i],
                        ocr_data["top"][i],
                        ocr_data["left"][i] + ocr_data["width"][i],
                        ocr_data["top"][i] + ocr_data["height"][i]
                    ]
                    bboxes.append(bbox)

        if not texts:
            return []

        raw_text = " ".join(texts)

        # Optional: LLM cleanup
        if policy.get("use_llm_for_ocr_cleanup", False):
            cleaned_claims = _cleanup_ocr_with_llm(raw_text, policy)
            return cleaned_claims

        # Rule-based extraction from OCR text
        claims = []
        claim_keywords = [
            r"proven", r"clinically", r"guaranteed", r"effective", r"results",
            r"cure", r"treat", r"prevent", r"miracle", r"instant",
            r"\d+%", r"100%"
        ]

        import re
        pattern = re.compile("|".join(claim_keywords), re.IGNORECASE)

        if pattern.search(raw_text):
            claims.append({
                "text": raw_text[:500],  # Limit length
                "source": "image",
                "confidence": 0.7,
                "bbox": str(bboxes) if bboxes else None,
                "claim_type": "unknown",
                "implied_outcome": "",
                "quantifier": "",
                "has_numeric_quantifier": bool(re.search(r'\d+', raw_text))
            })

        return claims

    except Exception as e:
        print(f"    ⚠️  OCR error for {asset_id}: {e}")
        return []


def _cleanup_ocr_with_llm(raw_text: str, policy: dict) -> List[Dict]:
    """
    Use LLM to clean up and structure OCR output.
    """
    import os
    import json

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return []

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(policy["model"])

        prompt = f"""Clean up this OCR text and extract any health/efficacy claims.

OCR may have errors. Fix obvious typos but preserve original meaning.

Return JSON array of claims:
[
  {{
    "text": "cleaned claim text",
    "claim_type": "efficacy",
    "quantifier": "..."
  }}
]

OCR text:
{raw_text}
"""

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0,
                "response_mime_type": "application/json"
            }
        )

        claims_data = json.loads(response.text)

        claims = []
        for claim in claims_data:
            claims.append({
                "text": claim.get("text", ""),
                "source": "image",
                "confidence": 0.75,  # Medium confidence for OCR + LLM
                "bbox": None,
                "claim_type": claim.get("claim_type", "unknown"),
                "implied_outcome": claim.get("implied_outcome", ""),
                "quantifier": claim.get("quantifier", ""),
                "has_numeric_quantifier": bool(claim.get("quantifier"))
            })

        return claims

    except Exception as e:
        print(f"    ⚠️  LLM cleanup error: {e}")
        return []


def classify_claim(claim_text: str) -> Dict:
    """
    Classify claim type and implied outcome.

    TODO: Implement classification
    - Rule-based keyword matching
    - Optional: lightweight ML classifier
    - Return: claim_type, implied_outcome, quantifiers
    """
    # FIXME: Replace with actual logic
    return {
        "claim_type": "efficacy",
        "implied_outcome": "sleep_quality",
        "quantifier": "87%",
        "has_numeric_quantifier": True,
        "quant_value": "87",
        "quant_unit": "%",
        "comparator": None
    }


def main():
    parser = argparse.ArgumentParser(description="Extract claims from pages")
    parser.add_argument("--pages", type=Path, required=True, help="Pages SHA256 CSV")
    parser.add_argument("--assets", type=Path, required=True, help="Assets index CSV")
    parser.add_argument("--html-dir", type=Path, required=True, help="HTML storage directory")
    parser.add_argument("--out", type=Path, required=True, help="Output JSONL")
    parser.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args()

    policy = load_extraction_policy(args.policy)

    print(f"Extracting claims (model={policy['model']}, temp={policy['temperature']})")

    if policy["temperature"] != 0:
        raise ValueError("❌ extraction_temperature MUST be 0 (deterministic)")

    # Load pages index
    import csv

    pages_data = {}
    with open(args.pages) as f:
        reader = csv.DictReader(f)
        for row in reader:
            pages_data[row["asin"]] = row

    # Load assets index
    assets_data = {}
    with open(args.assets) as f:
        reader = csv.DictReader(f)
        for row in reader:
            asin = row["asin"]
            if asin not in assets_data:
                assets_data[asin] = []
            assets_data[asin].append(row)

    extractions = []

    # Process each product
    for asin, page_row in pages_data.items():
        print(f"\n[{asin}] Extracting claims")

        # Load HTML
        html_path = args.html_dir / f"{asin}.html"
        if not html_path.exists():
            print(f"  ⚠️  HTML not found: {html_path}")
            continue

        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        page_sha256 = page_row["page_sha256"]

        # Extract from HTML
        print(f"  [HTML] Extracting claims...")
        html_claims = extract_from_html(html, asin, policy)
        print(f"    ✓ Found {len(html_claims)} claims")

        # Group HTML claims
        if html_claims:
            extractions.append({
                "asin": asin,
                "asset_id": f"{asin}_html",
                "source": "html",
                "extraction": {
                    "model": policy["model"],
                    "version": "v2025-11-12",
                    "temperature": policy["temperature"]
                },
                "claims": html_claims,
                "page_sha256": page_sha256
            })

        # Extract from images
        if asin in assets_data:
            for asset_row in assets_data[asin]:
                if asset_row["asset_type"] == "image":
                    asset_id = asset_row["asset_id"]
                    image_url = asset_row["url"]

                    print(f"  [IMAGE] {asset_id}")
                    image_claims = extract_from_image(image_url, asset_id, policy)

                    if image_claims:
                        print(f"    ✓ Found {len(image_claims)} claims")
                        extractions.append({
                            "asin": asin,
                            "asset_id": asset_id,
                            "source": "image",
                            "extraction": {
                                "model": policy["model"],
                                "version": "v2025-11-12",
                                "temperature": policy["temperature"]
                            },
                            "claims": image_claims,
                            "page_sha256": page_sha256
                        })

    # Write JSONL
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        for extraction in extractions:
            f.write(json.dumps(extraction) + "\n")

    total_claims = sum(len(e["claims"]) for e in extractions)
    print(f"\n✓ Extracted {total_claims} claims from {len(pages_data)} products")
    print(f"✓ Saved to {args.out}")


if __name__ == "__main__":
    main()
