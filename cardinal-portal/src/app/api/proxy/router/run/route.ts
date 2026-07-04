// Proxy: POST /api/proxy/router/run -> Railway POST /api/router/run.
// SSE stream, first event is `router_decision`, then normal protocol events.

import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

export async function POST(req: NextRequest) {
  const body = await req.text();

  return proxyToRailway("/api/router/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    // @ts-expect-error duplex is valid
    duplex: "half",
    sse: true,
  });
}
