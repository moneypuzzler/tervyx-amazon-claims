.PHONY: setup all generate scrape extract normalize validate weights report clean

# Configuration
PLAN := configs/sampling_plan.yaml
SCRAPE_POLICY := configs/scraping_policy.yaml
EXTRACT_POLICY := configs/extraction_policy.yaml
HINTS := configs/policy_hints.yaml

# Data paths
URLS := data/raw/product_urls.csv
PAGES := data/extracted/pages.sha256.csv
ASSETS := data/processed/assets_index.csv
CLAIMS_RAW := data/extracted/claims_raw.jsonl
PRODUCT_CSV := data/processed/product_info.csv
CLAIMS_CSV := data/processed/claims.csv
REPORT := data/reports/top_patterns.csv

# Setup environment
setup:
\tpython3 -m venv .venv
\t@echo "✓ Virtual environment created"
\t@echo "  Activate with: source .venv/bin/activate"
\t@echo "  Then run: pip install -r requirements.txt"

# Full pipeline
all: generate scrape extract normalize validate weights report

# Step 1: Generate URLs
generate:
\tpython scripts/1_generate_urls.py --plan $(PLAN) --out $(URLS)

# Step 2: Scrape pages
scrape:
\tpython scripts/2_scrape_pages.py --in $(URLS) --out $(PAGES) --assets $(ASSETS) --policy $(SCRAPE_POLICY)

# Step 3: Extract claims
extract:
\tpython scripts/3_extract_claims.py --assets $(ASSETS) --out $(CLAIMS_RAW) --policy $(EXTRACT_POLICY)

# Step 4: Normalize to CSV
normalize:
\tpython scripts/4_normalize_to_csv.py \
\t\t--raw $(CLAIMS_RAW) \
\t\t--product-urls $(URLS) \
\t\t--product-out $(PRODUCT_CSV) \
\t\t--claims-out $(CLAIMS_CSV) \
\t\t--assets-in $(ASSETS) \
\t\t--hints $(HINTS)

# Step 5: Validate
validate:
\tpython scripts/5_qc_validate.py \
\t\t--schemas schemas/ \
\t\t--product $(PRODUCT_CSV) \
\t\t--claims $(CLAIMS_CSV) \
\t\t--assets $(ASSETS)

# Step 6: Compute weights
weights:
\tpython scripts/6_sampling_weights.py --product $(PRODUCT_CSV) --plan $(PLAN)

# Step 7: Generate pattern report
report:
\tpython scripts/7_pattern_report.py --claims $(CLAIMS_CSV) --out $(REPORT)

# Clean generated data (keep configs/schemas)
clean:
\trm -rf data/raw/*.csv data/extracted/* data/processed/*.csv data/reports/*
\t@echo "✓ Cleaned data directories"

# Quick test (sample 10)
test:
\tpython scripts/1_generate_urls.py --plan $(PLAN) --out $(URLS) --sample 10
\t$(MAKE) scrape extract normalize validate
