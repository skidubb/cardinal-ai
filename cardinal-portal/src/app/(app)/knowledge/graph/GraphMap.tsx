"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import type { ComponentType } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { GraphEdge, GraphNode } from "@/lib/api";

type ForceGraphProps = {
  graphData: { nodes: ForceNode[]; links: ForceLink[] };
  width: number;
  height: number;
  backgroundColor?: string;
  nodeRelSize?: number;
  nodeLabel?: (node: ForceNode) => string;
  nodeVal?: (node: ForceNode) => number;
  nodeColor?: (node: ForceNode) => string;
  linkColor?: (link: ForceLink) => string;
  linkDirectionalArrowLength?: number;
  linkDirectionalArrowRelPos?: number;
  linkWidth?: number;
  cooldownTicks?: number;
  onNodeClick?: (node: ForceNode) => void;
};

// react-force-graph-2d touches canvas + window APIs, so we can't render it
// server-side. Load it client-only via next/dynamic. The dynamic import
// erases the component's prop types, so we re-attach them via a cast.
const ForceGraph2D = dynamic(
  () => import("react-force-graph-2d") as Promise<{ default: ComponentType<ForceGraphProps> }>,
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[640px] items-center justify-center rounded-xl border border-border bg-card text-xs text-muted-foreground">
        Loading graph engine…
      </div>
    ),
  },
) as ComponentType<ForceGraphProps>;

type ForceNode = GraphNode & {
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number;
  fy?: number;
  // The lib resolves edge endpoints in place. Allow the source/target on
  // edges to be either the raw id or the populated node object.
};

type ForceLink = {
  source: number | ForceNode;
  target: number | ForceNode;
  type: string;
};

const LABEL_PALETTE: Record<string, string> = {
  Client: "#6366f1",
  Engagement: "#8b5cf6",
  Protocol: "#0ea5e9",
  Decision: "#f59e0b",
  Lesson: "#10b981",
  Correction: "#ef4444",
  Person: "#ec4899",
  Agent: "#14b8a6",
  Source: "#64748b",
  Vertical: "#a855f7",
  Deliverable: "#22c55e",
  Node: "#94a3b8",
};

function colorFor(label: string): string {
  return LABEL_PALETTE[label] ?? LABEL_PALETTE.Node;
}

