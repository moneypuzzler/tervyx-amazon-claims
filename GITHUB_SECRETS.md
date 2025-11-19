# GitHub Secrets & Variables 설정 가이드

## 🔐 Required Secrets (필수 시크릿)

실제 데이터 수집을 위해 다음 3개 Secrets를 설정해야 합니다:

### 설정 방법

1. GitHub 레포 → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** 클릭
3. 아래 3개 추가:

---

### 1. `GOOGLE_SEARCH_API_KEY`

**용도**: Amazon 제품 URL 발견 (Google Custom Search API)

**발급 방법**:
1. https://console.cloud.google.com/apis/credentials 접속
2. **Create Credentials** → **API Key** 선택
3. API Key 복사
4. **APIs & Services** → **Library** → "Custom Search API" 검색 → Enable

**무료 할당량**: 100 queries/day (유료: $5 per 1000 queries)

```
Name: GOOGLE_SEARCH_API_KEY
Value: AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

---

### 2. `GOOGLE_SEARCH_CX`

**용도**: Custom Search Engine ID

**발급 방법**:
1. https://programmablesearchengine.google.com/ 접속
2. **Add** 클릭
3. **Sites to search**: `www.amazon.com` 입력
4. **Create** 후 **Control Panel** → **Setup**
5. **Search the entire web** 활성화
6. **Search engine ID** 복사 (형식: `a1b2c3d4e5f6g7h8i`)

```
Name: GOOGLE_SEARCH_CX
Value: a1b2c3d4e5f6g7h8i9j0k1l2m
```

---

### 3. `GEMINI_API_KEY`

**용도**: 주장 추출 (Gemini 2.0 Flash, temp=0)

**발급 방법**:
1. https://aistudio.google.com/app/apikey 접속
2. **Create API Key** 클릭
3. API Key 복사

**무료 할당량**: 1500 requests/day (유료: ~$0.10 per 1M tokens)

```
Name: GEMINI_API_KEY
Value: AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

---

## 🚀 사용 방법

### 방법 1: GitHub Actions (자동 실행)

**Manual Workflow 실행**:
1. GitHub 레포 → **Actions** 탭
2. **Data Collection (Real Scraping)** 워크플로우 선택
3. **Run workflow** 클릭
4. Sample size 선택 (10/50/100/1000)
5. **Run workflow** 버튼 클릭

**결과**:
- 자동으로 전체 파이프라인 실행
- Artifacts에서 CSV 다운로드

---

### 방법 2: 로컬 실행

**Secrets를 환경 변수로 내보내기**:

```bash
# GitHub CLI 사용 (추천)
gh secret list
export GOOGLE_SEARCH_API_KEY=$(gh secret get GOOGLE_SEARCH_API_KEY)
export GOOGLE_SEARCH_CX=$(gh secret get GOOGLE_SEARCH_CX)
export GEMINI_API_KEY=$(gh secret get GEMINI_API_KEY)

# 또는 수동 입력
export GOOGLE_SEARCH_API_KEY="your-key"
export GOOGLE_SEARCH_CX="your-cx"
export GEMINI_API_KEY="your-key"

# 파이프라인 실행
make all
```

---

## ✅ Secrets 검증

**API 키 작동 확인**:

```bash
# Google Custom Search
curl -s "https://www.googleapis.com/customsearch/v1?key=$GOOGLE_SEARCH_API_KEY&cx=$GOOGLE_SEARCH_CX&q=test" | jq .

# Gemini
python -c "
import os
import google.generativeai as genai
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash-exp')
print(model.generate_content('test').text)
"
```

---

## 🔒 보안 주의사항

### ✅ DO (해야 할 것)
- GitHub Secrets에만 저장 (암호화됨)
- API 키는 절대 코드에 하드코딩 금지
- `.env` 파일은 `.gitignore`에 포함 확인
- 주기적으로 API 키 재생성

### ❌ DON'T (하지 말아야 할 것)
- 공개 레포에 API 키 커밋 금지
- Issue/PR 코멘트에 키 노출 금지
- 로그에 키 출력 금지

---

## 💰 비용 예상

### 100개 제품 수집
| API | 무료 티어 | 유료 비용 |
|-----|----------|----------|
| Google Custom Search | 100 queries/day | ~$0.50 |
| Gemini 2.0 Flash | 1500 req/day | ~$0.20 |
| Tesseract OCR | 무제한 | $0 |
| **합계** | **무료** | **~$0.70** |

### 1000개 제품 수집
| API | 무료 티어 | 유료 비용 |
|-----|----------|----------|
| Google Custom Search | 10일 소요 | ~$5 |
| Gemini 2.0 Flash | 1-2일 소요 | ~$1-2 |
| **합계** | **12일 무료** | **~$6-7** |

---

## 🆘 Troubleshooting

### "API key not valid"
→ API가 활성화되었는지 확인 (Google Cloud Console → APIs & Services)

### "Quota exceeded"
→ 무료 티어 한도 초과. 다음날 다시 시도하거나 유료 플랜 활성화

### "Secrets not found"
→ Repository settings에서 Secrets가 정확히 입력되었는지 확인

---

## 📚 관련 문서

- **로컬 개발**: [SETUP.md](SETUP.md)
- **전체 구현**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **메인 가이드**: [README.md](README.md)
