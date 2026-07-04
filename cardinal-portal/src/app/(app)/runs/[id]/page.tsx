import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Wrench } from "lucide-react";
import { fetchRun, type StageAudit, type StageAuditStatus, type ToolCall } from "@/lib/api";
import NewCorrectionForm from "../../corrections/NewCorrectionForm";
import { DeleteRunButton } from "./DeleteRunButton";
import { Markdown } from "@/components/ui/markdown";
import { ArticleView } from "@/components/run/ArticleView";
import { ArticleTabs } from "@/components/run/ArticleTabs";

type RunDetail = Awaited<ReturnType<typeof fetchRun>>;

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
          run.protocol_report?.article ? (
            <ArticleTabs
              defaultTab="story"
              article={<ArticleView article={run.protocol_report.article} />}
              analyst={<RunAnalystStack run={run} id={id} />}
            />
          ) : (
            <RunAnalystStack run={run} id={id} />
          )
        ) : null}
    </div>
  );
}

function RunAnalystStack({ run, id }: { run: RunDetail; id: string }) {
  return (
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

            {/* Run Audit — observed vs intended stage table */}
            {run.protocol_report?.audit && "stages" in run.protocol_report.audit && run.protocol_report.audit.stages.length > 0 ? (
              <AuditCard
                stages={run.protocol_report.audit.stages}
                completeness={run.protocol_report.audit.completeness}
                overallAdvice={run.protocol_report.audit.overall_advice}
              />
            ) : null}

            {/* Executive Summary — elevated above agent transcripts so users see the answer, not working notes */}
            {run.protocol_report?.executive_summary ? (
              <section className="rounded-xl border border-primary/30 bg-primary/5 p-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="ce-label">Executive Summary</h2>
                  {run.protocol_report.confidence_score > 0 ? (
                    <span className="text-[10px] font-mono text-muted-foreground">
                      Confidence: {run.protocol_report.confidence_label} ({run.protocol_report.confidence_score}/5)
                    </span>
                  ) : null}
                </div>
                <div className="text-sm leading-relaxed text-foreground">
                  <Markdown>{run.protocol_report.executive_summary}</Markdown>
                </div>
              </section>
            ) : null}

            {/* Full Synthesis — the complete adapter-composed answer */}
            {run.protocol_report?.synthesis &&
              run.protocol_report.synthesis !== run.protocol_report.executive_summary ? (
              <section className="rounded-xl border border-border bg-card p-5">
                <h2 className="ce-label mb-3">Full Synthesis</h2>
                <div className="text-sm leading-relaxed text-foreground">
                  <Markdown>{run.protocol_report.synthesis}</Markdown>
                </div>
              </section>
            ) : null}

            <section className="space-y-2">
              <div className="flex items-center justify-between">
                <h2 className="ce-label">Correct this</h2>
                <span className="text-[10px] text-muted-foreground">
                  Will apply to future runs touching this decision
                </span>
              </div>
              <NewCorrectionForm initialScope="decision" initialTarget={id} compact />
            </section>

            {run.outputs && run.outputs.filter((o) => o.agent_key !== "_synthesis").length > 0 ? (
              <ToolsPanel
                outputs={run.outputs.filter((o) => o.agent_key !== "_synthesis")}
              />
            ) : null}

            {run.outputs && run.outputs.filter((o) => o.agent_key !== "_synthesis").length > 0 ? (
              <section className="space-y-3">
                <h2 className="ce-label">Agent transcripts · Working notes</h2>
                {run.outputs
                  .filter((o) => o.agent_key !== "_synthesis")
                  .map((o) => (
                    <details
                      key={o.id}
                      className="rounded-xl border border-border bg-card group"
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
                        <Markdown>{o.output_text}</Markdown>
                      </div>
                    </details>
                  ))}
              </section>
            ) : null}
    </>
  );
}

type AgentOutputForTools = {
  id: number;
  agent_key: string;
  tool_calls?: ToolCall[];
};

function ToolsPanel({ outputs }: { outputs: AgentOutputForTools[] }) {
  const totalCalls = outputs.reduce(
    (sum, o) => sum + (o.tool_calls?.length ?? 0),
    0,
  );

  return (
    <section className="rounded-xl border border-border bg-card p-5 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="ce-label flex items-center gap-2">
          <Wrench size={12} /> Tools used
        </h2>
        <span className="text-[11px] tabular-nums text-muted-foreground">
          {totalCalls} {totalCalls === 1 ? "call" : "calls"} across {outputs.length}{" "}
          {outputs.length === 1 ? "agent" : "agents"}
        </span>
      </div>

      {totalCalls === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-background px-3 py-2 text-xs italic text-muted-foreground">
          No tools invoked. Agents answered from prompt + memory only.
        </div>
      ) : (
        <div className="space-y-3">
          {outputs.map((o) => {
            const calls = o.tool_calls ?? [];
            if (calls.length === 0) {
              return (
                <div
                  key={o.id}
                  className="flex items-center justify-between rounded-lg border border-border bg-background px-3 py-1.5 text-[11px]"
                >
                  <span className="font-mono text-foreground">{o.agent_key}</span>
                  <span className="italic text-muted-foreground">no tools invoked</span>
                </div>
              );
            }
            return (
              <details key={o.id} className="rounded-lg border border-border bg-background">
                <summary className="cursor-pointer flex items-center justify-between gap-3 px-3 py-2 text-xs">
                  <span className="font-mono text-foreground">{o.agent_key}</span>
                  <span className="flex items-center gap-2 tabular-nums text-muted-foreground">
                    <span>
                      {calls.length} {calls.length === 1 ? "call" : "calls"}
                    </span>
                    <ToolNameStack calls={calls} />
                  </span>
                </summary>
                <div className="space-y-2 border-t border-border p-3">
                  {calls.map((c, i) => (
                    <ToolCallRow key={`${o.id}-${i}`} call={c} index={i} />
                  ))}
                </div>
              </details>
            );
          })}
        </div>
      )}
    </section>
  );
}

