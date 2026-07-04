"use client";

import Link from "next/link";
import { useMemo, useState, useTransition } from "react";
import type { Run } from "@/lib/api";
import { deleteRunsAction } from "./actions";

type Props = {
  runs: Run[];
};

export function RunsTable({ runs }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [showConfirm, setShowConfirm] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const allIds = useMemo(() => runs.map((r) => String(r.id)), [runs]);
  const allSelected = selected.size > 0 && selected.size === allIds.length;
  const someSelected = selected.size > 0 && !allSelected;

  function toggleOne(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((prev) => (prev.size === allIds.length ? new Set() : new Set(allIds)));
  }

  function onConfirmDelete() {
    const ids = Array.from(selected);
    setShowConfirm(false);
    startTransition(async () => {
      try {
        const result = await deleteRunsAction(ids);
        setSelected(new Set());
        const msg =
          result.skipped.length > 0
            ? `Deleted ${result.deleted}. ${result.skipped.length} skipped (already gone or out of scope).`
            : `Deleted ${result.deleted} run${result.deleted === 1 ? "" : "s"}.`;
        setFlash(msg);
      } catch (e) {
        setFlash(`Delete failed: ${e instanceof Error ? e.message : String(e)}`);
      }
    });
  }

  const flashTone = flash?.startsWith("Delete failed")
    ? "border-destructive/50 bg-destructive/10 text-destructive"
    : flash?.includes("skipped")
    ? "border-[rgb(var(--ce-yellow-500))]/40 bg-[rgb(var(--ce-yellow-500))]/10 text-foreground"
    : "border-[rgb(var(--ce-green-500))]/40 bg-[rgb(var(--ce-green-500))]/10 text-foreground";

  return (
    <>
      {flash ? (
        <div
          className={`sticky top-0 z-20 flex items-center justify-between gap-3 rounded-lg border px-4 py-2 text-sm ${flashTone}`}
          role="status"
        >
          <span>{flash}</span>
          <button
            type="button"
            onClick={() => setFlash(null)}
            className="text-xs text-muted-foreground transition-colors hover:text-foreground"
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      ) : null}

      {selected.size > 0 ? (
        <div className="sticky top-0 z-10 flex items-center justify-between gap-3 rounded-lg border border-primary/40 bg-primary/5 px-4 py-2 text-sm">
          <span className="font-medium">
            {selected.size} run{selected.size === 1 ? "" : "s"} selected
          </span>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setSelected(new Set())}
              className="text-xs text-muted-foreground transition-colors hover:text-foreground"
              disabled={isPending}
            >
              Clear
            </button>
            <button
              type="button"
              onClick={() => setShowConfirm(true)}
              className="inline-flex items-center gap-2 rounded-md bg-destructive px-3 py-1.5 text-xs font-medium text-destructive-foreground transition-colors hover:opacity-90 disabled:opacity-50"
              disabled={isPending}
            >
              {isPending ? "Deleting…" : "Delete selected"}
            </button>
          </div>
        </div>
      ) : null}

      <div className="rounded-xl border border-border overflow-hidden bg-card">
        <table className="w-full text-sm">
          <thead className="bg-secondary ce-label">
            <tr>
              <th className="w-10 px-4 py-3 text-left">
                <input
                  type="checkbox"
                  aria-label={allSelected ? "Unselect all runs" : "Select all runs"}
                  checked={allSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = someSelected;
                  }}
                  onChange={toggleAll}
                />
              </th>
              <th className="text-left px-4 py-3">Question</th>
              <th className="text-left px-4 py-3">Protocol</th>
              <th className="text-left px-4 py-3">Started</th>
              <th className="text-left px-4 py-3">Cost</th>
              <th className="text-left px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => {
              const id = String(r.id);
              const isChecked = selected.has(id);
              return (
                <tr
                  key={id}
                  className={`border-t border-border transition-colors ${
                    isChecked ? "bg-primary/5" : "hover:bg-secondary"
                  }`}
                >
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      aria-label={`Select run ${id}`}
                      checked={isChecked}
                      onChange={() => toggleOne(id)}
                    />
                  </td>
                  <td className="px-4 py-3 max-w-md">
                    <Link
                      href={`/runs/${id}`}
                      className="hover:text-primary truncate block transition-colors"
                    >
                      {r.question}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-xs font-mono text-muted-foreground">
                    {r.protocol_key}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {r.started_at ? new Date(r.started_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-4 py-3 text-xs tabular-nums text-muted-foreground">
                    {r.cost_usd != null ? `$${r.cost_usd.toFixed(4)}` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <StatusPill status={r.status} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {showConfirm ? (
        <ConfirmDialog
          count={selected.size}
          onCancel={() => setShowConfirm(false)}
          onConfirm={onConfirmDelete}
        />
      ) : null}
    </>
  );
}

function ConfirmDialog({
  count,
  onCancel,
  onConfirm,
}: {
  count: number;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-dialog-title"
    >
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-lg">
        <h2 id="delete-dialog-title" className="text-lg font-semibold">
          Delete {count} run{count === 1 ? "" : "s"}?
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          This removes the run, its agent outputs, and its pipeline steps. This cannot be undone.
        </p>
        <div className="mt-5 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-border px-3 py-1.5 text-sm transition-colors hover:bg-secondary"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-md bg-destructive px-3 py-1.5 text-sm font-medium text-destructive-foreground transition-colors hover:opacity-90"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: Run["status"] }) {
  const styles: Record<Run["status"], string> = {
    running:
      "bg-[rgb(var(--ce-blue-500))]/15 text-[rgb(var(--ce-blue-500))] border-[rgb(var(--ce-blue-500))]/30",
    completed:
      "bg-[rgb(var(--ce-green-500))]/15 text-[rgb(var(--ce-green-500))] border-[rgb(var(--ce-green-500))]/30",
    failed: "bg-destructive/15 text-destructive border-destructive/30",
    cancelled: "bg-secondary text-muted-foreground border-border",
  };
  return (
    <span
      className={`text-[10px] uppercase tracking-wider px-2 py-1 rounded-full border font-medium ${styles[status]}`}
    >
      {status}
    </span>
  );
}
