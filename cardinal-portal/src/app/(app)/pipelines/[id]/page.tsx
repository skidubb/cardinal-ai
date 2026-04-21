import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { fetchPipeline } from "@/lib/api";
import { DeletePipelineButton } from "@/components/pipelines/DeletePipelineButton";

export default async function PipelineDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let pipeline: Awaited<ReturnType<typeof fetchPipeline>> | null = null;
  let error: string | null = null;
  try {
    pipeline = await fetchPipeline(id);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.includes("404")) notFound();
    error = msg;
  }

  if (!pipeline && !error) notFound();

  const isPreset = typeof pipeline?.id === "string";

  return (
    <div className="mx-auto max-w-4xl px-8 py-10 space-y-6">
      <header>
        <Link
          href="/pipelines"
          className="text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          &larr; Pipelines
        </Link>
        <div className="mt-2 flex items-center gap-3">
          <span className="ce-eyebrow">Build</span>
          {isPreset ? (
            <span className="rounded-full border border-border bg-secondary px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              preset
            </span>
          ) : null}
        </div>
        <div className="mt-2 flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{pipeline?.name}</h1>
            {pipeline?.description ? (
              <p className="mt-1 max-w-2xl text-sm text-muted-foreground text-pretty">
                {pipeline.description}
              </p>
            ) : null}
          </div>
          <div className="flex items-center gap-2">
            <Link
              href={`/run?pipeline=${pipeline?.id}`}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-[var(--shadow-indigo)] transition-colors hover:bg-[rgb(var(--ce-indigo-500))]"
            >
              Run
              <ArrowRight size={14} />
            </Link>
            {!isPreset && pipeline ? <DeletePipelineButton id={pipeline.id} /> : null}
          </div>
        </div>
      </header>

      {error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <strong>Cannot load pipeline.</strong>
          <div className="mt-1 font-mono text-xs text-destructive/70">{error}</div>
        </div>
      ) : null}

      {pipeline ? (
        <section className="space-y-3">
          <div className="border-b border-border pb-2">
            <h2 className="text-base font-bold tracking-tight">
              Steps{" "}
              <span className="text-sm font-normal text-muted-foreground">
                ({pipeline.steps.length})
              </span>
            </h2>
          </div>

          <ol className="space-y-3">
            {pipeline.steps.map((step, i) => (
              <li
                key={step.id ?? i}
                className="rounded-xl border border-border bg-card p-5"
              >
                <div className="mb-3 flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                    {i + 1}
                  </span>
                  <span className="font-mono text-sm text-primary">{step.protocol_key}</span>
                  {step.rounds ? (
                    <span className="font-mono text-xs text-muted-foreground">
                      · {step.rounds} rounds
                    </span>
                  ) : null}
                  <div className="ml-auto flex gap-2">
                    {step.output_passthrough ? (
                      <span className="rounded-full border border-[rgb(var(--ce-cyan-400))]/30 bg-[rgb(var(--ce-cyan-400))]/10 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-[rgb(var(--ce-cyan-600))]">
                        passes output
                      </span>
                    ) : null}
                    {step.no_tools ? (
                      <span className="rounded-full border border-border bg-secondary px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
                        no tools
                      </span>
                    ) : null}
                  </div>
                </div>
                {step.question_template ? (
                  <pre className="whitespace-pre-wrap rounded-md border border-border bg-background p-3 font-mono text-xs leading-relaxed text-foreground">
                    {step.question_template}
                  </pre>
                ) : (
                  <p className="text-xs italic text-muted-foreground">
                    Uses the pipeline&apos;s top-level question.
                  </p>
                )}
              </li>
            ))}
          </ol>
        </section>
      ) : null}
    </div>
  );
}
