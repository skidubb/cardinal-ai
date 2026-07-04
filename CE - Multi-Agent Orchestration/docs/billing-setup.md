# Billing, Entitlements & Feature Flags — Setup and Operations

Clerk Billing (Stripe under the hood) owns plans, checkout, and subscription
state. The Railway backend enforces entitlements; the portal renders them.
Nothing in this repo talks to Stripe directly.

## Architecture in one paragraph

The portal sends Clerk's **default session token (v2)** to Railway. That token
natively carries the org's plan (`pla: "o:pro"`) and features
(`fea: "o:premium_protocols,o:knowledge_graph"`). `api/middleware/clerk_auth.py`
parses both this format and the legacy `ce-railway` template (fallback:
`tier` 1/2/3 maps to free/pro/enterprise). `api/entitlements.py` maps the plan
slug to limits and enforces them via FastAPI dependencies on every
money-spending endpoint. Session-tied claims (`pla`/`fea`) **cannot** be added
to custom JWT templates — that is why the default session token is used.

## Plans and limits

| Plan | Runs/month | Per-run cost cap | Features |
|------|-----------|------------------|----------|
| free (default / unknown slug) | 5 (`CE_FREE_RUNS_PER_MONTH`) | $0.50 (`CE_FREE_RUN_COST_CAP`) | none |
| pro | 100 (`CE_PRO_RUNS_PER_MONTH`) | $5.00 (`CE_PRO_RUN_COST_CAP`) | all |
| enterprise | unlimited | $25.00 (`CE_ENT_RUN_COST_CAP`) | all |
| internal (X-API-Key / local dev) | unlimited | none | all |

Features: `premium_protocols` (protocols outside `CE_FREE_PROTOCOLS`),
`knowledge_graph` (graph/knowledge/corrections/connectors endpoints),
`custom_protocols_agents` (agent + pipeline create/update/delete).

Free protocol set (override with `CE_FREE_PROTOCOLS`, comma-separated keys):
`p00_direct, p01_single_agent, p03_parallel_synthesis, p07_wicked_questions,
p08_min_specs, p14_one_two_four_all, p15_what_so_what_now_what`.

The quota window is the **UTC calendar month**, not the Stripe billing anchor
(lean v1). Failed runs don't burn quota. `POST /api/discover-questions` checks
quota headroom but does not increment usage (it creates no Run row) — v1
tradeoff. Quota keys use the canonicalized org slug (Clerk numeric suffixes
stripped), matching `Run.tenant_slug`.

## Clerk Dashboard configuration (manual, once per instance)

1. **Billing → Settings → enable Billing.** Dev instances use Clerk's shared
   test Stripe gateway (test card `4242 4242 4242 4242`). Production requires
   connecting the real Stripe account first. Clerk charges 0.7% + Stripe fees.
2. **Billing → Plans → "Plans for Organizations" tab:**
   - Add plan with slug `pro`, monthly price, "Publicly available" ON.
   - Add plan with slug `enterprise`, "Publicly available" ON (or hidden if
     contact-sales only).
   - Free is Clerk's built-in default org plan. Its slug (e.g. `free_org`)
     doesn't matter — the backend treats any unrecognized/missing plan as free.
3. **Billing → Features:** create `premium_protocols`, `knowledge_graph`,
   `custom_protocols_agents`. Attach all three to `pro` AND `enterprise`.
   Attach none to the free plan. Feature slugs must match exactly — they
   travel verbatim in the `fea` claim.
4. **No JWT template changes.** Do not try to add `pla`/`fea` to the
   `ce-railway` template — Clerk forbids session-tied claims in templates.
   Confirm the instance issues v2 session tokens (decode one; expect `"v": 2`,
   `o.slg`, `pla`, `fea`).
5. **Railway env:** existing `CLERK_JWKS_URL` already validates default
   session tokens (same issuer/JWKS). Leave `CLERK_AUDIENCE` unset — default
   session tokens carry `azp`, not `aud`.

## Environment variables (Railway)

