import Link from "next/link";
import {
  fetchProtocols,
  fetchProtocolStages,
  type Protocol,
  type ProtocolStage,
} from "@/lib/api";
import { PatternIcon } from "@/components/run/PatternIcon";
import type { OrchestrationPattern } from "@/components/run/orchestrationPattern";

const META_CATEGORY = "Meta-Protocols";

const TIER_COLOR: Record<string, string> = {
  low: "border-[rgb(var(--ce-green-500))]/40 text-[rgb(var(--ce-green-500))]",
  medium: "border-[rgb(var(--ce-yellow-500))]/40 text-[rgb(var(--ce-yellow-500))]",
  high: "border-destructive/40 text-destructive",
};

const STAGE_KIND_COLOR: Record<string, string> = {
  agent: "border-primary/40 text-primary",
  synthesis: "border-[rgb(var(--ce-indigo-500))]/40 text-[rgb(var(--ce-indigo-500))]",
  mechanical: "border-muted-foreground/30 text-muted-foreground",
};

export default async function ProtocolDetailPage({
  params,
}: {
  params: Promise<{ key: string }>;
}) {
  const { key } = await params;

  const [protocolsResult, stagesResult] = await Promise.allSettled([
    fetchProtocols(),
    fetchProtocolStages(key),
  ]);

  if (protocolsResult.status === "rejected") {
    return (
      <ErrorShell
        title="Cannot reach Railway"
        detail={String(protocolsResult.reason).slice(0, 400)}
      />
    );
  }

  const protocols = protocolsResult.value;
  const protocol = protocols.find((p) => p.key === key);

  if (!protocol) {
    return <NotFoundShell requestedKey={key} />;
  }

  const stages: ProtocolStage[] =
    stagesResult.status === "fulfilled" ? stagesResult.value.stages ?? [] : [];
  const stagesSource =
    stagesResult.status === "fulfilled" ? stagesResult.value.source : undefined;

  const code =
    protocol.protocol_id ?? protocol.code ?? protocol.key.split("_")[0].toUpperCase();
  const isMeta = protocol.category === META_CATEGORY;
  const tierClass = protocol.cost_tier ? TIER_COLOR[protocol.cost_tier] : "";

  return (
    <div className="mx-auto max-w-6xl px-8 py-10 space-y-6">
      <nav className="text-xs text-muted-foreground">
        <Link href="/protocols" className="hover:text-foreground">
          ← Protocol library
        </Link>
      </nav>

      <header className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm text-primary">{code}</span>
          <span className="text-xs text-muted-foreground">·</span>
          <span className="text-xs uppercase tracking-wider text-muted-foreground">
            {protocol.category}
          </span>
          {isMeta ? (
            <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded border border-primary/40 text-primary font-mono">
              Router
            </span>
          ) : null}
        </div>
        <h1 className="text-3xl font-bold tracking-tight">{protocol.name}</h1>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {protocol.orchestration_pattern ? (
            <PatternIcon
              pattern={protocol.orchestration_pattern as OrchestrationPattern}
              size={14}
              showLabel
            />
          ) : null}
          {protocol.cost_tier ? (
            <span
              className={`uppercase tracking-wider px-1.5 py-0.5 rounded border font-mono ${tierClass}`}
            >
              {protocol.cost_tier} cost
            </span>
          ) : null}
          {protocol.min_agents || protocol.max_agents ? (
            <span className="font-mono text-muted-foreground">
              {protocol.min_agents ?? "?"}–{protocol.max_agents ?? "∞"} agents
            </span>
          ) : null}
          {protocol.supports_rounds ? (
            <span className="font-mono text-muted-foreground">· multi-round</span>
          ) : null}
        </div>
      </header>

      {protocol.description ? (
        <Section title="What it does">
          <p className="text-sm leading-relaxed text-foreground text-pretty">
            {protocol.description}
          </p>
        </Section>
      ) : null}

      {protocol.when_to_use || protocol.when_not_to_use ? (
        <div className="grid gap-3 md:grid-cols-2">
          {protocol.when_to_use ? (
            <Panel label="When to use" tone="positive">
              {protocol.when_to_use}
            </Panel>
          ) : null}
          {protocol.when_not_to_use ? (
            <Panel label="When not to use" tone="negative">
              {protocol.when_not_to_use}
            </Panel>
          ) : null}
        </div>
      ) : null}

      {protocol.problem_types && protocol.problem_types.length > 0 ? (
        <Section title="Problem types">
          <div className="flex flex-wrap gap-1.5">
            {protocol.problem_types.map((pt) => (
              <span
                key={pt}
                className="text-[11px] font-mono px-2 py-0.5 rounded border border-border bg-card text-muted-foreground"
              >
                {pt}
              </span>
            ))}
          </div>
        </Section>
      ) : null}

      <Section title="How it runs">
        <StageList stages={stages} source={stagesSource} />
      </Section>

      <footer className="flex flex-wrap items-center gap-3 pt-4 border-t border-border">
        {isMeta ? (
          <div className="flex-1 rounded-xl border border-primary/30 bg-primary/5 p-4 text-sm text-primary/90">
            Meta-protocols are invoked automatically via Smart Route on Ask — they
            are not selectable as a standalone run.
          </div>
        ) : (
          <Link
            href={`/run?protocol=${protocol.key}`}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-[rgb(var(--ce-indigo-500))]"
          >
            Run this protocol →
          </Link>
        )}
        <Link
          href="/protocols"
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          ← Back to library
        </Link>
      </footer>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="ce-eyebrow">{title}</h2>
      {children}
    </section>
  );
}

