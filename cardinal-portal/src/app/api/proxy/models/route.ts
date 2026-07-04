// Proxy: GET /api/proxy/models -> Railway GET /api/models. Model catalog.

import { proxyToRailway } from "@/lib/railway";

export async function GET() {
  const upstream = await proxyToRailway("/api/models", { method: "GET" });

  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