| Var | Default | Meaning |
|-----|---------|---------|
| `ENTITLEMENTS_ENFORCE` | `0` | Kill switch. `0` = log-only dry run (`ENTITLEMENTS(dry-run)` warnings), `1` = enforce 402/403 + hard cost caps. |
| `CE_FREE_RUNS_PER_MONTH` | 5 | Free monthly run quota |
| `CE_PRO_RUNS_PER_MONTH` | 100 | Pro monthly run quota |
| `CE_FREE_RUN_COST_CAP` | 0.50 | Free per-run USD hard stop |
| `CE_PRO_RUN_COST_CAP` | 5.00 | Pro per-run USD hard stop |
| `CE_ENT_RUN_COST_CAP` | 25.00 | Enterprise per-run USD hard stop |
| `CE_FREE_PROTOCOLS` | (curated list above) | Comma-separated free protocol keys |

`PROTOCOL_COST_CEILING` (warn-only) still applies to runs without an
entitlement ceiling (CLI, internal callers).

## Error contracts (what the portal renders)

- **Quota:** `402` with
  `{"detail": {"code": "quota_exceeded", "message", "plan", "used", "limit", "upgrade_url": "/billing"}}`
- **Feature:** `403` with
  `{"detail": {"code": "feature_required", "feature", "plan", "message", "upgrade_url": "/billing"}}`
  (premium protocol rejections add `protocol_key`)
- **Mid-run cost cap:** SSE `error` event with
  `{"code": "cost_cap_exceeded", "message", "total_cost_usd", "ceiling_usd", "upgrade_url"}`;
  the run persists as `status=failed` with a JSON `error_message` and its
  actual `cost_usd`.
- `GET /api/usage` returns `plan`, `features`, `period_start/end`,
  `period_runs`, `period_cost_usd`, `runs_limit`, `runs_remaining`,
  `run_cost_cap_usd` alongside the existing all-time fields.

## Rollout order (nothing breaks at any step)

1. Deploy backend with `ENTITLEMENTS_ENFORCE=0`. Legacy `ce-railway` tokens
   keep working (dual-format parsing). Watch logs for `ENTITLEMENTS(dry-run)`
   lines; investigate any false blocks.
2. Configure the Clerk dashboard (dev instance first, then production).
3. Deploy the portal (default session token + `/billing` page). Verify
   `GET /api/auth/me` now returns `plan` and `features`.
4. Flip `ENTITLEMENTS_ENFORCE=1` on Railway with final quota/cap values.
   Rollback = flip it back to `0`.
5. Later cleanup: delete the `ce-railway` JWT template in Clerk and remove the
   legacy claim branches from `clerk_auth.py`.

## Manual E2E checklist (staging: `ENTITLEMENTS_ENFORCE=1`, `CE_FREE_RUNS_PER_MONTH=2`)

1. New org (free): `GET /api/auth/me` shows `plan: null` or `"free"`;
   dashboard meter shows 0 of 2.
2. Run a free protocol twice; the third attempt renders the upgrade card
   ("2 of 2").
3. Attempt a premium protocol or the Knowledge page as free → upgrade card
   (403).
4. `/billing` → PricingTable → subscribe to Pro with the test card. Session
   tokens refresh within ~60s; `pla` becomes `o:pro`; premium protocol runs
   and Knowledge loads.
5. Set `CE_FREE_RUN_COST_CAP=0.01`, run a multi-agent protocol on a free org:
   run stops, Run History shows `failed` with `cost_cap_exceeded`, SSE upsell
   rendered, `cost_usd` recorded.
6. `curl -H "X-API-Key: ..."` run succeeds regardless of quotas (internal
   path, includes the in-repo `ui/` admin console).

## Tests

`tests/test_entitlements.py` covers claim parsing (both token formats), plan
mapping, the month window, the quota query, 402/403 contracts, the dry-run
kill switch, and endpoint-level admission (no Run row created on 402).
`tests/test_cost_ceiling.py` covers the hard-stop cost cap. Run:

```bash
pytest tests/test_entitlements.py tests/test_cost_ceiling.py -q
```
