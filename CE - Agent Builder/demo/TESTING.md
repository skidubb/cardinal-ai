# Demo Testing Checklist

**Purpose:** Verify the Streamlit demo works end-to-end before going live with prospects.

**Before Demo to Prospects:** Complete all checks in this list.

---

## Environment Setup

- [ ] `.env` file exists with `ANTHROPIC_API_KEY`
- [ ] `python --version` shows 3.11+
- [ ] Virtual environment activated (if using one)
- [ ] `pip install -r requirements.txt` completes without errors

---

## Local Testing

### Step 1: Start the App

```bash
cd demo
streamlit run app.py
```

- [ ] App starts without errors
- [ ] Browser opens to http://localhost:8501
- [ ] Page loads (Cardinal Element header visible)

### Step 2: Test Company Search

#### Test Case 1: Valid Company (AAPL)

```
Input: AAPL
Expected: Company overview + financials + ICP score
```

- [ ] Search button responds
- [ ] Loading spinner appears
- [ ] Company info displays (Apple Inc, ticker AAPL, state CA, industry Software)
- [ ] Financial metrics display (Revenue, Net Income, Employees)
- [ ] ICP fit score displays with color coding
- [ ] No errors in terminal or browser

#### Test Case 2: Valid Company (MSFT)

```
Input: MSFT
Expected: Same flow, different company
```

- [ ] Works as expected
- [ ] ICP fit different from AAPL
- [ ] No errors

#### Test Case 3: Invalid Ticker

```
Input: XXXXX
Expected: "Company not found" error message
```

- [ ] Error message displays clearly
- [ ] App doesn't crash
- [ ] Can try another search

#### Test Case 4: Company Name Search

```
Input: "Apple Inc"
Expected: Company found and displayed
```

- [ ] Resolves to AAPL
- [ ] Full data displays
- [ ] No errors

### Step 3: Test Agent Queries

#### CFO Agent Query

```
Company: AAPL
Question: "What are the financial risks for this prospect?"
```

- [ ] Agent selection dropdown works
- [ ] Question input accepts text
- [ ] Loading spinner appears while processing
- [ ] CFO response displays in <10 seconds
- [ ] Response is relevant (mentions revenue, industry, financials)
- [ ] No markdown formatting errors (text readable)

#### CTO Agent Query

```
Company: MSFT
Question: "What is the technical sophistication of this company?"
```

- [ ] Similar to CFO test
- [ ] CTO response is technically relevant
- [ ] No errors

#### Follow-up Query

```
Same company, different question
```

- [ ] Agent remembers previous context (session works)
- [ ] Response is coherent

### Step 4: Test UI/UX

