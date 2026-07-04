// Proxy: POST /api/proxy/agents/suggest -> Railway POST /api/agents/suggest.
// Suggests existing agents, net-new specialist specs, and an optional team
// for a given question.

import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

export async function POST(req: NextRequest) {
  const body = await req.text();

  const upstream = await proxyToRailway("/api/agents/suggest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });

  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
