// Entitlement rejections (402 quota_exceeded / 403 feature_required) arrive as
// structured JSON from the Railway backend. Parse them out of response bodies
// or Error messages so pages can render an upgrade card instead of a raw error.

export type UpgradeDetail = {
  code: string;
  message: string;
  plan?: string;
  used?: number;
  limit?: number;
  feature?: string;
};

export function parseUpgradeDetail(text: string): UpgradeDetail | null {
  // Accept either a raw JSON body or an Error message with the body appended
  // (authedFetch throws `${status} ${statusText} from ${path}: ${body}`).
  const start = text.indexOf("{");
  if (start === -1) return null;
  try {
    const parsed = JSON.parse(text.slice(start)) as { detail?: Record<string, unknown> };
    const detail = parsed.detail;
    if (!detail || (detail.code !== "quota_exceeded" && detail.code !== "feature_required")) {
      return null;
    }
    return {
      code: String(detail.code),
      message: String(detail.message ?? "Upgrade required."),
      plan: typeof detail.plan === "string" ? detail.plan : undefined,
      used: typeof detail.used === "number" ? detail.used : undefined,
      limit: typeof detail.limit === "number" ? detail.limit : undefined,
      feature: typeof detail.feature === "string" ? detail.feature : undefined,
    };
  } catch {
    return null;
  }
}
