// Proxy: POST /api/proxy/discover-questions -> Railway POST /api/discover-questions.
// Forwards multipart FormData (files) and returns the JSON response as-is.

import { auth } from "@clerk/nextjs/server";
import type { NextRequest } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const { getToken } = await auth();
  const token = await getToken({ template: "ce-railway" }).catch(() => null);

  const body = await req.blob();
  const contentType = req.headers.get("content-type") ?? "multipart/form-data";

  const upstream = await fetch(`${API_BASE}/api/discover-questions`, {
    method: "POST",
    headers: {
      "Content-Type": contentType,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body,
    // @ts-expect-error duplex is valid
    duplex: "half",
  });

  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "application/json",
    },
  });
}
