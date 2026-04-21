import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { fetchRuns, type Run } from "@/lib/api";
import { RunsTable } from "./RunsTable";

export default async function RunsPage() {
  const { orgSlug } = await auth();

  let runs: Run[] = [];
  let apiError: string | null = null;
  try {
    runs = await fetchRuns(100);
  } catch (e: unknown) {
    apiError = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="mx-auto max-w-6xl px-8 py-10 space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <span className="ce-eyebrow">History</span>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">All runs</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {orgSlug ? <span className="font-mono">{orgSlug}</span> : "(no org)"}
            <span className="ml-3">· {runs.length} runs</span>
          </p>
        </div>
        <Link
          href="/run"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-[rgb(var(--ce-indigo-500))]"
        >
          + New run
        </Link>
      </header>

      {apiError ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <strong>Railway API unreachable.</strong>
          <div className="text-destructive/70 text-xs mt-1 font-mono">{apiError}</div>
        </div>
      ) : runs.length === 0 ? (
        <div className="rounded-xl border border-border bg-card p-8 text-center">
          <p className="text-muted-foreground">No runs yet for this tenant.</p>
          <Link
            href="/run"
            className="inline-block mt-3 text-primary hover:underline underline-offset-4 text-sm"
          >
            Run your first protocol &rarr;
          </Link>
        </div>
      ) : (
        <RunsTable runs={runs} />
      )}
    </div>
  );
}
