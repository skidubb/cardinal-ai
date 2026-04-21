// SSE proxy: forwards POST /api/proxy/run -> Railway POST /api/protocols/run.
// Attaches the caller's Clerk JWT server-side so we never expose it to the
// browser; pipes the upstream SSE stream straight back to the client unchanged.

import { auth } from "@clerk/nextjs/server";
import type { NextRequest } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const { getToken } = await auth();
  const token = await getToken({ template: "ce-railway" }).catch(() => null);

  const body = await req.text();

  const upstream = await fetch(`${API_BASE}/api/protocols/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body,
    // Streaming requests need duplex: half on Node 18+; harmless on others.
    // @ts-expect-error -- duplex is a valid fetch option not in the lib types yet
    duplex: "half",
  });

  if (!upstream.ok || !upstream.body) {
    const errBody = await upstream.text().catch(() => "");
    return new Response(errBody || `Upstream ${upstream.status}`, { status: upstream.status });
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
