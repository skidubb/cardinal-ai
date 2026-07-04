"use client";

import { useEffect } from "react";
import { useAuth, useOrganization } from "@clerk/nextjs";
import { usePathname } from "next/navigation";

const DEBUG_ENDPOINT = "http://127.0.0.1:7350/ingest/7d90c358-4410-4dad-829c-feec59af07ac";
const DEBUG_SESSION_ID = "a678b6";

function logHydration(message: string, hypothesisId: string, data: Record<string, unknown>) {
  fetch(DEBUG_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Debug-Session-Id": DEBUG_SESSION_ID,
    },
    body: JSON.stringify({
      sessionId: DEBUG_SESSION_ID,
      runId: "pre-fix",
      hypothesisId,
      location: "cardinal-portal/src/components/shell/topbar-hydration-debug.tsx",
      message,
      data,
      timestamp: Date.now(),
    }),
  }).catch(() => {});
}

export function TopbarHydrationDebug() {
  const pathname = usePathname();
  const auth = useAuth();
  const { organization, isLoaded: organizationLoaded } = useOrganization();

  useEffect(() => {
    // #region agent log
    logHydration("topbar clerk client state after hydration", "H1,H2,H3,H4", {
      pathname,
      authLoaded: auth.isLoaded,
      signedIn: auth.isSignedIn,
      orgIdPresent: Boolean(auth.orgId),
      orgSlugPresent: Boolean(auth.orgSlug),
      organizationLoaded,
      organizationPresent: Boolean(organization),
    });
    // #endregion
  }, [
    pathname,
    auth.isLoaded,
    auth.isSignedIn,
    auth.orgId,
    auth.orgSlug,
    organizationLoaded,
    organization,
  ]);

  return null;
}
