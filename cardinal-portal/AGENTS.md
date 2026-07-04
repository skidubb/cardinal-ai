<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# cardinal-portal — Agent Guide

Customer + admin web portal. The **experience layer** — auth, orgs, billing, dashboard, query UI. The **engine** is Railway (`CE - Multi-Agent Orchestration`). Portal authenticates with Clerk, then calls Railway with the user's Clerk JWT; `org_slug` on the JWT scopes every backend op to the right tenant.

See the monorepo root [`CLAUDE.md`](../CLAUDE.md) for the full stack context and [`README.md`](./README.md) for setup.

## Stack

- **Next.js 16** (App Router) — **middleware.ts is renamed to `src/proxy.ts`** in Next 16. Clerk's `clerkMiddleware` still works inside it.
- **React 19**, **TypeScript**, **Tailwind 4** (via `@tailwindcss/postcss`), **shadcn/ui** components under `src/components/ui/`.
- **Clerk** (`@clerk/nextjs`) — auth, Organizations (= tenants), Billing. Uses Clerk's default session token (v2) — no custom JWT template. Claims: `o.slg` (org slug), `o.rol` (org role), `pla` (plan), `fea` (features).
- **Vercel** deploy. Root directory: `cardinal-portal`.

## Commands

```bash
npm install
npm run dev        # localhost:3000
npm run build      # production build
npm start          # run built app locally
```

No test, lint, or typecheck scripts are defined in `package.json` — don't invent them.

## Layout

```
cardinal-portal/
├── src/
│   ├── app/
│   │   ├── (app)/                 # Protected routes (require Clerk session + org)
│   │   │   ├── dashboard/         # Graph stats, recent runs
│   │   │   ├── run/               # New run form
│   │   │   ├── runs/              # Run history
│   │   │   ├── protocols/         # Protocol library browser
│   │   │   ├── agents/            # Agent registry + CRUD (portal UI for the 62-agent reg)
│   │   │   ├── pipelines/         # Multi-protocol pipelines
│   │   │   ├── teams/             # Agent team presets
│   │   │   ├── c-suite/           # C-suite-specific views
│   │   │   ├── integrations/      # Connector setup (Notion, Slack, Gmail, ...)
│   │   │   ├── knowledge/         # ce-graph browsing
│   │   │   ├── corrections/       # Corrections-as-data UI
│   │   │   ├── discover/          # Content surfacing
│   │   │   └── layout.tsx         # App shell (sidebar, nav, Clerk org switcher)
│   │   ├── sign-in/[[...sign-in]] # Clerk hosted
│   │   ├── sign-up/[[...sign-up]] # Clerk hosted
│   │   └── api/proxy/             # Server-side proxy to Railway (avoids CORS, strips tokens)
│   ├── components/
│   │   ├── shell/                 # Sidebar, nav-group, org switcher
│   │   ├── run/                   # Protocol run UI (ProtocolDiagram, RunForm)
│   │   ├── agents/, pipelines/, teams/, integrations/, brand/
│   │   └── ui/                    # shadcn primitives
│   ├── lib/
│   │   └── api.ts                 # Typed fetch → Railway FastAPI (Server Components / Actions)
│   └── proxy.ts                   # Next 16 renamed middleware — clerkMiddleware lives here
└── package.json
```

## Auth flow

- **User → Organization (Clerk)** — standard Clerk; portal requires an active org.
- **Organization → Tenant** — `org.slug` is the canonical tenant id. Matches a `ce-graph/tenants/<slug>.yaml` file on the backend.
- **API calls** — Railway accepts Clerk's default session token (v2), so there's no custom JWT template to configure. `src/lib/railway.ts` exports `getRailwayToken()` (`auth().getToken()`, no template arg) as the single source of the bearer token, plus `proxyToRailway()` for browser-facing `/api/proxy/**` routes (handles JSON and SSE passthrough, including 402/403 rejection bodies). `src/lib/api.ts`'s `authedFetch` wrapper uses `getRailwayToken()` under the hood — use it from Server Components and Server Actions rather than rolling your own fetch.
- **Backend verification** — Railway's `api/middleware/clerk_auth.py` validates the session token and reads `o.slg`/`o.rol`/`pla`/`fea` claims for tenant scoping, plan, and feature entitlements.

## Conventions

- **Server Components by default.** Mark client components with `"use client"` only when you need browser APIs, state, or interactivity.
- **Data fetching** — Server Components call `src/lib/api.ts` helpers directly. Server Actions for mutations. Keep tokens out of the browser.
- **shadcn components** live in `src/components/ui/`. Compose, don't fork. Import from `@/components/ui/*`.
- **Tailwind 4** — no `tailwind.config.js` needed; config goes in CSS via `@theme`. Don't add a legacy config file.
- **Routing** — protected pages go under `src/app/(app)/`. Public-auth pages use Clerk's catch-all segments.
- **No emojis in code or copy** (product convention).

## Next.js 16 watch-outs

- `middleware.ts` → **`proxy.ts`** (file rename only; the exported function is still `middleware`/`clerkMiddleware`).
- `cookies()`, `headers()`, `params`, `searchParams` are **async** — `await` them.
- `cache` and `revalidate` semantics changed — read `node_modules/next/dist/docs/` before opinionating.
- If something disagrees with your training data, the docs in `node_modules` are authoritative.
