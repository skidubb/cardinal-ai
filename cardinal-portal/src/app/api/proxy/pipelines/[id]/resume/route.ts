// Proxy: POST /api/proxy/pipelines/[id]/resume -> Railway POST /api/pipelines/resume/{id}. SSE.

import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

export async function POST(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;

  return proxyToRailway(`/api/pipelines/resume/${id}`, {
    method: "POST",
    sse: true,
  });
}
