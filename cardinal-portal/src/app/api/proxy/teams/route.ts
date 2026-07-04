// Proxy: /api/proxy/teams -> Railway /api/teams. Supports GET + POST.

import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

async function proxy(req: NextRequest, method: string) {
  const body = method === "GET" ? undefined : await req.text();

  const upstream = await proxyToRailway("/api/teams", {
    method,
    headers: { "Content-Type": "application/json" },
    body,
  });

  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function GET(req: NextRequest) {
  return proxy(req, "GET");
}

export async function POST(req: NextRequest) {
  return proxy(req, "POST");
}
