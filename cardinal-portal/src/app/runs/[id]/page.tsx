import { auth } from "@clerk/nextjs/server";
import { OrganizationSwitcher, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchRun } from "@/lib/api";
import NewCorrectionForm from "../../corrections/NewCorrectionForm";

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
    <main className="min-h-screen p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <Link href="/runs" className="text-xs text-slate-500 hover:text-slate-300">
              &larr; All runs
            </Link>
            <h1 className="text-2xl font-semibold tracking-tight mt-1">Run #{id}</h1>
            <p className="text-sm text-slate-400 mt-1">
              Tenant: <span className="font-mono text-slate-200">{orgSlug ?? "(no org)"}</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <a
              href={`${railwayApi}/api/reports/${id}/pdf`}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-md border border-slate-700 px-3 py-1.5 text-xs font-medium hover:bg-slate-900 transition"
            >
              Download PDF &darr;
            </a>
            <OrganizationSwitcher hidePersonal />
            <UserButton />
          </div>
        </header>

        {apiError ? (
          <div className="rounded-lg border border-rose-700/40 bg-rose-950/20 p-4 text-sm text-rose-200">
            <strong>Railway API unreachable.</strong>
            <div className="text-rose-300/70 text-xs mt-1 font-mono">{apiError}</div>
          </div>
        ) : null}

        {run ? (
          <>
            {/* Question + meta */}
            <section className="rounded-lg border border-slate-800 bg-slate-900/40 p-5 space-y-3">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Question</div>
                <div className="text-base">{run.question}</div>
              </div>
              <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-400">
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
                <div className="text-xs text-slate-400">
                  <span className="text-slate-500 uppercase tracking-wider mr-2">Agents:</span>
                  {run.agent_keys.map((k) => (
                    <span key={k} className="inline-block bg-slate-800 px-2 py-0.5 rounded mr-1 font-mono">
                      {k}
                    </span>
                  ))}
                </div>
              ) : null}
              {run.error_message ? (
                <div className="rounded border border-rose-700/40 bg-rose-950/20 p-3 text-xs text-rose-200 font-mono">
                  {run.error_message.slice(0, 800)}
                </div>
              ) : null}
            </section>

            {/* Correct this run -- writes a Correction node scoped to this decision */}
            <section className="space-y-2">
              <div className="flex items-center justify-between">
                <h2 className="text-sm uppercase tracking-wider text-slate-400">
                  Correct this
                </h2>
                <span className="text-[10px] text-slate-500">
                  Will apply to future runs touching this decision
                </span>
              </div>
              <NewCorrectionForm initialScope="decision" initialTarget={id} compact />
            </section>

            {/* Agent outputs */}
            {run.outputs && run.outputs.length > 0 ? (
              <section className="space-y-3">
                <h2 className="text-sm uppercase tracking-wider text-slate-400">Agent transcripts</h2>
                {run.outputs.map((o) => (
                  <details
                    key={o.id}
                    className="rounded-lg border border-slate-800 bg-slate-900/40 group"
                    open={o.agent_key === "_synthesis"}
                  >
                    <summary className="cursor-pointer p-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-sm text-fuchsia-300">{o.agent_key}</span>
                        {o.model ? (
                          <span className="text-[10px] text-slate-500 font-mono">{o.model}</span>
                        ) : null}
                      </div>
                      <span className="text-[10px] text-slate-500 tabular-nums">
                        {o.cost_usd ? `$${o.cost_usd.toFixed(4)}` : ""}
                        {o.input_tokens ? `  ${o.input_tokens}↓` : ""}
                        {o.output_tokens ? ` ${o.output_tokens}↑` : ""}
                      </span>
                    </summary>
                    <div className="px-5 pb-5 pt-0">
                      <pre className="whitespace-pre-wrap text-sm text-slate-200 font-sans leading-relaxed">
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
    </main>
  );
}

function Meta({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <span className="text-slate-500 uppercase tracking-wider mr-2">{label}:</span>
      <span className={mono ? "font-mono" : ""}>{value}</span>
    </div>
  );
}
