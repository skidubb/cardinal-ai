import type { ToolDirection } from "@/lib/api";

const STYLES: Record<ToolDirection, string> = {
  input:
    "bg-[rgb(var(--ce-cyan-400))]/15 text-[rgb(var(--ce-cyan-600))] border-[rgb(var(--ce-cyan-400))]/40",
  output:
    "bg-[rgb(var(--ce-purple-500))]/15 text-[rgb(var(--ce-purple-500))] border-[rgb(var(--ce-purple-500))]/40",
  internal: "bg-secondary text-muted-foreground border-border",
};

const LABEL: Record<ToolDirection, string> = {
  input: "IN",
  output: "OUT",
  internal: "INT",
};

export function DirectionPill({ direction }: { direction: ToolDirection }) {
  return (
    <span
      className={`rounded border px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-wider ${STYLES[direction]}`}
      title={direction === "input" ? "Reads/fetches data" : direction === "output" ? "Writes/produces artifacts" : "Internal (validation)"}
    >
      {LABEL[direction]}
    </span>
  );
}
