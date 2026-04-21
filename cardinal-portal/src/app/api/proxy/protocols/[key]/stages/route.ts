// Proxy: GET /api/proxy/protocols/{key}/stages -> Railway GET /api/protocols/{key}/stages.

import { auth } from "@clerk/nextjs/server";
import type { NextRequest } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL ?? "http://localhost:8000";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ key: string }> },
) {
  const { key } = await params;
  const { getToken } = await auth();
  const token = await getToken({ template: "ce-railway" }).catch(() => null);

  const upstream = await fetch(
    `${API_BASE}/api/protocols/${encodeURIComponent(key)}/stages`,
    {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      cache: "no-store",
    },
  );

  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "application/json",
    },
  });
}