function ToolNameStack({ calls }: { calls: ToolCall[] }) {
  const counts = new Map<string, number>();
  for (const c of calls) counts.set(c.tool, (counts.get(c.tool) ?? 0) + 1);
  return (
    <span className="flex flex-wrap items-center gap-1">
      {Array.from(counts.entries())
        .slice(0, 4)
        .map(([tool, n]) => (
          <span
            key={tool}
            className="rounded-full border border-border bg-card px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
          >
            {tool}
            {n > 1 ? <span className="ml-0.5 text-foreground">×{n}</span> : null}
          </span>
        ))}
    </span>
  );
}

function ToolCallRow({ call, index }: { call: ToolCall; index: number }) {
  return (
    <div className="rounded border border-border bg-card p-2 text-[11px]">
      <div className="mb-1 flex items-center gap-2">
        <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-secondary font-mono text-[9px] text-muted-foreground">
          {index + 1}
        </span>
        <span className="font-mono text-foreground">{call.tool}</span>
        {call.iteration != null ? (
          <span className="text-muted-foreground">iter {call.iteration}</span>
        ) : null}
        {call.elapsed_ms != null ? (
          <span className="ml-auto tabular-nums text-muted-foreground">
            {call.elapsed_ms.toFixed(0)} ms
          </span>
        ) : null}
      </div>
      {call.input_summary ? (
        <div className="mb-1">
          <div className="ce-label text-[9px]">input</div>
          <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded bg-secondary/40 p-1.5 font-mono text-[10px] text-foreground">
            {call.input_summary}
          </pre>
        </div>
      ) : null}
      {call.result_summary ? (
        <div>
          <div className="ce-label text-[9px]">result</div>
          <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap break-words rounded bg-secondary/40 p-1.5 font-mono text-[10px] text-foreground">
            {call.result_summary}
          </pre>
        </div>
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

const STATUS_STYLES: Record<StageAuditStatus, string> = {
  ok: "bg-[rgb(var(--ce-green-500))]/15 text-[rgb(var(--ce-green-500))] border-[rgb(var(--ce-green-500))]/30",
  missing: "bg-destructive/15 text-destructive border-destructive/30",
  partial:
    "bg-[rgb(var(--ce-yellow-500))]/15 text-[rgb(var(--ce-yellow-500))] border-[rgb(var(--ce-yellow-500))]/30",
  degraded:
    "bg-[rgb(var(--ce-yellow-500))]/15 text-[rgb(var(--ce-yellow-500))] border-[rgb(var(--ce-yellow-500))]/30",
  implicit: "bg-secondary text-muted-foreground border-border",
  unknown: "bg-secondary text-muted-foreground border-border",
};

function StatusPill({ status }: { status: StageAuditStatus }) {
  return (
    <span
      className={`inline-block rounded border px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-wider ${
        STATUS_STYLES[status] ?? STATUS_STYLES.unknown
      }`}
    >
      {status}
    </span>
  );
}

function AuditCard({
  stages,
  completeness,
  overallAdvice,
}: {
  stages: StageAudit[];
  completeness: string;
  overallAdvice: string | null;
}) {
  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="ce-label">Run Audit · Observed vs Intended</h2>
        {completeness ? (
          <span className="text-[10px] font-mono text-muted-foreground">{completeness}</span>
        ) : null}
      </div>
      <div className="space-y-2">
        {stages.map((stage, i) => (
          <div
            key={`${stage.name}-${i}`}
            className="flex items-start gap-3 border-t border-border pt-2 first:border-t-0 first:pt-0"
          >
            <div className="mt-0.5 w-16 shrink-0">
              <StatusPill status={stage.status} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold">{stage.name}</div>
              {stage.intent ? (
                <div className="text-[11px] text-muted-foreground">{stage.intent}</div>
              ) : null}
              {stage.advice ? (
                <div className="mt-1 rounded border-l-2 border-[rgb(var(--ce-yellow-500))] bg-[rgb(var(--ce-yellow-500))]/10 px-2 py-1 text-[11px] text-foreground">
                  {stage.advice}
                </div>
              ) : null}
            </div>
            <div className="w-1/3 shrink-0 font-mono text-[10px] text-muted-foreground">
              {stage.observed}
            </div>
          </div>
        ))}
      </div>
      {overallAdvice ? (
        <div className="mt-3 rounded border-l-2 border-[rgb(var(--ce-yellow-500))] bg-[rgb(var(--ce-yellow-500))]/10 px-3 py-2 text-xs text-foreground">
          {overallAdvice}
        </div>
      ) : null}
    </section>
  );
}
