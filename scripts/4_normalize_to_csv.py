#!/usr/bin/env python3
"""
TERVYX Amazon Claims — Normalization (JSONL → CSV + Policy Hints)
Map claims to standard CSV schema and apply gate hint signals.
"""

import argparse
import csv
import json
import hashlib
import yaml
import re
from pathlib import Path
from typing import List, Dict, Set


def load_policy_hints(hints_path: Path) -> dict:
    """Load policy hints YAML."""
    with open(hints_path) as f:
        return yaml.safe_load(f)


def map_phi_hints(text: str, hints: dict) -> List[str]:
    """Map Φ gate hints (physics/physiology violations)."""
    ids = []
    for hint_id, conf in hints["phi"].items():
        for pattern in conf["patterns"]:
            if re.search(pattern, text, flags=re.IGNORECASE):
                ids.append(hint_id)
                break
    return ids


def map_k_hints(text: str, ingredients: List[str], hints: dict) -> List[str]:
    """Map K gate hints (safety/regulatory)."""
    ids = []
    combined = text + " " + " ".join(ingredients or [])

    for hint_id, conf in hints["k"].items():
        for pattern in conf["patterns"]:
            if re.search(pattern, combined, flags=re.IGNORECASE):
                ids.append(hint_id)
                break
    return ids


def map_l_tokens(text: str, hints: dict) -> tuple[List[str], int]:
    """Map L gate tokens and compute score."""
    weights = hints["l"]["weights"]
    tokens = []
    score = 0

    text_lower = text.lower()
    for token, weight in weights.items():
        if token.lower() in text_lower:
            tokens.append(token)
            score += weight

    return tokens, score


def compute_gate_hint(phi_ids: List[str], k_ids: List[str], l_score: int) -> str:
    """Compute overall gate hint."""
    if k_ids:
        return "k_candidate"
    if phi_ids:
        return "phi_candidate"
    if l_score >= 3:
        return "l_hard"
    if l_score > 0:
        return "l_soft"
    return "none"


def main():
    parser = argparse.ArgumentParser(description="Normalize claims to CSV")
    parser.add_argument("--raw", type=Path, required=True, help="claims_raw.jsonl")
    parser.add_argument("--product-urls", type=Path, required=True)
    parser.add_argument("--product-out", type=Path, required=True)
    parser.add_argument("--claims-out", type=Path, required=True)
    parser.add_argument("--assets-in", type=Path, required=True)
    parser.add_argument("--hints", type=Path, default=Path("configs/policy_hints.yaml"))
    args = parser.parse_args()

    hints = load_policy_hints(args.hints)

    print(f"Normalizing {args.raw} → CSV")

    # Load URL metadata
    url_meta = {}
    with open(args.product_urls) as f:
        for row in csv.DictReader(f):
            url_meta[row["asin"]] = row

    # Process JSONL
    products = {}
    claims = []

    with open(args.raw) as f:
        for line_num, line in enumerate(f, 1):
            entry = json.loads(line)
            asin = entry["asin"]

            # Initialize product record
            if asin not in products:
                meta = url_meta.get(asin, {})
                products[asin] = {
                    "asin": asin,
                    "platform": "amazon",
                    "category_path": meta.get("category_hint", ""),
                    "intervention_type": "supplement",  # FIXME: Infer from category
                    "product_title": f"Product {asin}",
                    "brand": "",
                    "price": "",
                    "currency": "USD",
                    "product_url": f"https://www.amazon.com/dp/{asin}",
                    "wayback_url": f"https://web.archive.org/web/20251112000000/...",
                    "captured_at": "2025-11-12T00:00:00Z",
                    "sampling_cohort": meta.get("cohort", "R"),
                    "selection_method": meta.get("method", "random"),
                    "sampling_weight": "1.0" if meta.get("cohort") == "R" else "",
                    "sampling_frame_version": "v2025-11-12",
                    "product_sha256": entry["page_sha256"],
                    "ingredients_raw": "",
                    "ingredients_norm": "[]",
                    "risk_hits": "[]",
                    "fda_warning_match": "false",
                    "phi_any_candidate": "false",
                    "k_any_candidate": "false",
                    "l_max_token_score": "0"
                }

            # Process claims
            for claim_data in entry["claims"]:
                claim_id = f"{asin}_c{len(claims):04d}"
                claim_text = claim_data["text"]

                # Map hints
                phi_ids = map_phi_hints(claim_text, hints)
                k_ids = map_k_hints(claim_text, [], hints)
                l_tokens, l_score = map_l_tokens(claim_text, hints)
                gate_hint = compute_gate_hint(phi_ids, k_ids, l_score)

                # Update product aggregates
                if phi_ids:
                    products[asin]["phi_any_candidate"] = "true"
                if k_ids:
                    products[asin]["k_any_candidate"] = "true"
                products[asin]["l_max_token_score"] = str(max(
                    int(products[asin]["l_max_token_score"]),
                    l_score
                ))

                # Claim record
                claims.append({
                    "asin": asin,
                    "claim_id": claim_id,
                    "claim_text_verbatim": claim_text,
                    "claim_type": claim_data.get("claim_type", "efficacy"),
                    "implied_outcome": claim_data.get("implied_outcome", ""),
                    "quantifier": claim_data.get("quantifier", ""),
                    "has_citation": "false",
                    "source": claim_data.get("source", "html"),
                    "ocr_bbox": claim_data.get("bbox", ""),
                    "extraction_model": entry["extraction"]["model"],
                    "extraction_version": entry["extraction"]["version"],
                    "extraction_temperature": str(entry["extraction"]["temperature"]),
                    "claim_sha256": hashlib.sha256(claim_text.encode()).hexdigest(),
                    "page_sha256": entry["page_sha256"],
                    "claim_scope": "wellness",
                    "has_numeric_quantifier": str(claim_data.get("has_numeric_quantifier", False)).lower(),
                    "quant_value": claim_data.get("quant_value", ""),
                    "quant_unit": claim_data.get("quant_unit", ""),
                    "comparator": claim_data.get("comparator", ""),
                    "phi_hint_ids": json.dumps(phi_ids),
                    "k_hint_ids": json.dumps(k_ids),
                    "l_tokens": json.dumps(l_tokens),
                    "l_token_score": str(l_score),
                    "ingredient_hits": "[]",
                    "medical_scope_flag": "false",
                    "evidence_anchor_id": "",
                    "extract_confidence": str(claim_data.get("confidence", 0.9)),
                    "claim_group_id": "",
                    "gate_hint": gate_hint,
                    "review_needed": str(claim_data.get("confidence", 1.0) < 0.8).lower()
                })

    # Write product CSV
    args.product_out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.product_out, "w", newline="") as f:
        fieldnames = list(list(products.values())[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(products.values())

    # Write claims CSV
    args.claims_out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.claims_out, "w", newline="") as f:
        fieldnames = list(claims[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(claims)

    print(f"✓ Products: {len(products)} → {args.product_out}")
    print(f"✓ Claims: {len(claims)} → {args.claims_out}")


if __name__ == "__main__":
    main()
