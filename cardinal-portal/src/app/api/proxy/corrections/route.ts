// Proxy: GET list + POST create for /api/corrections
import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

async function forward(req: NextRequest, method: "GET" | "POST") {
  const body = method === "POST" ? await req.text() : undefined;
  const url = new URL(req.url);
  const qs = url.searchParams.toString();
  const upstream = await proxyToRailway(`/api/corrections${qs ? "?" + qs : ""}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body,
  });
  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function GET(req: NextRequest) {
  return forward(req, "GET");
}

export async function POST(req: NextRequest) {
  return forward(req, "POST");
}
