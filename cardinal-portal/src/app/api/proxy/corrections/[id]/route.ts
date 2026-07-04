// Proxy: DELETE /api/corrections/[id] (retire)
import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

export async function DELETE(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const upstream = await proxyToRailway(`/api/corrections/${id}`, { method: "DELETE" });
  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
