# Cardinal Element Streamlit Demo

**Status:** Production (Sprint 2 Deliverable 1)
**Deadline:** February 15, 2026
**Deployment Target:** Streamlit Community Cloud (Free Tier)

---

## Overview

This is the first client-facing demo environment for Cardinal Element's AI-powered prospect research and C-Suite advisory platform. The demo showcases:

- **Prospect Research:** SEC EDGAR data enrichment and analysis
- **ICP Fit Scoring:** Evaluation against Cardinal Element's target profile (B2B operators, $5M-$40M ARR, 20-150 employees)
- **C-Suite Advisors:** AI agents (CFO, CTO) responding to questions about prospects

The demo accepts a company ticker or name, fetches public financial data, calculates ICP fit, and displays a working example of how Cardinal Element's agents analyze prospects for strategic fit.

---

## Running Locally

### Prerequisites

- Python 3.11+
- `ANTHROPIC_API_KEY` environment variable set

### Setup

```bash
# Navigate to the demo directory
cd demo

# Create a virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file (or create your own .env)
cp ../.env .env.local

# Add ANTHROPIC_API_KEY to .env.local if not present
echo "ANTHROPIC_API_KEY=sk-..." >> .env.local
```

### Run the Demo

```bash
# From the demo/ directory
streamlit run app.py

# The app will open in your browser at http://localhost:8501
```

---

## Deploying to Streamlit Community Cloud

### Prerequisites

- GitHub account
- Streamlit Community Cloud account (free)

### Deployment Steps

1. **Push code to GitHub:**
   ```bash
   git add demo/
   git commit -m "Add Streamlit demo (Sprint 2 D1)"
   git push origin main
   ```

2. **Connect to Streamlit Cloud:**
   - Visit https://share.streamlit.io
   - Click "New app"
   - Select your GitHub repository
   - Set the main file path to `demo/app.py`
   - Click "Deploy"

3. **Configure Secrets:**
   - In Streamlit Cloud dashboard, go to "Manage secrets"
   - Add `ANTHROPIC_API_KEY` with your key
   - Save

4. **Live Demo URL:**
   - Streamlit provides a shareable URL (e.g., `https://your-username.streamlit.app`)
   - Share this URL with prospects during discovery calls

---

## Architecture

### Single-File Design

The entire demo is `app.py` (one file, ~400 lines). This is intentional:

- **Simplicity:** Easy to review, modify, and deploy
- **Speed:** No complex orchestration or configuration
- **Tech Debt:** Named for paydown in Sprint 3 (replace with Next.js or FastAPI once validated)

### Import Structure

The demo imports from the main `src/csuite/` codebase:

```python
from csuite.agents.cfo import CFOAgent
from csuite.agents.cto import CTOAgent
from csuite.tools.sec_edgar import SECEdgarClient
```

**Do not copy code.** The demo leverages existing agent and API client implementations.

### Data Flow

```
User Input (ticker/name)
    ↓
SEC EDGAR Client (fetch company data)
    ↓
ICP Fit Calculation (score against target profile)
    ↓
Display Company Overview + Financial Metrics
    ↓
User Question → C-Suite Agent (CFO or CTO) → Response
```

### Error Handling

The demo degrades gracefully:

- **Company not found:** Shows clear error message
- **API timeout:** Returns "N/A" for unavailable metrics
- **Agent error:** Shows informative error without crashing

---

## Feature Set

### Core Features (MVP)

- [x] Ticker/name search (supports public companies)
- [x] Company overview (name, ticker, state, industry)
- [x] Financial metrics (revenue, net income, employees)
- [x] ICP fit score (0.0-1.0 with color coding)
- [x] C-Suite agent interaction (CFO, CTO)
- [x] Responsive layout (works on desktop and tablet)

### Known Limitations (Tech Debt)