function Panel({
  label,
  tone,
  children,
}: {
  label: string;
  tone: "positive" | "negative";
  children: React.ReactNode;
}) {
  const border =
    tone === "positive"
      ? "border-[rgb(var(--ce-green-500))]/30"
      : "border-destructive/30";
  const chip =
    tone === "positive"
      ? "text-[rgb(var(--ce-green-500))]"
      : "text-destructive";
  return (
    <div className={`rounded-xl border ${border} bg-card p-4 space-y-2`}>
      <div className={`text-[10px] uppercase tracking-wider font-mono ${chip}`}>
        {label}
      </div>
      <p className="text-sm leading-relaxed text-foreground text-pretty">{children}</p>
    </div>
  );
}

function StageList({
  stages,
  source,
}: {
  stages: ProtocolStage[];
  source: string | undefined;
}) {
  if (!stages || stages.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-4 text-sm text-muted-foreground">
        Stage manifest not yet published for this protocol.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <ol className="space-y-2">
        {stages.map((s, i) => {
          const kind = s.stage_type ?? "agent";
          const kindClass = STAGE_KIND_COLOR[kind] ?? STAGE_KIND_COLOR.agent;
          return (
            <li
              key={s.key || `${i}-${s.name}`}
              className="rounded-xl border border-border bg-card p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-baseline gap-2">
                  <span className="font-mono text-xs text-muted-foreground tabular-nums">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="font-medium text-foreground">{s.name}</span>
                </div>
                <span
                  className={`text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded border font-mono shrink-0 ${kindClass}`}
                >
                  {kind}
                </span>
              </div>
              {s.description ? (
                <p className="mt-2 text-xs leading-relaxed text-muted-foreground text-pretty">
                  {s.description}
                </p>
              ) : null}
            </li>
          );
        })}
      </ol>
      {source === "fallback" ? (
        <p className="text-[10px] text-muted-foreground italic">
          Stage structure inferred from orchestrator source — may not reflect every step.
        </p>
      ) : null}
    </div>
  );
}

function NotFoundShell({ requestedKey }: { requestedKey: string }) {
  return (
    <div className="mx-auto max-w-3xl px-8 py-16 space-y-4">
      <span className="ce-eyebrow">Not found</span>
      <h1 className="text-2xl font-bold tracking-tight">Protocol not found</h1>
      <p className="text-sm text-muted-foreground">
        No protocol is registered under the key{" "}
        <span className="font-mono text-foreground">{requestedKey}</span>.
      </p>
      <Link
        href="/protocols"
        className="inline-flex text-sm text-primary hover:underline"
      >
        ← Back to protocol library
      </Link>
    </div>
  );
}

function ErrorShell({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="mx-auto max-w-3xl px-8 py-16 space-y-4">
      <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
        <strong>{title}.</strong>
        <div className="text-destructive/70 text-xs mt-1 font-mono">{detail}</div>
      </div>
      <Link
        href="/protocols"
        className="inline-flex text-sm text-primary hover:underline"
      >
        ← Back to protocol library
      </Link>
    </div>
  );
}
