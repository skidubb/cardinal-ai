# cardinal-portal

Customer + admin web portal for Cardinal Element.

**Stack:** Next.js 16 (App Router) · React 19 · TypeScript · Tailwind 4 · Clerk (auth + orgs + billing) · deployed to Vercel.

The portal is the **experience layer**. The **engine** lives on Railway (`CE - Multi-Agent Orchestration`). The portal authenticates users with Clerk, then calls Railway with the user's Clerk JWT (claims include `org_slug` → tenant scoping happens server-side on Railway).

## Local dev

```bash
cd cardinal-portal
cp .env.local.example .env.local      # fill in Clerk keys + Railway URL
npm install                            # if you haven't already
npm run dev                            # http://localhost:3000
```

You will need:

1. A Clerk account (free) — https://dashboard.clerk.com
2. A Clerk application (dev environment)
3. Organizations enabled in the Clerk dashboard
4. A JWT template named `ce-railway` that includes:
   ```json
   {
     "org_slug": "{{org.slug}}",
     "org_role": "{{org.role}}",
     "tier": "{{org.public_metadata.tier}}"
   }
   ```
5. Publishable + Secret keys pasted into `.env.local`

## Routes

| Path | Purpose |
|---|---|
| `/` | Landing — sign in / sign up |
| `/sign-in/*` | Clerk hosted sign-in catch-all |
| `/sign-up/*` | Clerk hosted sign-up catch-all |
| `/dashboard` | Customer dashboard (protected) — graph stats |
| `/connectors` | Connector setup (Milestone 2) |
| `/query` | Natural-language query UI (Milestone 3) |
| `/history` | Past queries (Milestone 3) |
| `/billing` | Clerk Billing portal (Milestone 4) |
| `/admin/*` | CE staff console (Milestone 4, role-gated) |

## Auth model

- **User → Organization (Clerk)** = standard Clerk auth
- **Organization → Tenant (CE)** = `org.slug` is the canonical tenant identifier
- All API calls to Railway send the Clerk JWT in `Authorization: Bearer <jwt>`
- Railway's `clerk_auth.py` middleware extracts `org_slug` and uses it to scope every operation against the correct FalkorDB graph + Pinecone namespace

See `/Users/scottewalt/.claude/plans/are-you-currently-relying-imperative-token.md` for the full roadmap.

## Build / deploy

```bash
npm run build   # production build
npm start       # run production build locally
```

Vercel: link the repo, set the root directory to `cardinal-portal`, push to main → auto-deploys. Set the same env vars in Vercel project settings (use prod Clerk keys + prod Railway URL).

## Next.js 16 note

Next.js 16 renamed the `middleware.ts` file convention to `proxy.ts` (the function inside is unchanged — Clerk's `clerkMiddleware` still works as before). See `src/proxy.ts`.
