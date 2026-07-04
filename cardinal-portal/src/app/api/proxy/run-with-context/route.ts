// Proxy: POST /api/proxy/run-with-context -> Railway POST /api/protocols/run/with-context.
// Forwards multipart FormData (agent_keys JSON-encoded, question + protocol_key strings, files).

import type { NextRequest } from "next/server";
import { proxyToRailway } from "@/lib/railway";

export async function POST(req: NextRequest) {
  // Pass through the raw body + content-type so FormData boundary is preserved
  const body = await req.blob();
  const contentType = req.headers.get("content-type") ?? "multipart/form-data";

  return proxyToRailway("/api/protocols/run/with-context", {
    method: "POST",
    headers: { "Content-Type": contentType },
    body,
    // @ts-expect-error duplex is valid
    duplex: "half",
    sse: true,
  });
}
