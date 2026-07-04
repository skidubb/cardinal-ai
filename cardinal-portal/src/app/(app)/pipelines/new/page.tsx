import Link from "next/link";
import { fetchProtocols } from "@/lib/api";
import { PipelineBuilder } from "@/components/pipelines/PipelineBuilder";

export default async function NewPipelinePage() {
  let protocols: Awaited<ReturnType<typeof fetchProtocols>> = [];
  let error: string | null = null;
  try {
    protocols = await fetchProtocols();
  } catch (e: unknown) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="mx-auto max-w-4xl px-8 py-10 space-y-6">
      <header>
        <Link
          href="/pipelines"
          className="text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          &larr; Pipelines
        </Link>
        <span className="ce-eyebrow mt-2 block">Build</span>
        <h1 className="mt-1 text-3xl font-bold tracking-tight">New pipeline</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Chain protocols. Each step receives the previous step&apos;s output as context.
        </p>
      </header>

      {error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <strong>Cannot load protocols.</strong>
          <div className="mt-1 font-mono text-xs text-destructive/70">{error}</div>
        </div>
      ) : (
        <PipelineBuilder protocols={protocols} />
      )}
    </div>
  );
}
