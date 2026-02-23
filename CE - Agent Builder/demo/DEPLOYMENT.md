# Streamlit Cloud Deployment Guide

**For Chairman:** Complete deployment to Streamlit Community Cloud (free tier) by **February 15, 2026**.

---

## 5-Minute Deployment

### Step 1: Push Code to GitHub (2 min)

```bash
# From project root
git add demo/
git commit -m "Add Streamlit demo (CTO Sprint 2 D1)"
git push origin main
```

### Step 2: Connect to Streamlit Cloud (3 min)

1. Go to https://share.streamlit.io
2. Click "New app"
3. Select your GitHub repository
4. Set main file path to: `demo/app.py`
5. Click "Deploy"

Streamlit will build and deploy. This takes 1-2 minutes. You'll see a live URL when done.

### Step 3: Add API Key (1 min)

1. In Streamlit Cloud dashboard, click your app
2. Click "Manage secrets" (gear icon, top right)
3. Paste your `ANTHROPIC_API_KEY` in the text area:
   ```
   ANTHROPIC_API_KEY = "sk-your-key-here"
   ```
4. Click "Save"

The app will reboot with the secret. Done.

---

## Verification Checklist

After deployment, verify the demo works:

- [ ] Visit the live URL (shown in Streamlit Cloud)
- [ ] Search for a company (e.g., `AAPL`)
- [ ] See company overview and financial metrics
- [ ] Get ICP fit score
- [ ] Ask a CFO question and get a response
- [ ] No error messages in the app

---

## Live Demo URL Format

Your URL will look like:
```
https://ce-demo-xyz.streamlit.app
```

Share this with prospects during discovery calls.

---

## Troubleshooting Deployment

### Issue: "requirements.txt not found"

**Solution:** Verify demo/requirements.txt exists in repo and commit it

```bash
git status  # Should show demo/requirements.txt
```

### Issue: "ModuleNotFoundError: No module named 'csuite'"

**Solution:** The app needs to import from src/. This is handled in app.py with:

```python
sys.path.insert(0, str(project_root / "src"))
```

If this fails, ensure the project structure is:
```
project-root/
├── demo/
│   └── app.py
├── src/
│   └── csuite/
│       ├── agents/
│       ├── tools/
│       └── ...
```

### Issue: "ANTHROPIC_API_KEY not found" during run

**Solution:** Verify secret is in Streamlit Cloud dashboard

1. Click your app name
2. Click "Manage secrets"
3. Paste the key again and save
4. Wait 10 seconds for reboot

### Issue: App loads but getting "Company not found"

**Solution:** This is normal for invalid tickers. Test with `AAPL`, `MSFT`, or `GOOGL`.

---

## Updating the Demo After Deployment

To push updates:

1. Make changes to demo/app.py
2. Commit and push to GitHub:
   ```bash
   git commit -am "Update demo feature"
   git push
   ```
3. Streamlit Cloud automatically redeploys from main branch

No manual redeployment needed.

---

## Cost & Limits

**Streamlit Community Cloud (Free):**
- 1 GB RAM
- Shared CPU
- No custom domain
- 1 app per GitHub account (upgrade for more)

**Anthropic API:**
- Pay-as-you-go by token usage
- Each demo query costs ~$0.01-$0.10 depending on company size and response length
- Budget alert available in Anthropic console

---

## Performance Expectations

**Normal response times:**
- Company search: 2-5 seconds
- Agent response: 5-15 seconds
- Full demo flow: 20-30 seconds

**If slower:**
- Check internet connection
- Verify ANTHROPIC_API_KEY is valid
- Check Streamlit Cloud logs (Manage app → Logs)

---

## Monitoring After Deploy

### Streamlit Cloud Logs

Access logs to debug issues:

1. Click your app in Streamlit Cloud
2. Click "Manage app" (settings icon)
3. Click "Logs"

### Anthropic API Usage

Track costs:

1. Go to https://console.anthropic.com
2. Click "Usage" → "API Usage"
3. View tokens consumed per day

---

## Rollback (If Needed)

If deployed version has a critical bug:

```bash
# Revert to previous commit
git revert HEAD
git push origin main

# Streamlit automatically redeploys from main branch
# Takes 1-2 minutes
```

---

## Support

**Issues with Streamlit deployment?**
- Streamlit Docs: https://docs.streamlit.io
- Streamlit Community: https://discuss.streamlit.io

**Issues with Anthropic API?**
- API Docs: https://docs.anthropic.com
- Support: https://support.anthropic.com

---

## Next Checkpoint

Once live, monitor for 48 hours:

- Are there API errors?
- Are response times acceptable?
- Is the ICP scoring reasonable?

Document any issues for Sprint 2 review.

---

*Deployment Guide — CTO Sprint 2 Deliverable 1*
*Target Date: February 15, 2026*
