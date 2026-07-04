// Proxy: POST /api/proxy/context-preview -> Railway /api/context/preview
import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

export async function POST(req: NextRequest) {
  const body = await req.text();
  const upstream = await proxyToRailway("/api/context/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
