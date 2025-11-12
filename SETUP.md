# TERVYX Amazon Claims — Setup Guide

## Prerequisites

- Python 3.11+
- Tesseract OCR (for image claim extraction)
- Google Cloud account (for Custom Search API)
- Google AI Studio account (for Gemini API)

---

## 1. Install Dependencies

```bash
# Clone repository
git clone https://github.com/<org>/tervyx-amazon-claims
cd tervyx-amazon-claims

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

---

## 2. Install Tesseract OCR

### macOS
```bash
brew install tesseract
```

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

### Windows
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

---

## 3. Setup Google Custom Search API

### Create Custom Search Engine

1. Go to: https://programmablesearchengine.google.com/
2. Click **"Add"** to create a new search engine
3. Configure:
   - **Sites to search**: `www.amazon.com`
   - **Name**: `Amazon Product Search`
4. After creation, click **"Control Panel"** → **"Setup"**
5. Enable **"Search the entire web"**
6. Copy your **Search Engine ID** (looks like: `a1b2c3d4e5f6g7h8i`)

### Get API Key

1. Go to: https://console.cloud.google.com/apis/credentials
2. Create a new API key (or use existing)
3. Enable **"Custom Search API"** for the project
4. Copy your API key

### Set Environment Variables

```bash
export GOOGLE_SEARCH_API_KEY="your-api-key-here"
export GOOGLE_SEARCH_CX="your-search-engine-id-here"
```

Or create a `.env` file:
```bash
GOOGLE_SEARCH_API_KEY=your-api-key-here
GOOGLE_SEARCH_CX=your-search-engine-id-here
```

**Note**: Google Custom Search API has a free quota of 100 queries/day. For larger datasets, you'll need to upgrade to a paid plan.

---

## 4. Setup Gemini API

### Get API Key

1. Go to: https://aistudio.google.com/app/apikey
2. Click **"Create API Key"**
3. Copy your API key

### Set Environment Variable

```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
```

Or add to `.env`:
```bash
GEMINI_API_KEY=your-gemini-api-key-here
```

**Note**: Gemini 2.0 Flash has a generous free tier. See pricing: https://ai.google.dev/pricing

---

## 5. Verify Installation

```bash
# Check Tesseract
tesseract --version

# Check Python dependencies
python -c "import google.generativeai; print('Gemini SDK OK')"
python -c "import pytesseract; print('PyTesseract OK')"
python -c "from googleapiclient.discovery import build; print('Google API Client OK')"

# Check environment variables
echo $GOOGLE_SEARCH_API_KEY
echo $GOOGLE_SEARCH_CX
echo $GEMINI_API_KEY
```

---

## 6. Quick Test (10 Samples)

```bash
make test
```

This will:
1. Generate 10 product URLs using placeholder mode (no API required)
2. Simulate scraping (no actual HTTP requests)
3. Run extraction pipeline (will use rule-based extraction if APIs not configured)

---

## 7. Production Run (50+ Samples)

Once APIs are configured, run:

```bash
# Generate URLs (uses Google Custom Search API)
python scripts/1_generate_urls.py \
  --plan configs/sampling_plan.yaml \
  --out data/raw/product_urls.csv \
  --sample 50

# Scrape pages (respects robots.txt, throttles requests)
python scripts/2_scrape_pages.py \
  --in data/raw/product_urls.csv \
  --out data/extracted/pages.sha256.csv \
  --assets data/processed/assets_index.csv \
  --html-dir data/raw/html/ \
  --policy configs/scraping_policy.yaml

# Extract claims (uses Gemini API)
python scripts/3_extract_claims.py \
  --pages data/extracted/pages.sha256.csv \
  --assets data/processed/assets_index.csv \
  --html-dir data/raw/html/ \
  --out data/extracted/claims_raw.jsonl \
  --policy configs/extraction_policy.yaml
```

---

## Troubleshooting

### "Google Search API quota exceeded"
- Free tier: 100 queries/day
- Solution: Wait 24 hours or upgrade to paid plan
- Alternative: Use manual seed list (see `data/seeds/`)

### "robots.txt disallows"
- Amazon's robots.txt may restrict automated access
- Solution: Use longer throttle times (5-10s), respect rate limits
- Alternative: Manual product list

### "Tesseract not found"
- Ensure Tesseract is installed and in PATH
- macOS: `which tesseract` should return path
- Windows: Add Tesseract install dir to PATH

### "Gemini API error"
- Check API key is valid: https://aistudio.google.com/app/apikey
- Check quota: https://aistudio.google.com/app/prompts
- Free tier limits: 15 RPM (requests per minute)

---

## Cost Estimates (1000 Products)

### Google Custom Search API
- Free tier: 100 queries/day → 10 days for 1000 products
- Paid tier: $5 per 1000 queries → ~$5 total

### Gemini API (2.0 Flash)
- Free tier: 1500 requests/day
- 1000 products × 2 requests (HTML + images) = 2000 requests → ~2 days
- Paid tier: ~$0.10 per 1M tokens → ~$1-2 total

### Wayback Machine
- Free (no API key required)

**Total cost (paid tier)**: ~$6-7 for 1000 products

---

## Next Steps

1. Review `configs/sampling_plan.yaml` to adjust strata/targets
2. Review `configs/policy_hints.yaml` for Φ/K/L gate patterns
3. Run 50-product prototype: `make test`
4. Scale up to 1000 products: `make all`

For questions, see: [README.md](README.md)
