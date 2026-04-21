import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchRun } from "@/lib/api";
import NewCorrectionForm from "../../corrections/NewCorrectionForm";
import { DeleteRunButton } from "./DeleteRunButton";

type RunDetail = Awaited<ReturnType<typeof fetchRun>> & {
  outputs?: Array<{
    id: number;
    agent_key: string;
    model?: string | null;
    output_text: string;
    cost_usd?: number;
    input_tokens?: number;
    output_tokens?: number;
  }>;
  steps?: Array<{ id: number; step_order: number; protocol_key: string; status: string; cost_usd?: number }>;
  error_message?: string | null;
  protocol_report?: { metadata?: Record<string, unknown> } | null;
};

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { orgSlug } = await auth();

  let run: RunDetail | null = null;
  let apiError: string | null = null;
  try {
    run = (await fetchRun(id)) as RunDetail;
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.includes("404")) {
      notFound();
    }
    apiError = msg;
  }

  if (!run && !apiError) {
    notFound();
  }

  const railwayApi = process.env.NEXT_PUBLIC_RAILWAY_API_URL ?? "http://localhost:8000";

  return (
    <div className="mx-auto max-w-5xl px-8 py-10 space-y-6">
        <header className="flex items-end justify-between">
          <div>
            <Link href="/runs" className="text-xs text-muted-foreground hover:text-foreground transition-colors">
              &larr; All runs
            </Link>
            <h1 className="mt-2 text-3xl font-bold tracking-tight">Run #{id}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {orgSlug ? <span className="font-mono">{orgSlug}</span> : "(no org)"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={`${railwayApi}/api/reports/${id}/pdf`}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-secondary"
            >
              Download PDF &darr;
            </a>
            <DeleteRunButton id={id} />
          </div>
        </header>

        {apiError ? (
          <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
            <strong>Railway API unreachable.</strong>
            <div className="text-destructive/70 text-xs mt-1 font-mono">{apiError}</div>
          </div>
        ) : null}

        {run ? (
          <>
            <section className="rounded-xl border border-border bg-card p-5 space-y-3">
              <div>
                <div className="ce-label mb-1">Question</div>
                <div className="text-base">{run.question}</div>
              </div>
              <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-muted-foreground">
                <Meta label="Protocol" value={run.protocol_key} mono />
                <Meta label="Status" value={run.status} />
                <Meta
                  label="Started"
                  value={run.started_at ? new Date(run.started_at).toLocaleString() : "—"}
                />
                <Meta
                  label="Cost"
                  value={run.cost_usd != null ? `$${run.cost_usd.toFixed(4)}` : "—"}
                />
              </div>
              {run.agent_keys && run.agent_keys.length > 0 ? (
                <div className="text-xs text-muted-foreground">
                  <span className="ce-label mr-2">Agents:</span>
                  {run.agent_keys.map((k) => (
                    <span key={k} className="inline-block bg-secondary text-secondary-foreground px-2 py-0.5 rounded mr-1 font-mono">
                      {k}
                    </span>
                  ))}
                </div>
              ) : null}
              {run.error_message ? (
                <div className="rounded border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive font-mono">
                  {run.error_message.slice(0, 800)}
                </div>
              ) : null}
            </section>

            <section className="space-y-2">
              <div className="flex items-center justify-between">
                <h2 className="ce-label">Correct this</h2>
                <span className="text-[10px] text-muted-foreground">
                  Will apply to future runs touching this decision
                </span>
              </div>
              <NewCorrectionForm initialScope="decision" initialTarget={id} compact />
            </section>

            {run.outputs && run.outputs.length > 0 ? (
              <section className="space-y-3">
                <h2 className="ce-label">Agent transcripts</h2>
                {run.outputs.map((o) => (
                  <details
                    key={o.id}
                    className="rounded-xl border border-border bg-card group"
                    open={o.agent_key === "_synthesis"}
                  >
                    <summary className="cursor-pointer p-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-sm text-primary">{o.agent_key}</span>
                        {o.model ? (
                          <span className="text-[10px] text-muted-foreground font-mono">{o.model}</span>
                        ) : null}
                      </div>
                      <span className="text-[10px] text-muted-foreground tabular-nums">
                        {o.cost_usd ? `$${o.cost_usd.toFixed(4)}` : ""}
                        {o.input_tokens ? `  ${o.input_tokens}↓` : ""}
                        {o.output_tokens ? ` ${o.output_tokens}↑` : ""}
                      </span>
                    </summary>
                    <div className="px-5 pb-5 pt-0">
                      <pre className="whitespace-pre-wrap text-sm text-foreground font-sans leading-relaxed">
                        {o.output_text}
                      </pre>
                    </div>
                  </details>
                ))}
              </section>
            ) : null}
          </>
        ) : null}
    </div>
  );
}

function Meta({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <span className="ce-label mr-2">{label}:</span>
      <span className={mono ? "font-mono" : ""}>{value}</span>
    </div>
  );
}
