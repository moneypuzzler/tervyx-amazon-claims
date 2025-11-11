# TERVYX Amazon Claims — "Rule-to-Market" Scraping

**Extracting Marketing Claims from Amazon Products for TERVYX Protocol Validation**

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)

---

## Overview

This repository implements the **"Rule-to-Market"** pipeline: extracting health/efficacy claims from Amazon product pages, normalizing them to a standard CSV format, and embedding **gate hint signals** (Φ/K/L) for downstream policy-as-code evaluation by the [TERVYX protocol](https://github.com/tervyx/tervyx).

### Key Principles

1. **LLM = Extraction Only** (temp=0): LLMs assist in extracting verbatim claim text, NOT in making judgments
2. **Deterministic Pipeline**: All extraction parameters, policy hints, and sampling logic are versioned and reproducible
3. **Ethics-First**: Robots.txt compliance, transparent User-Agent, throttling, Wayback archival
4. **R/T Cohorts**: Representative (R) + Targeted (T) sampling for both population estimation and stress testing
5. **Gate Hints, Not Judgments**: We tag claims with `phi_hint_ids`, `k_hint_ids`, `l_tokens` — the A-repo policy engine makes final labels

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  TERVYX Amazon Claims (This Repo)                              │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐           │
│  │ 1. Generate │→ │ 2. Scrape    │→ │ 3. Extract  │           │
│  │    URLs     │  │    Pages     │  │    Claims   │           │
│  │   (R/T)     │  │  (Ethics)    │  │  (LLM=0)    │           │
│  └─────────────┘  └──────────────┘  └─────────────┘           │
│         ↓                 ↓                 ↓                   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐           │
│  │ 4. Normalize│→ │ 5. Validate  │→ │ 6. Weights  │           │
│  │   + Hints   │  │   (QC)       │  │   (R only)  │           │
│  └─────────────┘  └──────────────┘  └─────────────┘           │
│         ↓                                                       │
│  ┌─────────────────────────────────────────────────┐           │
│  │ Output: product_info.csv, claims.csv, assets    │           │
│  └─────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│  TERVYX A-Repo (Policy Engine)                                 │
│  Applies Φ/K/L gates → TEL-5 labels → entry.jsonld             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Schema

### `product_info.csv` (1 row = 1 product)

| Field | Type | Description |
|-------|------|-------------|
| `asin` | string | Amazon Standard Identification Number |
| `platform` | string | Always "amazon" |
| `category_path` | string | Category breadcrumb |
| `intervention_type` | enum | supplement \| device_noninvasive \| food \| cosmetic \| other |
| `product_title` | string | Product title (verbatim) |
| `product_url` | url | Original URL |
| `wayback_url` | url | Wayback Machine archive URL |
| `captured_at` | datetime | ISO8601 UTC |
| `sampling_cohort` | enum | R (representative) \| T (targeted) |
| `selection_method` | enum | random \| node_id \| keyword \| bestseller |
| `sampling_weight` | float | Population weight (R only) |
| `sampling_frame_version` | string | Snapshot version (e.g., v2025-11-12) |
| `product_sha256` | string | Page content hash |
| `ingredients_norm` | json | Normalized ingredient list |
| `risk_hits` | json | K policy hint IDs matched |
| `phi_any_candidate` | bool | Any claim has Φ hints |
| `k_any_candidate` | bool | Any claim has K hints |
| `l_max_token_score` | int | Max L score across claims |

### `claims.csv` (1 row = 1 claim)

| Field | Type | Description |
|-------|------|-------------|
| `asin` | string | Product ASIN |
| `claim_id` | string | Unique claim ID |
| `claim_text_verbatim` | string | **Exact claim text (no paraphrasing)** |
| `claim_type` | enum | efficacy \| safety \| mechanism \| medical |
| `implied_outcome` | string | sleep_quality, hair_growth, weight_loss, etc. |
| `quantifier` | string | "87%", "instant", "100%", etc. |
| `source` | enum | html \| image |
| `extraction_model` | string | LLM model name |
| `extraction_temperature` | float | **MUST be 0.0** (deterministic) |
| `claim_sha256` | string | Claim text hash |
| `page_sha256` | string | Source page hash |
| `phi_hint_ids` | json | Φ gate hints (e.g., `["phi_quantum", "phi_magnetic"]`) |
| `k_hint_ids` | json | K gate hints (e.g., `["k_kratom", "k_colloidal_silver"]`) |
| `l_tokens` | json | L tokens (e.g., `["miracle", "100%"]`) |
| `l_token_score` | int | Cumulative L score |
| `gate_hint` | enum | none \| phi_candidate \| k_candidate \| l_soft \| l_hard |
| `review_needed` | bool | Low confidence → manual review |

**Full schema**: See [`configs/fields.yml`](configs/fields.yml) and [`schemas/`](schemas/)

---

## Configuration

### Sampling Plan (`configs/sampling_plan.yaml`)

- **R cohort**: Stratified random sample across health/beauty/device categories (target N=700)
- **T cohort**: High-risk products for Φ/K/L validation (target N=300)
  - Magnetic therapy, ionic detox, quantum pendants (Φ)
  - Colloidal silver, tejocote, kratom (K)
  - "Miracle", "100%", "instant" (L)

### Scraping Policy (`configs/scraping_policy.yaml`)

- **robots.txt compliance**: Always check before scraping
- **Throttling**: 3 seconds between requests
- **User-Agent**: `TERVYX-Protocol-Research-Bot/1.0 (+https://tervyx.org/rule-to-market)`
- **Wayback archival**: Save to Internet Archive
- **Domain whitelist**: `www.amazon.com` only

### Extraction Policy (`configs/extraction_policy.yaml`)

- **LLM**: Gemini 2.0 Flash (low-cost, fast)
- **Temperature**: **0** (deterministic only)
- **Tasks**: Extract verbatim claims, identify quantifiers, classify types

### Policy Hints (`configs/policy_hints.yaml`)

Maps claim text → gate hint IDs using regex patterns:

- **Φ (physics/physiology)**: `phi_quantum`, `phi_magnetic`, `phi_ionic_detox`, `phi_homeopathy`
- **K (safety/regulatory)**: `k_tejocote`, `k_colloidal_silver`, `k_kratom`, ...
- **L (exaggeration)**: Token weights (miracle=3, 100%=2, instant=2, ...)

---

## Installation

```bash
# Clone repository
git clone https://github.com/<org>/tervyx-amazon-claims
cd tervyx-amazon-claims

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

### Full Pipeline (Makefile)

```bash
make all  # Run entire pipeline: generate → scrape → extract → normalize → validate
```

### Step-by-Step

```bash
# 1. Generate URLs (R/T cohorts)
python scripts/1_generate_urls.py \
  --plan configs/sampling_plan.yaml \
  --out data/raw/product_urls.csv

# 2. Scrape pages (ethics-first)
python scripts/2_scrape_pages.py \
  --in data/raw/product_urls.csv \
  --out data/extracted/pages.sha256.csv \
  --assets data/processed/assets_index.csv \
  --policy configs/scraping_policy.yaml

# 3. Extract claims (LLM temp=0)
python scripts/3_extract_claims.py \
  --assets data/processed/assets_index.csv \
  --out data/extracted/claims_raw.jsonl \
  --policy configs/extraction_policy.yaml

# 4. Normalize to CSV + apply hints
python scripts/4_normalize_to_csv.py \
  --raw data/extracted/claims_raw.jsonl \
  --product-urls data/raw/product_urls.csv \
  --product-out data/processed/product_info.csv \
  --claims-out data/processed/claims.csv \
  --assets-in data/processed/assets_index.csv

# 5. Validate (QC)
python scripts/5_qc_validate.py \
  --schemas schemas/ \
  --product data/processed/product_info.csv \
  --claims data/processed/claims.csv \
  --assets data/processed/assets_index.csv

# 6. Compute sampling weights (R cohort)
python scripts/6_sampling_weights.py \
  --product data/processed/product_info.csv \
  --plan configs/sampling_plan.yaml

# 7. Generate pattern report (Φ/K/L stats)
python scripts/7_pattern_report.py \
  --claims data/processed/claims.csv \
  --out data/reports/top_patterns.csv
```

### Quick Test (10 samples)

```bash
make test
```

---

## Gate Hints Logic

### How Hints Work

This repository **tags claims** with hint IDs, but does **NOT make final judgments**. The TERVYX A-repo policy engine applies the actual gates.

#### Φ Gate (Physics/Physiology Violations)

**Monotonic hard-cap**: If **any** claim matches Φ hints, the product is a candidate for Black (FAIL).

Example: `claim_text_verbatim = "Quantum energy field healing"`
→ `phi_hint_ids = ["phi_quantum"]`
→ A-repo applies Φ gate → Black

#### K Gate (Safety/Regulatory)

**Hard block**: If ingredients or claims match K hints (FDA warnings, banned substances), immediate Black.

Example: `ingredients_norm = ["Mitragyna speciosa"]`
→ `k_hint_ids = ["k_kratom"]`
→ A-repo applies K gate → Black

#### L Gate (Exaggeration)

**Soft penalty**: L tokens accumulate a score. High scores limit max tier (e.g., `l_token_score >= 3` → no Gold/Silver).

Example: `claim_text_verbatim = "Miracle cure with 100% instant results"`
→ `l_tokens = ["miracle", "100%", "instant"]`
→ `l_token_score = 3 + 2 + 2 = 7`
→ A-repo applies L penalty → Red or Black

### Multiple Claims Per Product

- **Φ/K**: **Any** claim triggering Φ/K → entire product fails
- **L**: **Max score** across claims determines penalty
- Aggregation fields in `product_info.csv`: `phi_any_candidate`, `k_any_candidate`, `l_max_token_score`

---

## Ethics & Legal Compliance

### What We Do

✅ **Public pages only** (no login/paywall)
✅ **Robots.txt compliance** (respect disallow directives)
✅ **Transparent User-Agent** (research bot identification)
✅ **Throttling** (3s delay between requests)
✅ **Wayback archival** (audit trail)
✅ **SHA256 hashing** (reproducibility)
✅ **Scope limits** (targeted categories/keywords only)

### What We Don't Do

❌ **No aggressive crawling** (no parallel requests, no server load)
❌ **No circumvention** (no proxy rotation, no header spoofing)
❌ **No private data** (no user accounts, no personal info)
❌ **No bulk storage** (images/HTML stored externally, only indices in repo)

### Platform Risk

⚠️ **Technical blocking**: Amazon may block automated access. This pipeline is designed for **research use** with explicit throttling and compliance mechanisms. For production, consider:
- Official Product Advertising API (if access available)
- Manual seeding + targeted discovery (not bulk crawling)
- Coordination with platform (research partnerships)

---

## Integration with TERVYX A-Repo

### What We Provide

1. **Standard CSVs**: `product_info.csv`, `claims.csv`, `assets_index.csv`
2. **Gate hints**: `phi_hint_ids`, `k_hint_ids`, `l_tokens`, `l_token_score`
3. **Reproducibility**: `policy_fingerprint`, `sha256` hashes, `wayback_url`

### What A-Repo Does

1. Load CSVs + policy-as-code rules
2. Apply Φ/K/L gates (using hint IDs as triggers)
3. Compute TEL-5 labels (Gold/Silver/Bronze/Red/Black)
4. Generate `entry.jsonld`, `simulation.json`, `citations.json`

### Export Bundle

```bash
# (TODO: Implement export script)
python integration/export_for_tervyx_A.py \
  --product data/processed/product_info.csv \
  --claims data/processed/claims.csv \
  --out dist/claims_snapshot_v1/
```

---

## Reproducibility

### 5-Minute Repro Card

```bash
# 1. Clone & setup
git clone https://github.com/<org>/tervyx-amazon-claims
cd tervyx-amazon-claims
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Run pipeline (test mode: 10 samples)
make test

# 3. Validate outputs
python scripts/5_qc_validate.py \
  --schemas schemas/ \
  --product data/processed/product_info.csv \
  --claims data/processed/claims.csv \
  --assets data/processed/assets_index.csv
```

Expected output:
- `product_info.csv`: ~10 rows
- `claims.csv`: ~20-40 rows (multiple claims per product)
- All validations pass (temp=0, required fields present, schemas valid)

---

## Limitations & Future Work

### Current Limitations

1. **Access constraints**: No official API access → search-based discovery only
2. **OCR quality**: Image-based claims require manual review (low confidence)
3. **Ingredient parsing**: Raw text extraction → normalization needs refinement
4. **Population weights**: R cohort weights are placeholder (need external benchmarks)

### Roadmap

- [ ] Integrate official Amazon Product Advertising API (if available)
- [ ] Improve OCR pipeline (GROBID-style structured extraction)
- [ ] Add FDA warning list auto-update (scrape FDA website)
- [ ] Implement claim deduplication (cosine similarity clustering)
- [ ] Expand T cohort with known-problematic ASINs (manual seed list)
- [ ] Add multi-language support (non-English claims)

---

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Follow code style (Black, Ruff)
4. Add tests for new functionality
5. Submit a pull request

---

## Citation

If you use this dataset/pipeline in research, please cite:

```bibtex
@software{tervyx_amazon_claims_2025,
  title={TERVYX Amazon Claims: Rule-to-Market Scraping for Health Claim Validation},
  author={TERVYX Protocol Contributors},
  year={2025},
  url={https://github.com/<org>/tervyx-amazon-claims},
  version={v1.0}
}
```

---

## License

- **Code**: Apache 2.0
- **Data**: CC BY 4.0 (claims are factual extractions, properly attributed)

See [LICENSE](LICENSE) for details.

---

## Contact

- **Issues**: [GitHub Issues](https://github.com/<org>/tervyx-amazon-claims/issues)
- **Email**: research@tervyx.org
- **Documentation**: [TERVYX Protocol Docs](https://docs.tervyx.org)

---

## Acknowledgments

This work is part of the **TERVYX Protocol** initiative: building reproducible, policy-driven standards for trustworthy knowledge in the AI era.

Inspired by:
- Evidence-based medicine standards (GRADE, Cochrane)
- Open science practices (OSF, Zenodo)
- Reproducible research principles (RMarkdown, Jupyter)

**"Authority is not truth. Reproducibility is."**
