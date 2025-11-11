#!/usr/bin/env python3
"""
TERVYX Amazon Claims — Quality Control & Validation
Validate CSVs against schemas and policy requirements.
"""

import argparse
import csv
import json
import jsonschema
from pathlib import Path
from typing import Dict, List


def load_schema(schema_path: Path) -> dict:
    """Load JSON schema."""
    with open(schema_path) as f:
        return json.load(f)


def validate_csv(csv_path: Path, schema: dict, name: str) -> tuple[bool, List[str]]:
    """Validate CSV rows against schema."""
    errors = []

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            # Convert empty strings to None for nullable fields
            row_cleaned = {k: (v if v != "" else None) for k, v in row.items()}

            # Convert string booleans
            for k, v in row_cleaned.items():
                if v in ("true", "false"):
                    row_cleaned[k] = (v == "true")

            # Convert numeric strings (respecting schema types)
            for k, v in row_cleaned.items():
                if v:
                    # Integer fields (scores)
                    if k.endswith("_score"):
                        try:
                            row_cleaned[k] = int(v)
                        except ValueError:
                            pass
                    # Float fields (weights, prices)
                    elif k.endswith(("_weight", "price")):
                        try:
                            row_cleaned[k] = float(v)
                        except ValueError:
                            pass

            try:
                jsonschema.validate(row_cleaned, schema)
            except jsonschema.ValidationError as e:
                errors.append(f"Row {i}: {e.message}")

    return (len(errors) == 0), errors


def check_extraction_temperature(claims_csv: Path) -> tuple[bool, List[str]]:
    """Ensure extraction_temperature == 0 (deterministic requirement)."""
    errors = []

    with open(claims_csv) as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            temp = float(row.get("extraction_temperature", 0))
            if temp != 0.0:
                errors.append(f"Row {i}: extraction_temperature={temp} (MUST be 0)")

    return (len(errors) == 0), errors


def check_required_fields(csv_path: Path, required: List[str]) -> tuple[bool, List[str]]:
    """Check for missing required fields."""
    errors = []

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            for field in required:
                if not row.get(field):
                    errors.append(f"Row {i}: Missing required field '{field}'")

    return (len(errors) == 0), errors


def main():
    parser = argparse.ArgumentParser(description="Validate CSV outputs")
    parser.add_argument("--schemas", type=Path, required=True, help="Schema directory")
    parser.add_argument("--product", type=Path, required=True)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    args = parser.parse_args()

    print("=" * 60)
    print("TERVYX Amazon Claims — QC Validation")
    print("=" * 60)

    all_pass = True

    # Validate product_info
    print("\n[1/4] Validating product_info.csv...")
    schema = load_schema(args.schemas / "product_info.schema.json")
    passed, errors = validate_csv(args.product, schema, "product_info")
    if passed:
        print("  ✓ Schema validation PASSED")
    else:
        print(f"  ✗ Schema validation FAILED ({len(errors)} errors)")
        for err in errors[:5]:  # Show first 5
            print(f"    - {err}")
        all_pass = False

    # Validate claims
    print("\n[2/4] Validating claims.csv...")
    schema = load_schema(args.schemas / "claims.schema.json")
    passed, errors = validate_csv(args.claims, schema, "claims")
    if passed:
        print("  ✓ Schema validation PASSED")
    else:
        print(f"  ✗ Schema validation FAILED ({len(errors)} errors)")
        for err in errors[:5]:
            print(f"    - {err}")
        all_pass = False

    # Check extraction temperature
    print("\n[3/4] Checking extraction_temperature == 0...")
    passed, errors = check_extraction_temperature(args.claims)
    if passed:
        print("  ✓ All claims have temperature=0 (deterministic)")
    else:
        print(f"  ✗ FAILED ({len(errors)} violations)")
        for err in errors[:5]:
            print(f"    - {err}")
        all_pass = False

    # Check critical fields
    print("\n[4/4] Checking critical fields...")
    # Note: wayback_url is in product_info, not claims (join via page_sha256)
    required_claims = ["page_sha256", "claim_sha256"]
    passed, errors = check_required_fields(args.claims, required_claims)
    if passed:
        print("  ✓ All critical fields present")
    else:
        print(f"  ✗ Missing fields ({len(errors)} violations)")
        for err in errors[:5]:
            print(f"    - {err}")
        all_pass = False

    # Summary
    print("\n" + "=" * 60)
    if all_pass:
        print("✓ ALL VALIDATIONS PASSED")
        print("=" * 60)
        return 0
    else:
        print("✗ VALIDATION FAILED — Fix errors before proceeding")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit(main())
