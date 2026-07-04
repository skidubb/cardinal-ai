// Proxy: GET /api/proxy/protocols/{key}/stages -> Railway GET /api/protocols/{key}/stages.

import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ key: string }> },
) {
  const { key } = await params;

  const upstream = await proxyToRailway(`/api/protocols/${encodeURIComponent(key)}/stages`);

  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "application/json",
    },
  });
}
