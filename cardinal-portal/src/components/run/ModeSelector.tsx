"use client";

import { Sparkles, BookOpen, Workflow } from "lucide-react";

export type RunMode = "smart" | "protocol" | "pipeline";

const MODES: Array<{ value: RunMode; label: string; desc: string; icon: React.ComponentType<{ size?: number }> }> = [
  {
    value: "smart",
    label: "Smart route",
    desc: "Let the router pick the protocol",
    icon: Sparkles,
  },
  {
    value: "protocol",
    label: "Pick protocol",
    desc: "Choose one of 53 methodologies",
    icon: BookOpen,
  },
  {
    value: "pipeline",
    label: "Pick pipeline",
    desc: "Run a saved chain of protocols",
    icon: Workflow,
  },
];

export function ModeSelector({
  value,
  onChange,
}: {
  value: RunMode;
  onChange: (m: RunMode) => void;
}) {
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
      {MODES.map((mode) => {
        const Icon = mode.icon;
        const active = value === mode.value;
        return (
          <button
            key={mode.value}
            type="button"
            onClick={() => onChange(mode.value)}
            className={[
              "flex flex-col items-start gap-2 rounded-xl border p-4 text-left transition-all",
              active
                ? "border-primary bg-primary/5 shadow-[var(--shadow-indigo)]"
                : "border-border bg-card hover:border-primary/50",
            ].join(" ")}
          >
            <div
              className={[
                "flex h-8 w-8 items-center justify-center rounded-md",
                active ? "bg-primary text-primary-foreground" : "bg-secondary text-primary",
              ].join(" ")}
            >
              <Icon size={16} />
            </div>
            <div className="font-semibold tracking-tight">{mode.label}</div>
            <div className="text-xs text-muted-foreground">{mode.desc}</div>
          </button>
        );
      })}
    </div>
  );
}