- [ ] Layout is clean and readable (no text overflow)
- [ ] Colors match Cardinal Element branding (navy #0B1E3F, gold #D4AF37)
- [ ] Responsive: works at different browser widths
- [ ] Sidebar displays correctly with example searches
- [ ] Footer/disclaimer visible

### Step 5: Test Error Handling

#### API Timeout

```
Stop internet connection (or wait for API timeout)
```

- [ ] App shows graceful error (not stack trace)
- [ ] Error message is user-friendly
- [ ] Can still interact with app (search again)

#### Agent Error

```
Intentionally corrupt ANTHROPIC_API_KEY and try agent query
```

- [ ] Error message displays
- [ ] App doesn't crash
- [ ] Can fix key and try again

---

## Performance Testing

Time each operation from start to visible result:

### Company Search Time

Target: **<5 seconds** from click to full display

```bash
# Measure with a stopwatch or browser dev tools
1. Click Search
2. When does company info appear?
3. When does agent query section appear?
```

| Company | Time (sec) | Status |
|---------|-----------|--------|
| AAPL    |           | PASS/FAIL |
| MSFT    |           | PASS/FAIL |
| GOOGL   |           | PASS/FAIL |

**Target:** All <5 seconds

### Agent Query Time

Target: **<15 seconds** from click to response visible

```bash
1. Click "Get Recommendation"
2. When does response appear?
```

| Agent | Query | Time (sec) | Status |
|-------|-------|-----------|--------|
| CFO   | "Risks?" |           | PASS/FAIL |
| CTO   | "Tech maturity?" |           | PASS/FAIL |

**Target:** All <15 seconds

---

## Content Verification

### Company Display

- [ ] Company name is correct
- [ ] Ticker matches input (e.g., AAPL shows AAPL, not something else)
- [ ] State shows correct location
- [ ] Industry description is relevant

### Financial Metrics

- [ ] Revenue formatted as currency ($X.XB or $X.XM)
- [ ] Numbers look reasonable (not negative unless net loss)
- [ ] Employee count formatted with commas

### ICP Fit Score

- [ ] Score displays between 0.0 and 1.0
- [ ] Color matches expectation:
  - Green (🟢) if score >= 0.8
  - Orange (🟠) if score 0.6-0.8
  - Red (🔴) if score < 0.6
- [ ] Label matches (EXCELLENT/GOOD/FAIR/POOR FIT)
- [ ] Reasons listed (e.g., "Revenue $X in target range")

### Agent Responses

- [ ] Response is substantive (not generic)
- [ ] Uses company-specific context
- [ ] Is relevant to the question
- [ ] Is formatted as markdown (readable, not raw text)

---

## Accessibility & Compatibility

### Browser Testing

Test in:
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari
- [ ] Edge (if possible)

**Expected:** App works in all modern browsers

### Mobile Testing

- [ ] Test on mobile browser (iPhone Safari or Android Chrome)
- [ ] Layout is readable (text size OK)
- [ ] Search/agent buttons are clickable
- [ ] No horizontal scroll needed

---

## Security Check

- [ ] API key is NOT logged to console or displayed in UI
- [ ] No sensitive data in error messages
- [ ] Cannot inject malicious input via search box
- [ ] Streamlit secrets are configured (for cloud deployment)

---

## Demo Scenario (Full End-to-End)

Simulate a discovery call scenario:

```
1. Open the demo URL
2. Show prospect the header (Cardinal Element branding)
3. Search for a company they know (e.g., a competitor or peer)
4. Discuss the financial metrics displayed
5. Show the ICP fit score and explain it
6. Ask an agent a question about the prospect
7. Show the response (no errors, professional output)
8. Ask follow-up question
9. Show email link at bottom (for future PDF export)
```

- [ ] Demo runs smoothly without interruptions
- [ ] No errors appear during demonstration
- [ ] Response times are acceptable (not slow)
- [ ] Branding looks professional
- [ ] Would impress a prospect

---

## Streamlit Cloud Pre-Check

Before deploying to Streamlit Cloud:

- [ ] All tests above pass locally
- [ ] `requirements.txt` includes all imports (streamlit, anthropic, httpx, pydantic, etc.)
- [ ] No local file paths hardcoded (uses Path relative to project root)
- [ ] `.env` is NOT committed to git (add to `.gitignore`)
- [ ] All code follows Ruff linting (optional for demo, but recommended)

---

## Deployment Verification

After deploying to Streamlit Cloud:

- [ ] App loads at public URL without errors
- [ ] Can search for companies
- [ ] Can query agents
- [ ] API key is configured in Streamlit secrets (test by asking agent a question)
- [ ] Logs show no errors (check Streamlit Cloud logs)

---

## Sign-Off

**Tested by:** [Name]
**Date:** [Date]
**Status:** ✅ PASS / ❌ FAIL

**Issues Found (if any):**

```
[List any issues, with severity and fix status]
```

**Recommendation:**

- [ ] Ready to deploy to production
- [ ] Fix issues first (list above)
- [ ] Defer to next sprint

---

## Notes for Chairman

When Scott reports the demo is "ready," verify with this checklist:

1. Run it locally on your machine (5 min)
2. Search for a company you know
3. Ask a CFO question
4. Confirm output is professional and error-free

That's all the testing needed. The goal is a working demo at a URL, not perfection.

---

*Testing Checklist — CTO Sprint 2 Deliverable 1*
*Use this before going live with prospects.*
