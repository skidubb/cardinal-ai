// Proxy: POST /api/proxy/router/run-with-context -> Railway POST /api/router/run/with-context.
// Smart-route + uploaded context. Forwards multipart FormData with question + optional agents JSON + files.

import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

export async function POST(req: NextRequest) {
  const body = await req.blob();
  const contentType = req.headers.get("content-type") ?? "multipart/form-data";

  return proxyToRailway("/api/router/run/with-context", {
    method: "POST",
    headers: { "Content-Type": contentType },
    body,
    // @ts-expect-error duplex is valid
    duplex: "half",
    sse: true,
  });
}
