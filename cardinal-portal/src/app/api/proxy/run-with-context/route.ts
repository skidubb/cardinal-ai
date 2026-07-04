// Proxy: POST /api/proxy/run-with-context -> Railway POST /api/protocols/run/with-context.
// Forwards multipart FormData (agent_keys JSON-encoded, question + protocol_key strings, files).

import { auth } from "@clerk/nextjs/server";
import type { NextRequest } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const { getToken } = await auth();
  const token = await getToken({ template: "ce-railway" }).catch(() => null);

  // Pass through the raw body + content-type so FormData boundary is preserved
  const body = await req.blob();
  const contentType = req.headers.get("content-type") ?? "multipart/form-data";

  const upstream = await fetch(`${API_BASE}/api/protocols/run/with-context`, {
    method: "POST",
    headers: {
      "Content-Type": contentType,
      Accept: "text/event-stream",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body,
    // @ts-expect-error duplex is valid
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
