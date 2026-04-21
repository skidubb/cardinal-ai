import Link from "next/link";
import { Plus, Workflow } from "lucide-react";
import { fetchPipelines } from "@/lib/api";

export default async function PipelinesPage() {
  let pipelines: Awaited<ReturnType<typeof fetchPipelines>> = [];
  let error: string | null = null;
  try {
    pipelines = await fetchPipelines();
  } catch (e: unknown) {
    error = e instanceof Error ? e.message : String(e);
  }

  const presets = pipelines.filter((p) => typeof p.id === "string");
  const saved = pipelines.filter((p) => typeof p.id === "number");

  return (
    <div className="mx-auto max-w-6xl px-8 py-10 space-y-8">
      <header className="flex items-end justify-between">
        <div>
          <span className="ce-eyebrow">Build</span>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">
            Pipelines{" "}
            <span className="text-base font-normal text-muted-foreground">
              ({pipelines.length})
            </span>
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Chain protocols together. Each step&apos;s output feeds the next.
          </p>
        </div>
        <Link
          href="/pipelines/new"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-[var(--shadow-indigo)] transition-colors hover:bg-[rgb(var(--ce-indigo-500))]"
        >
          <Plus size={14} /> New pipeline
        </Link>
      </header>

      {error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <strong>Cannot reach Railway.</strong>
          <div className="mt-1 font-mono text-xs text-destructive/70">{error}</div>
        </div>
      ) : null}

      {saved.length > 0 ? (
        <section className="space-y-3">
          <div className="border-b border-border pb-2">
            <h2 className="text-base font-bold tracking-tight">Your pipelines</h2>
          </div>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {saved.map((p) => (
              <PipelineCard key={p.id} pipeline={p} />
            ))}
          </div>
        </section>
      ) : null}

      {presets.length > 0 ? (
        <section className="space-y-3">
          <div className="border-b border-border pb-2">
            <h2 className="text-base font-bold tracking-tight">Preset pipelines</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Research-backed chains shipped with the platform. Use as-is or fork.
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {presets.map((p) => (
              <PipelineCard key={p.id} pipeline={p} preset />
            ))}
          </div>
        </section>
      ) : null}

      {pipelines.length === 0 && !error ? (
        <div className="rounded-xl border border-border bg-card p-10 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Workflow size={20} />
          </div>
          <p className="mt-4 text-sm text-muted-foreground text-pretty">
            No pipelines yet. Chain protocols together — the first step&apos;s output becomes the
            second step&apos;s context, and so on.
          </p>
          <Link
            href="/pipelines/new"
            className="mt-4 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-[rgb(var(--ce-indigo-500))]"
          >
            <Plus size={14} /> Build your first pipeline
          </Link>
        </div>
      ) : null}
    </div>
  );
}

function PipelineCard({
  pipeline,
  preset,
}: {
  pipeline: Awaited<ReturnType<typeof fetchPipelines>>[number];
  preset?: boolean;
}) {
  return (
    <Link
      href={`/pipelines/${pipeline.id}`}
      className="group block rounded-xl border border-border bg-card p-4 transition-all duration-300 hover:border-primary/50"
    >
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[10px] uppercase tracking-wider text-primary">
          {pipeline.steps.length} STEPS
        </span>
        {preset ? (
          <span className="rounded-full border border-border bg-secondary px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
            preset
          </span>
        ) : null}
      </div>
      <div className="mt-1 font-semibold tracking-tight text-foreground group-hover:text-primary transition-colors">
        {pipeline.name}
      </div>
      {pipeline.description ? (
        <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-muted-foreground text-pretty">
          {pipeline.description}
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-1 font-mono text-[10px] text-muted-foreground">
        {pipeline.steps.slice(0, 4).map((s, i) => (
          <span
            key={s.id ?? i}
            className="rounded bg-secondary px-1.5 py-0.5"
          >
            {s.protocol_key.split("_")[0]}
          </span>
        ))}
        {pipeline.steps.length > 4 ? (
          <span className="text-muted-foreground">+{pipeline.steps.length - 4}</span>
        ) : null}
      </div>
    </Link>
  );
}
