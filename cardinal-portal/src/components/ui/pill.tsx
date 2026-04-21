import * as React from "react";

type Tone = "brand" | "light" | "muted";

const toneClasses: Record<Tone, string> = {
  brand:
    "border border-[rgb(var(--ce-indigo-400)/0.3)] bg-[rgb(var(--ce-indigo-500)/0.2)] text-[rgb(var(--ce-indigo-300))]",
  light:
    "border border-[rgb(var(--ce-indigo-500)/0.3)] bg-[rgb(var(--ce-indigo-500)/0.1)] text-primary",
  muted: "border border-border bg-secondary text-muted-foreground",
};

export interface PillProps extends React.HTMLAttributes<HTMLSpanElement> {
  icon?: React.ReactNode;
  tone?: Tone;
}

export function Pill({ icon, tone = "light", className = "", children, ...rest }: PillProps) {
  return (
    <span
      className={[
        "inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium",
        toneClasses[tone],
        className,
      ].join(" ")}
      {...rest}
    >
      {icon}
      {children}
    </span>
  );
}