- No session persistence (doesn't remember previous searches)
- No authentication (demo only, no user accounts)
- No caching (repeat searches hit API each time)
- Single-file architecture (no modular structure)
- Hardcoded styling (all CSS inline)
- Limited agent selection (only CFO and CTO; CEO, CMO, COO, CPO not included)

---

## Testing Before Demo

### Local Testing Checklist

```bash
# 1. Run locally and test with a few tickers
streamlit run app.py

# Test cases:
# - Valid public company (e.g., AAPL, MSFT)
# - Invalid ticker (e.g., XXXXX)
# - Edge case (very small or very large company)
# - Agent query with follow-up questions

# 2. Verify environment setup
echo $ANTHROPIC_API_KEY  # Should show your key

# 3. Check that agents respond without errors
# Test CFO query: "Is this a good prospect for our services?"
# Test CTO query: "What are the tech risks here?"
```

### Streamlit Cloud Testing

After deployment:

1. Visit the live URL
2. Search for a company
3. View the results
4. Ask an agent a question
5. Verify no errors in the Streamlit Cloud logs

---

## Customization

### ICP Fit Scoring (Adjust in `calculate_icp_fit()`)

Current logic scores on:

- Revenue ($5M-$40M ARR): 40% weight
- Industry (B2B signals in SIC): 30% weight
- Employees (estimated from financials): 30% weight

To adjust:

```python
def calculate_icp_fit(company_info, financials):
    # Modify scoring logic here
    # Example: increase revenue weight if ICP is shifting
```

### Agent Selection

To add more agents (CMO, COO, etc.):

1. Import the agent class
2. Add to `agent_choice` selectbox
3. Instantiate in `query_agent()` function

```python
elif agent_choice == "CMO":
    agent_class = CMOAgent
```

### Branding

To customize Cardinal Element branding:

- Edit CSS in the `<style>` block (colors, fonts, spacing)
- Modify header text and descriptions
- Adjust sidebar content

---

## Monitoring

### What to Watch

**Streamlit Cloud Dashboard:**

- CPU/memory usage
- Response times
- Error logs
- API call frequency

**Anthropic Console:**

- Token usage (cost tracking)
- API error rates
- Rate limit hits

**Demo Performance Metrics (Track Manually)**

- Time to fetch company data (target: <3 seconds)
- Time for agent response (target: <10 seconds)
- API error rate (target: <1%)

---

## Support & Troubleshooting

### Common Issues

**Issue:** `ANTHROPIC_API_KEY not found`
**Solution:** Ensure `.env` file exists in demo/ or set env var before running

**Issue:** `Company not found` for a valid company
**Solution:** Try the full company name instead of ticker, or wait 10 seconds (SEC API rate limiting)

**Issue:** Streamlit Cloud deployment fails
**Solution:** Check that all dependencies are in `requirements.txt`, verify Python 3.11+

**Issue:** Agent response is slow or times out
**Solution:** Check internet connection, verify ANTHROPIC_API_KEY is valid, check Anthropic API status

### Viewing Logs

**Local:** Logs appear in terminal where `streamlit run` is executed

**Streamlit Cloud:** View logs in the dashboard under "Manage app" → "Logs"

---

## Sprint 2 Context

**CTO Deliverable 1:** Streamlit Demo App — Public URL Deployment
**Priority:** P1/P3 (enables outbound conversion and discovery call preparation)
**Chairman Action Line:** Scott will use this deliverable to show prospects a live, working AI-powered prospect research brief during discovery calls, starting February 17.

**Hard Deadline:** February 15, 2026
**Unblocks:** COO dry runs (R5), CEO discovery calls (R1), ODSC submission (P0)

---

## Next Steps (Sprint 3)

The following improvements are named as tech debt and scheduled for Sprint 3:

- [ ] Replace with Next.js/FastAPI for better performance and flexibility
- [ ] Add session persistence (remember previous searches)
- [ ] Implement caching layer (repeat searches instant)
- [ ] Add all 6 executives + agent selection UI
- [ ] PDF export for prospect briefs (leave-behind artifact)
- [ ] Integration with CRM/Notion for lead tracking
- [ ] Analytics dashboard (track demo engagement)
- [ ] Authentication (private demo for prospects only)

---

## Questions?

See CTO Sprint 2 Plan or contact Scott Ewalt.
