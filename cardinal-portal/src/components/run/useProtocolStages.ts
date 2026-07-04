"use client";

import { useEffect, useState } from "react";
import type { Stage } from "./ProtocolDiagram";

export type StagesPayload = {
  protocol_id: string;
  protocol_name: string;
  stages: Stage[];
  source?: "yaml" | "regex" | "fallback";
};

export function useProtocolStages(protocolKey: string | null | undefined) {
  const [data, setData] = useState<StagesPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!protocolKey) {
      setData(null);
      return;
    }
    const ctrl = new AbortController();
    setError(null);
    (async () => {
      try {
        const resp = await fetch(
          `/api/proxy/protocols/${encodeURIComponent(protocolKey)}/stages`,
          { signal: ctrl.signal },
        );
        if (!resp.ok) throw new Error(`${resp.status}`);
        const payload = (await resp.json()) as StagesPayload;
        setData(payload);
      } catch (e) {
        if ((e as { name?: string })?.name !== "AbortError") {
          setError(e instanceof Error ? e.message : String(e));
        }
      }
    })();
    return () => ctrl.abort();
  }, [protocolKey]);

  return { data, error };
}