export function GraphMap({
  nodes,
  edges,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState<number>(960);
  const [search, setSearch] = useState("");
  const [activeLabels, setActiveLabels] = useState<Set<string>>(() => {
    const s = new Set<string>();
    for (const n of nodes) s.add(n.label);
    return s;
  });
  const [selected, setSelected] = useState<GraphNode | null>(null);

  // Resize observer — keep the canvas matching its container width.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setWidth(Math.max(360, Math.floor(entry.contentRect.width)));
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const allLabels = useMemo(() => {
    const counts = new Map<string, number>();
    for (const n of nodes) counts.set(n.label, (counts.get(n.label) ?? 0) + 1);
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([label, count]) => ({ label, count }));
  }, [nodes]);

  const visibleNodes = useMemo(() => {
    const q = search.trim().toLowerCase();
    return nodes.filter((n) => {
      if (!activeLabels.has(n.label)) return false;
      if (!q) return true;
      return (
        n.name.toLowerCase().includes(q) ||
        Object.values(n.props ?? {}).some(
          (v) => typeof v === "string" && v.toLowerCase().includes(q),
        )
      );
    });
  }, [nodes, activeLabels, search]);

  const visibleNodeIds = useMemo(() => {
    const set = new Set<number>();
    for (const n of visibleNodes) set.add(n.id);
    return set;
  }, [visibleNodes]);

  const visibleEdges = useMemo(
    () =>
      edges.filter(
        (e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target),
      ),
    [edges, visibleNodeIds],
  );

  // The lib mutates the data it receives (adds x/y/vx/vy/fx/fy and replaces
  // edge endpoints with node objects). Rebuild fresh objects each render so
  // we don't fight that mutation.
  const graphData = useMemo(
    () => ({
      nodes: visibleNodes.map((n) => ({ ...n })) as ForceNode[],
      links: visibleEdges.map((e) => ({ ...e })) as ForceLink[],
    }),
    [visibleNodes, visibleEdges],
  );

  function toggleLabel(label: string) {
    setActiveLabels((curr) => {
      const next = new Set(curr);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  }

  return (
    <div className="grid gap-4 md:grid-cols-[1fr_280px]">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter nodes by name or property…"
            className="w-72 rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
          />
          <span className="text-[11px] text-muted-foreground">
            {visibleNodes.length} of {nodes.length} nodes shown ·{" "}
            {visibleEdges.length} edges
          </span>
        </div>

        <div className="flex flex-wrap gap-1">
          {allLabels.map(({ label, count }) => {
            const active = activeLabels.has(label);
            return (
              <button
                key={label}
                type="button"
                onClick={() => toggleLabel(label)}
                className={`flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] transition-colors ${
                  active
                    ? "border-primary/40 bg-primary/10 text-foreground"
                    : "border-border bg-background text-muted-foreground hover:border-primary/50"
                }`}
              >
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{ backgroundColor: colorFor(label) }}
                />
                {label}
                <span className="text-muted-foreground">·{count}</span>
              </button>
            );
          })}
        </div>

        <div
          ref={containerRef}
          className="relative h-[640px] w-full overflow-hidden rounded-xl border border-border bg-card"
        >
          {visibleNodes.length === 0 ? (
            <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
              No nodes match the current filters.
            </div>
          ) : (
            <ForceGraph2D
              graphData={graphData}
              width={width}
              height={640}
              backgroundColor="rgba(0,0,0,0)"
              nodeRelSize={4}
              nodeLabel={(node: ForceNode) =>
                `${node.label}: ${node.name} (degree ${node.degree})`
              }
              nodeVal={(node: ForceNode) => 1 + Math.sqrt(node.degree)}
              nodeColor={(node: ForceNode) => colorFor(node.label)}
              linkColor={() => "rgba(148,163,184,0.4)"}
              linkDirectionalArrowLength={3}
              linkDirectionalArrowRelPos={1}
              linkWidth={0.5}
              cooldownTicks={120}
              onNodeClick={(node: ForceNode) => setSelected(node)}
            />
          )}
        </div>
      </div>

      <SidePanel selected={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

function SidePanel({
  selected,
  onClose,
}: {
  selected: GraphNode | null;
  onClose: () => void;
}) {
  if (!selected) {
    return (
      <aside className="rounded-xl border border-border bg-card p-4 text-xs text-muted-foreground">
        <div className="ce-label mb-2">Inspector</div>
        <p className="leading-relaxed">
          Click a node to inspect its properties and connections. Use the legend
          chips to hide node types you don&apos;t care about.
        </p>
        <p className="mt-2 leading-relaxed">
          Drag nodes to reposition. Scroll to zoom.
        </p>
      </aside>
    );
  }

  const propEntries = Object.entries(selected.props ?? {}).filter(
    ([, v]) => v != null && v !== "",
  );

  // Heuristic: if this is a Decision tied to a run, surface a deep link.
  const sourceId =
    typeof selected.props?.source_id === "string"
      ? (selected.props.source_id as string)
      : null;

  return (
    <aside className="space-y-3 rounded-xl border border-border bg-card p-4 text-xs">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="ce-label">{selected.label}</div>
          <div className="mt-0.5 break-words text-sm font-medium text-foreground">
            {selected.name}
          </div>
          <div className="mt-0.5 text-[10px] tabular-nums text-muted-foreground">
            id {selected.id} · degree {selected.degree}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground transition-colors hover:bg-secondary"
        >
          Close
        </button>
      </div>

      {propEntries.length > 0 ? (
        <div className="space-y-1.5">
          <div className="ce-label text-[10px]">Properties</div>
          <dl className="space-y-1">
            {propEntries.map(([k, v]) => (
              <div key={k} className="grid grid-cols-[88px_1fr] gap-2">
                <dt className="font-mono text-[10px] text-muted-foreground">{k}</dt>
                <dd className="break-words font-mono text-[10px] text-foreground">
                  {typeof v === "string" ? v : JSON.stringify(v)}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      ) : (
        <p className="italic text-muted-foreground">No additional properties.</p>
      )}

      {selected.label === "Decision" && sourceId ? (
        <div>
          <Link
            href={`/runs/${encodeURIComponent(sourceId)}`}
            className="inline-flex items-center gap-1 text-[11px] text-primary underline-offset-4 hover:underline"
          >
            Open source run #{sourceId} →
          </Link>
        </div>
      ) : null}
    </aside>
  );
}
