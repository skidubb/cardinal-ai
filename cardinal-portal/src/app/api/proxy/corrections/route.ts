// Proxy: GET list + POST create for /api/corrections
import { auth } from "@clerk/nextjs/server";
import type { NextRequest } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL ?? "http://localhost:8000";

async function forward(req: NextRequest, method: "GET" | "POST") {
  const { getToken } = await auth();
  const token = await getToken({ template: "ce-railway" }).catch(() => null);
  const body = method === "POST" ? await req.text() : undefined;
  const url = new URL(req.url);
  const qs = url.searchParams.toString();
  const upstream = await fetch(`${API_BASE}/api/corrections${qs ? "?" + qs : ""}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
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
