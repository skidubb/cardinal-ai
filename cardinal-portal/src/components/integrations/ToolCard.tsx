"use client";

import { useState } from "react";
import { Settings, Trash2 } from "lucide-react";
import { BrandIcon } from "./BrandIcon";
import { DirectionPill } from "./DirectionPill";
import type { ToolDirection } from "@/lib/api";

export type ToolCardProps = {
  name: string;
  title?: string;
  description: string;
  domain?: string;
  brand?: string;
  direction?: ToolDirection;
  /** Is there a corresponding Integration row (i.e. enable/disable meaningful)? */
  integrationName?: string;
  enabled?: boolean;
  apiKeyConfigured?: boolean;
  deletable?: boolean;
  onToggle?: (next: boolean) => void | Promise<void>;
  onConfigure?: () => void;
  onDelete?: () => void | Promise<void>;
};

export function ToolCard(props: ToolCardProps) {
  const {
    name,
    title,
    description,
    domain,
    brand,
    direction,
    integrationName,
    enabled,
    apiKeyConfigured,
    deletable,
    onToggle,
    onConfigure,
    onDelete,
  } = props;

  const [busy, setBusy] = useState(false);

  async function handleToggle(next: boolean) {
    if (!onToggle || busy) return;
    setBusy(true);
    try {
      await onToggle(next);
    } finally {
      setBusy(false);
    }
  }

  const status = enabled
    ? "enabled"
    : apiKeyConfigured === false && integrationName
      ? "needs-config"
      : "disabled";

  return (
    <div className="relative flex gap-4 rounded-xl border border-border bg-card p-4 transition-all duration-300 hover:border-primary/50">
      <div className="shrink-0">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-secondary">
          <BrandIcon slug={brand} size={24} colored />
        </div>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="truncate font-semibold tracking-tight text-foreground">
                {title ?? name}
              </span>
              {direction ? <DirectionPill direction={direction} /> : null}
            </div>
            {domain ? (
              <div className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                {domain}
              </div>
            ) : null}
          </div>
          <StatusDot status={status} />
        </div>

        <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-muted-foreground text-pretty">
          {description}
        </p>

        {integrationName || onToggle ? (
          <div className="mt-3 flex items-center gap-2">
            {onToggle ? (
              <label className="flex items-center gap-2 text-xs text-muted-foreground">
                <Switch
                  checked={!!enabled}
                  onChange={(n) => handleToggle(n)}
                  disabled={busy}
                />
                {enabled ? "Enabled" : "Disabled"}
              </label>
            ) : null}
            {onConfigure ? (
              <button
                type="button"
                onClick={onConfigure}
                className="ml-auto inline-flex items-center gap-1.5 rounded border border-border px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              >
                <Settings size={11} /> Configure
              </button>
            ) : null}
            {deletable && onDelete ? (
              <button
                type="button"
                onClick={onDelete}
                className="inline-flex items-center gap-1.5 rounded border border-destructive/40 px-2 py-1 text-[10px] text-destructive transition-colors hover:bg-destructive/10"
              >
                <Trash2 size={11} />
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function StatusDot({ status }: { status: "enabled" | "needs-config" | "disabled" }) {
  const styles: Record<typeof status, { bg: string; label: string }> = {
    enabled: { bg: "bg-[rgb(var(--ce-green-500))]", label: "Enabled" },
    "needs-config": { bg: "bg-[rgb(var(--ce-yellow-500))]", label: "Needs config" },
    disabled: { bg: "bg-slate-300 dark:bg-[rgb(var(--ce-slate-700))]", label: "Disabled" },
  };
  const { bg, label } = styles[status];
  return (
    <span
      className="inline-flex shrink-0 items-center gap-1.5 font-mono text-[9px] uppercase tracking-wider text-muted-foreground"
      title={label}
    >
      <span className={`h-2 w-2 rounded-full ${bg}`} />
    </span>
  );
}

function Switch({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={[
        "relative inline-flex h-4 w-7 shrink-0 cursor-pointer rounded-full transition-colors",
        checked ? "bg-primary" : "bg-border",
        disabled ? "opacity-50 cursor-not-allowed" : "",
      ].join(" ")}
    >
      <span
        className={[
          "inline-block h-3 w-3 translate-y-0.5 transform rounded-full bg-white shadow transition-transform",
          checked ? "translate-x-3.5" : "translate-x-0.5",
        ].join(" ")}
      />
    </button>
  );
}
