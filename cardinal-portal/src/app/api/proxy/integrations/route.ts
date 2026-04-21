// Proxy: /api/proxy/integrations -> Railway /api/integrations. GET + POST.

import { auth } from "@clerk/nextjs/server";
import type { NextRequest } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL ?? "http://localhost:8000";

async function proxy(req: NextRequest, method: string) {
  const { getToken } = await auth();
  const token = await getToken({ template: "ce-railway" }).catch(() => null);
  const body = method === "GET" ? undefined : await req.text();

  const upstream = await fetch(`${API_BASE}/api/integrations`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
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
