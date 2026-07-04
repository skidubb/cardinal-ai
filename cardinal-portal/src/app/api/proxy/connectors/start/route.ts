// Proxy: browser POST /api/proxy/connectors/start -> Railway /api/connectors/start
// Attaches Clerk JWT server-side.

import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

export async function POST(req: NextRequest) {
  const body = await req.text();

  const upstream = await proxyToRailway("/api/connectors/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });

  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" },
  });
}
