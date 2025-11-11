# 5-Minute Reproducibility Card

## TERVYX Amazon Claims — Quick Test

This document provides a reproducible test protocol to verify the pipeline in under 5 minutes.

---

## Prerequisites

- Python 3.11+
- Internet access (for simulated scraping)
- 10 MB disk space

---

## Steps

### 1. Clone & Setup

```bash
git clone https://github.com/<org>/tervyx-amazon-claims
cd tervyx-amazon-claims
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Expected time**: 60-90 seconds

---

### 2. Run Test Pipeline (10 samples)

```bash
make test
```

This will:
1. Generate 10 placeholder product URLs
2. Simulate page scraping (no actual network requests)
3. Extract claims (simulated)
4. Normalize to CSV + apply policy hints
5. Validate schemas

**Expected time**: 30-60 seconds

---

### 3. Verify Outputs

```bash
# Check product CSV
wc -l data/processed/product_info.csv
# Expected: 11 lines (1 header + 10 products)

# Check claims CSV
wc -l data/processed/claims.csv
# Expected: ~20-40 lines (multiple claims per product)

# Run QC validation
python scripts/5_qc_validate.py \
  --schemas schemas/ \
  --product data/processed/product_info.csv \
  --claims data/processed/claims.csv \
  --assets data/processed/assets_index.csv
# Expected: "✓ ALL VALIDATIONS PASSED"
```

**Expected time**: 10-20 seconds

---

## Success Criteria

✅ **product_info.csv**: 10 rows, all required fields present
✅ **claims.csv**: 20-40 rows, `extraction_temperature == 0.0`
✅ **assets_index.csv**: Generated (may be empty in test mode)
✅ **QC validation**: All checks pass
✅ **Policy hints**: `phi_hint_ids`, `k_hint_ids`, `l_tokens` populated

---

## Expected Output Sample

### product_info.csv (first row)
```csv
asin,platform,category_path,intervention_type,...,phi_any_candidate,k_any_candidate,l_max_token_score
RHEA00000,amazon,HealthAndHousehold,supplement,...,false,false,0
```

### claims.csv (first row)
```csv
asin,claim_id,claim_text_verbatim,claim_type,...,phi_hint_ids,k_hint_ids,l_tokens,l_token_score
RHEA00000,RHEA00000_c0000,"Clinically proven to improve sleep quality by 87%",efficacy,...,[],["""clinically proven"""],1
```

---

## Notes

- **No actual scraping**: Test mode uses placeholder data
- **No LLM calls**: Extraction is simulated (no API key required)
- **Deterministic**: Running twice should produce identical output
- **Fast**: Total time < 5 minutes on standard laptop

---

## Full Pipeline (Real Data)

For production use with real Amazon pages:

1. Update `configs/sampling_plan.yaml` with target categories
2. Implement actual scraping logic in `scripts/2_scrape_pages.py`
3. Add LLM API credentials for `scripts/3_extract_claims.py`
4. Run: `make all` (no `--sample` limit)

---

## Troubleshooting

**Problem**: Schema validation fails
- **Solution**: Check `extraction_temperature == 0` in claims.csv

**Problem**: Missing CSV files
- **Solution**: Run `make clean && make test` to regenerate

**Problem**: Import errors
- **Solution**: Ensure virtual environment is activated + `pip install -r requirements.txt`

---

## Reproducibility Checklist

- [ ] Git commit hash recorded: `git rev-parse HEAD`
- [ ] Python version: `python --version`
- [ ] Package versions: `pip freeze > requirements.lock`
- [ ] Run timestamp: `date -u`
- [ ] Output hashes match: `sha256sum data/processed/*.csv`

---

**Total Time**: < 5 minutes
**Success Rate**: 100% (deterministic)
