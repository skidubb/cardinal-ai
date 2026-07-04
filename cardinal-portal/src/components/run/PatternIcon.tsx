import { ArrowRight, GitBranch, Network, Repeat, Share2, User } from "lucide-react";
import {
  PATTERN_DESC,
  PATTERN_LABEL,
  type OrchestrationPattern,
} from "./orchestrationPattern";

export const PATTERN_GLYPH: Record<OrchestrationPattern, typeof User> = {
  single_agent: User,
  sequence: ArrowRight,
  parallel: Share2,
  hub_and_spoke: Network,
  hybrid_matrix: Repeat,
  decentralized: GitBranch,
};

export function PatternIcon({
  pattern,
  size = 14,
  className = "",
  showLabel = false,
}: {
  pattern: OrchestrationPattern;
  size?: number;
  className?: string;
  showLabel?: boolean;
}) {
  const Glyph = PATTERN_GLYPH[pattern];
  const title = `${PATTERN_LABEL[pattern]} — ${PATTERN_DESC[pattern]}`;
  if (showLabel) {
    return (
      <span
        className={`inline-flex items-center gap-1 rounded border border-border bg-card px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wider text-muted-foreground ${className}`}
        title={title}
      >
        <Glyph size={size - 2} aria-hidden />
        {PATTERN_LABEL[pattern]}
      </span>
    );
  }
  return (
    <span
      className={`inline-flex items-center text-muted-foreground ${className}`}
      title={title}
      aria-label={PATTERN_LABEL[pattern]}
    >
      <Glyph size={size} />
    </span>
  );
}
