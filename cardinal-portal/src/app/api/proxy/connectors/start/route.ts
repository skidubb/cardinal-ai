// Proxy: browser POST /api/proxy/connectors/start -> Railway /api/connectors/start
// Attaches Clerk JWT server-side.

import { auth } from "@clerk/nextjs/server";
import type { NextRequest } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const { getToken } = await auth();
  const token = await getToken({ template: "ce-railway" }).catch(() => null);

  const body = await req.text();

  const upstream = await fetch(`${API_BASE}/api/connectors/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body,
  });

  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" },
  });
}
