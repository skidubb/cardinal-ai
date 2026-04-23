// Shared between the Server Component page (for filtering) and the Client
// Component filter (for reading the currently-selected set). Lives in its own
// module so neither side pulls in the other's boundary.
//
// DO NOT add "use client" to this file.

import type { OrchestrationPattern } from "@/components/run/orchestrationPattern";

export const PATTERN_ORDER: OrchestrationPattern[] = [
  "single_agent",
  "sequence",
  "parallel",
  "hub_and_spoke",
  "hybrid_matrix",
  "decentralized",
];

export const PATTERN_PARAM = "patterns";

const VALID = new Set<OrchestrationPattern>(PATTERN_ORDER);

export function patternsFromSearchParams(
  raw: string | string[] | undefined,
): Set<OrchestrationPattern> {
  const value = Array.isArray(raw) ? raw.join(",") : raw ?? "";
  const tokens = value
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean) as OrchestrationPattern[];
  return new Set(tokens.filter((t) => VALID.has(t)));
}
