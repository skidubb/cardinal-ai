import * as React from "react";
import type { LucideIcon } from "lucide-react";

export interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  body: string;
}

export function FeatureCard({ icon: Icon, title, body }: FeatureCardProps) {
  return (
    <div className="group flex items-start gap-4 rounded-xl border border-border bg-card p-6 transition-all duration-300 hover:border-primary/50">
      <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg bg-secondary text-primary transition-colors group-hover:bg-primary/10">
        <Icon size={22} strokeWidth={2} />
      </div>
      <div>
        <h4 className="mb-1.5 text-lg font-semibold leading-snug text-foreground">{title}</h4>
        <p className="text-sm leading-relaxed text-muted-foreground text-pretty">{body}</p>
      </div>
    </div>
  );
}
