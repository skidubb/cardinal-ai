// Proxy: POST /api/proxy/pipelines/run -> Railway POST /api/pipelines/run.
// SSE stream for multi-step pipeline execution.

import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

export async function POST(req: NextRequest) {
  const body = await req.text();

  return proxyToRailway("/api/pipelines/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    // @ts-expect-error duplex is valid
    duplex: "half",
    sse: true,
  });
}
