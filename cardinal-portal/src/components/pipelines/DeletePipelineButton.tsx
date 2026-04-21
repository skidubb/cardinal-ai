"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Trash2 } from "lucide-react";

export function DeletePipelineButton({ id }: { id: string | number }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function remove() {
    if (!confirm("Delete this pipeline? This cannot be undone.")) return;
    setBusy(true);
    try {
      const resp = await fetch(`/api/proxy/pipelines/${id}`, { method: "DELETE" });
      if (resp.status !== 204 && !resp.ok) {
        const text = await resp.text().catch(() => "");
        alert(`Delete failed: ${resp.status} ${text.slice(0, 200)}`);
        return;
      }
      router.push("/pipelines");
    } catch (e: unknown) {
      alert(`Delete failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      onClick={remove}
      disabled={busy}
      className="inline-flex items-center gap-2 rounded-md border border-destructive/40 px-3 py-1.5 text-xs font-medium text-destructive transition-colors hover:bg-destructive/10 disabled:opacity-50"
    >
      <Trash2 size={12} />
      {busy ? "Deleting…" : "Delete"}
    </button>
  );
}
