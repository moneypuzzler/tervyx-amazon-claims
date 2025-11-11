#!/usr/bin/env python3
"""
TERVYX Amazon Claims — Export Bundle for A-Repo
Package CSVs + metadata for TERVYX policy engine.
"""

import argparse
import csv
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime


def compute_bundle_hash(files: list) -> str:
    """Compute combined SHA256 of all files in bundle."""
    hasher = hashlib.sha256()
    for f in sorted(files):
        with open(f, "rb") as fh:
            hasher.update(fh.read())
    return hasher.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Export bundle for TERVYX A-repo")
    parser.add_argument("--product", type=Path, required=True)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--out-bundle", type=Path, required=True)
    args = parser.parse_args()

    # Create bundle directory
    bundle_dir = args.out_bundle
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # Copy CSVs
    shutil.copy(args.product, bundle_dir / "product_info.csv")
    shutil.copy(args.claims, bundle_dir / "claims.csv")
    shutil.copy(args.assets, bundle_dir / "assets_index.csv")

    # Generate metadata
    files = [
        bundle_dir / "product_info.csv",
        bundle_dir / "claims.csv",
        bundle_dir / "assets_index.csv"
    ]
    bundle_hash = compute_bundle_hash(files)

    # Count rows
    with open(args.product) as f:
        n_products = sum(1 for _ in csv.DictReader(f))
    with open(args.claims) as f:
        n_claims = sum(1 for _ in csv.DictReader(f))

    metadata = {
        "bundle_name": "tervyx-amazon-claims-snapshot",
        "version": "v1",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "bundle_hash": bundle_hash,
        "contents": {
            "product_info.csv": {"rows": n_products},
            "claims.csv": {"rows": n_claims},
            "assets_index.csv": {"rows": 0}  # TODO: count
        },
        "description": "Amazon health claims extraction for TERVYX protocol validation",
        "reproducibility": {
            "repo": "https://github.com/<org>/tervyx-amazon-claims",
            "commit": "TODO",  # Add git commit hash
            "pipeline_version": "v1.0"
        }
    }

    with open(bundle_dir / "bundle_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✓ Bundle created: {bundle_dir}")
    print(f"  Products: {n_products}")
    print(f"  Claims: {n_claims}")
    print(f"  Hash: {bundle_hash[:16]}...")


if __name__ == "__main__":
    main()
