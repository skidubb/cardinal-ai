// Proxy: POST /api/proxy/discover-questions -> Railway POST /api/discover-questions.
// Forwards multipart FormData (files) and returns the JSON response as-is.

import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

export async function POST(req: NextRequest) {
  const body = await req.blob();
  const contentType = req.headers.get("content-type") ?? "multipart/form-data";

  const upstream = await proxyToRailway("/api/discover-questions", {
    method: "POST",
    headers: { "Content-Type": contentType },
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
