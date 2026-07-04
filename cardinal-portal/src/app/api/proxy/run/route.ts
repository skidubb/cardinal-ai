// SSE proxy: forwards POST /api/proxy/run -> Railway POST /api/protocols/run.
// Attaches the caller's Clerk JWT server-side so we never expose it to the
// browser; pipes the upstream SSE stream straight back to the client unchanged.

import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

export async function POST(req: NextRequest) {
  const body = await req.text();

  return proxyToRailway("/api/protocols/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    // Streaming requests need duplex: half on Node 18+; harmless on others.
    // @ts-expect-error -- duplex is a valid fetch option not in the lib types yet
    duplex: "half",
    sse: true,
  });
}
