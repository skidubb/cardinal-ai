"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, Paperclip, X } from "lucide-react";
import type {
  Agent,
  Pipeline,
  Protocol,
  RouterDecision,
  Team,
} from "@/lib/api";
import MemoryBrief from "./MemoryBrief";
import { ModeSelector, type RunMode } from "@/components/run/ModeSelector";
import { ProtocolDiagram } from "@/components/run/ProtocolDiagram";
import { useProtocolStages } from "@/components/run/useProtocolStages";
import { inferLiveStage } from "@/components/run/liveStageInference";
import { RouterDecisionCard } from "@/components/run/RouterDecisionCard";

type SseEvent = { event: string; data: Record<string, unknown> };

type AgentTrace = {
  agent_key: string;
  text: string;
  model?: string;
  cost_usd?: number;
  input_tokens?: number;
  output_tokens?: number;
};

export default function RunForm({
  protocols,
  agents,
  pipelines,
  teams,
  initialQuestion = "",
  initialProtocol = "",
}: {
  protocols: Protocol[];
  agents: Agent[];
  pipelines: Pipeline[];
  teams: Team[];
  initialQuestion?: string;
  initialProtocol?: string;
}) {
  const hasInitialProtocol =
    initialProtocol && protocols.some((p) => p.key === initialProtocol);
  const [mode, setMode] = useState<RunMode>(hasInitialProtocol ? "protocol" : "smart");
  const [question, setQuestion] = useState(initialQuestion);

  const [protocolKey, setProtocolKey] = useState<string>(
    hasInitialProtocol
      ? initialProtocol
      : protocols.find((p) => p.key === "p04_multi_round_debate")?.key ?? protocols[0]?.key ?? "",
  );
  const [agentKeys, setAgentKeys] = useState<string[]>(["ceo", "cfo", "cto"]);
  const [rounds, setRounds] = useState<number>(2);

  const [pipelineKey, setPipelineKey] = useState<string>(
    pipelines[0] ? String(pipelines[0].id) : "",
  );

  const [decision, setDecision] = useState<RouterDecision | null>(null);
  const [deciding, setDeciding] = useState(false);

  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<SseEvent[]>([]);
  const [traces, setTraces] = useState<Record<string, AgentTrace>>({});
  const [synthesis, setSynthesis] = useState<string>("");
  const [runId, setRunId] = useState<number | null>(null);
  const [completedRunId, setCompletedRunId] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const { data: stagesData } = useProtocolStages(
    mode === "protocol" ? protocolKey : null,
  );
  const liveStage = useMemo(() => {
    if (!stagesData || events.length === 0 || mode !== "protocol") {
      return { activeStageKey: null, completedStageKeys: [] };
    }
    return inferLiveStage(stagesData.stages, events);
  }, [stagesData, events, mode]);

  const selectedProtocol = protocols.find((p) => p.key === protocolKey);

  useEffect(() => {
    if (mode !== "smart") {
      setDecision(null);
      return;
    }
    const q = question.trim();
    if (q.length < 15) {
      setDecision(null);
      return;
    }
    const ctrl = new AbortController();
    const handle = setTimeout(async () => {
      setDeciding(true);
      try {
        const resp = await fetch("/api/proxy/router/decide", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: q }),
          signal: ctrl.signal,
        });
        if (resp.ok) {
          setDecision((await resp.json()) as RouterDecision);
        }
      } catch {
        // silent — decide is advisory
      } finally {
        setDeciding(false);
      }
    }, 700);
    return () => {
      ctrl.abort();
      clearTimeout(handle);
    };
  }, [mode, question]);

  function toggleAgent(key: string) {
    setAgentKeys((curr) => (curr.includes(key) ? curr.filter((k) => k !== key) : [...curr, key]));
  }

  function applyTeam(teamId: string) {
    if (!teamId) return;
    const t = teams.find((t) => String(t.id) === teamId);
    if (t) setAgentKeys(t.agent_keys);
  }

  async function saveAsTeam() {
    const name = prompt("Team name?");
    if (!name?.trim()) return;
    try {
      const resp = await fetch("/api/proxy/teams", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), agent_keys: agentKeys }),
      });
      if (!resp.ok) throw new Error(`${resp.status}: ${(await resp.text()).slice(0, 200)}`);
      alert(`Saved team "${name}". Reload to see it in the dropdown.`);
    } catch (e: unknown) {
      alert(`Save failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  }

  async function startRun() {
    if (!question.trim() || running) return;
    setRunning(true);
    setError(null);
    setEvents([]);
    setTraces({});
    setSynthesis("");
    setRunId(null);
    setCompletedRunId(null);

    const controller = new AbortController();
    abortRef.current = controller;

    const hasFiles = attachedFiles.length > 0;

    let endpoint = "/api/proxy/run";
    let body: Record<string, unknown> | FormData = {};

    if (mode === "smart") {
      endpoint = "/api/proxy/router/run";
      body = { question };
    } else if (mode === "pipeline") {
      const selectedPipeline = pipelines.find((p) => String(p.id) === pipelineKey);
      if (!selectedPipeline) {
        setError("Pick a pipeline first.");
        setRunning(false);
        return;
      }
      endpoint = "/api/proxy/pipelines/run";
      body = {
        question,
        agent_keys: agentKeys,
        steps: selectedPipeline.steps.map((s) => ({
          protocol_key: s.protocol_key,
          question_template: s.question_template,
          thinking_model: s.thinking_model,
          orchestration_model: s.orchestration_model,
          rounds: s.rounds,
          output_passthrough: s.output_passthrough ?? true,
          no_tools: s.no_tools ?? false,
        })),
      };
    } else {
      if (!protocolKey || agentKeys.length === 0) {
        setError("Pick a protocol and at least one agent.");
        setRunning(false);
        return;
      }

      if (hasFiles) {
        // Multipart path — can only attach context to single-protocol runs
        endpoint = "/api/proxy/run-with-context";
        const fd = new FormData();
        fd.append("protocol_key", protocolKey);
        fd.append("question", question);
        fd.append("agent_keys", JSON.stringify(agentKeys));
        if (selectedProtocol?.max_agents && selectedProtocol.max_agents > 0 && rounds) {
          fd.append("rounds", String(rounds));
        }
        fd.append("no_tools", "false");
        for (const f of attachedFiles) fd.append("files", f);
        body = fd;
      } else {
        body = {
          protocol_key: protocolKey,
          question,
          agent_keys: agentKeys,
          rounds:
            selectedProtocol?.max_agents && selectedProtocol.max_agents > 0 ? rounds : undefined,
          no_tools: false,
        };
      }
    }

    const isFormData = body instanceof FormData;
    const fetchBody: BodyInit = isFormData ? (body as FormData) : JSON.stringify(body);

    try {
      const resp = await fetch(endpoint, {
        method: "POST",
        headers: isFormData ? {} : { "Content-Type": "application/json" },
        body: fetchBody,
        signal: controller.signal,
      });

      if (!resp.ok || !resp.body) {
        throw new Error(`HTTP ${resp.status}: ${(await resp.text()).slice(0, 300)}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const messages = buffer.split("\n\n");
        buffer = messages.pop() ?? "";

        for (const raw of messages) {
          if (!raw.trim() || raw.startsWith(":")) continue;
          const lines = raw.split("\n");
          let eventName = "message";
          let dataStr = "";
          for (const line of lines) {
            if (line.startsWith("event:")) eventName = line.slice(6).trim();
            else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
          }
          if (!dataStr) continue;
          let data: Record<string, unknown> = {};
          try {
            data = JSON.parse(dataStr);
          } catch {
            continue;
          }
          handleEvent({ event: eventName, data });
        }
      }
    } catch (e: unknown) {
      if ((e as { name?: string })?.name === "AbortError") return;
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }

  function handleEvent(ev: SseEvent) {
    setEvents((curr) => [...curr, ev]);
    const d = ev.data;
    switch (ev.event) {
      case "router_decision":
        setDecision(d as unknown as RouterDecision);
        if (typeof d.run_id === "number") setRunId(d.run_id);
        break;
      case "run_start":
        if (typeof d.run_id === "number") setRunId(d.run_id);
        break;
      case "agent_output": {
        const key = String(d.agent_key ?? "unknown");
        setTraces((curr) => ({
          ...curr,
          [key]: {
            agent_key: key,
            text: String(d.text ?? d.output_text ?? ""),
            model: d.model as string | undefined,
            cost_usd: d.cost_usd as number | undefined,
            input_tokens: d.input_tokens as number | undefined,
            output_tokens: d.output_tokens as number | undefined,
          },
        }));
        break;
      }
      case "synthesis":
        setSynthesis(String(d.text ?? ""));
        break;
      case "run_complete":
        if (typeof d.run_id === "number") setCompletedRunId(d.run_id);
        break;
      case "error":
      case "router_error":
        setError(String(d.message ?? d.error ?? "Run failed"));
        break;
    }
  }

  function cancel() {
    abortRef.current?.abort();
    setRunning(false);
  }

  const agentsByCategory: Record<string, Agent[]> = {};
  for (const a of agents) {
    const cat = (a as Agent & { category?: string }).category ?? a.layer ?? "other";
    if (!agentsByCategory[cat]) agentsByCategory[cat] = [];
    agentsByCategory[cat].push(a);
  }
  const categoryOrder = [
    "executive",
    "c_suite",
    "cfo-team",
    "cto-team",
    "cmo-team",
    "cpo-team",
    "coo-team",
    "cro-team",
    "gtm-sales",
    "gtm-marketing",
    "direct_report",
    "functional",
    "other",
  ];
  const sortedCategories = Object.keys(agentsByCategory).sort(
    (a, b) =>
      (categoryOrder.indexOf(a) >= 0 ? categoryOrder.indexOf(a) : 999) -
      (categoryOrder.indexOf(b) >= 0 ? categoryOrder.indexOf(b) : 999),
  );

  const canRun =
    !running &&
    question.trim().length > 0 &&
    (mode === "smart" ||
      (mode === "protocol" && protocolKey && agentKeys.length > 0) ||
      (mode === "pipeline" && !!pipelineKey));

  return (
    <div className="space-y-6">
      <div>
        <span className="ce-label mb-2 block">Mode</span>
        <ModeSelector value={mode} onChange={setMode} />
      </div>

      <section className="rounded-xl border border-primary/30 bg-primary/5 p-5">
        <label className="ce-label mb-2 block">Strategic question</label>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. Should we expand into the European market in Q3? What pricing tier maximizes revenue without churn risk?"
          rows={3}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:border-ring focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
          disabled={running}
        />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={running || mode !== "protocol"}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground disabled:opacity-40"
            title={
              mode === "protocol"
                ? "Attach PDF/TXT/MD context for this single run (non-persistent)"
                : "File attachment is available only in Pick protocol mode"
            }
          >
            <Paperclip size={12} /> Attach context
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            hidden
            accept=".pdf,.txt,.md,.markdown"
            onChange={(e) => {
              const chosen = Array.from(e.target.files ?? []);
              if (chosen.length) setAttachedFiles((curr) => [...curr, ...chosen]);
              e.target.value = "";
            }}
          />
          {attachedFiles.map((f, i) => (
            <span
              key={`${f.name}-${i}`}
              className="inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 font-mono text-[10px] text-primary"
              title={`${(f.size / 1024).toFixed(1)} KB`}
            >
              <Paperclip size={10} />
              {f.name}
              <button
                type="button"
                onClick={() => setAttachedFiles((curr) => curr.filter((_, idx) => idx !== i))}
                disabled={running}
                className="ml-0.5 text-muted-foreground transition-colors hover:text-destructive"
                aria-label={`Remove ${f.name}`}
              >
                <X size={10} />
              </button>
            </span>
          ))}
        </div>
        <div className="mt-3">
          <MemoryBrief question={question} />
        </div>
      </section>

      {mode === "smart" ? (
        <RouterDecisionCard decision={decision} loading={deciding} />
      ) : null}

      {mode === "protocol" ? (
        <div className="grid gap-6 md:grid-cols-2">
          <section className="rounded-xl border border-border bg-card p-4">
            <label className="ce-label mb-2 block">
              Protocol ({protocols.length} available)
            </label>
            <select
              value={protocolKey}
              onChange={(e) => setProtocolKey(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
              disabled={running}
            >
              {protocols.map((p) => (
                <option key={p.key} value={p.key}>
                  {p.code ?? p.key.split("_")[0].toUpperCase()} — {p.name} ({p.category})
                </option>
              ))}
            </select>
            {selectedProtocol?.description ? (
              <p className="mt-2 text-xs leading-relaxed text-muted-foreground text-pretty">
                {selectedProtocol.description}
              </p>
            ) : null}
            {selectedProtocol && (selectedProtocol.max_agents ?? 0) > 1 ? (
              <div className="mt-3">
                <label className="ce-label">Rounds</label>
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={rounds}
                  onChange={(e) => setRounds(Number(e.target.value))}
                  className="ml-2 w-16 rounded border border-input bg-background px-2 py-1 text-sm tabular-nums text-foreground"
                  disabled={running}
                />
              </div>
            ) : null}
            {protocolKey ? (
              <div className="mt-4">
                <ProtocolDiagram
                  protocolKey={protocolKey}
                  initialData={stagesData}
                  activeStageKey={liveStage.activeStageKey}
                  completedStageKeys={liveStage.completedStageKeys}
                />
              </div>
            ) : null}
          </section>

          <section className="rounded-xl border border-border bg-card p-4">
            <div className="mb-2 flex items-center justify-between gap-2">
              <label className="ce-label">
                Agents ({agentKeys.length} selected)
              </label>
              <div className="flex items-center gap-2">
                {teams.length > 0 ? (
                  <select
                    onChange={(e) => applyTeam(e.target.value)}
                    defaultValue=""
                    disabled={running}
                    className="rounded border border-input bg-background px-2 py-1 text-[10px] text-foreground"
                  >
                    <option value="">Load team…</option>
                    {teams.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                ) : null}
                <button
                  type="button"
                  onClick={saveAsTeam}
                  disabled={running || agentKeys.length === 0}
                  className="rounded border border-border px-2 py-1 text-[10px] transition-colors hover:bg-secondary disabled:opacity-50"
                >
                  Save team
                </button>
              </div>
            </div>
            <div className="max-h-60 space-y-3 overflow-y-auto pr-1">
              {sortedCategories.map((cat) => (
                <div key={cat}>
                  <div className="ce-label mb-1">{cat}</div>
                  <div className="flex flex-wrap gap-1">
                    {agentsByCategory[cat].map((a) => (
                      <button
                        key={a.key}
                        type="button"
                        onClick={() => toggleAgent(a.key)}
                        disabled={running}
                        className={`rounded border px-2 py-1 text-xs transition-colors ${
                          agentKeys.includes(a.key)
                            ? "border-primary/40 bg-primary/15 text-primary"
                            : "border-border bg-background text-foreground hover:border-primary/50"
                        } disabled:opacity-50`}
                      >
                        {a.key}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      ) : null}

      {mode === "pipeline" ? (
        <section className="rounded-xl border border-border bg-card p-4">
          <label className="ce-label mb-2 block">
            Pipeline ({pipelines.length} saved)
          </label>
          {pipelines.length === 0 ? (
            <div className="text-sm text-muted-foreground">
              No pipelines saved yet.{" "}
              <a href="/pipelines" className="text-primary underline-offset-4 hover:underline">
                Build one →
              </a>
            </div>
          ) : (
            <>
              <select
                value={pipelineKey}
                onChange={(e) => setPipelineKey(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
                disabled={running}
              >
                {pipelines.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.steps.length} steps)
                  </option>
                ))}
              </select>
              {(() => {
                const selected = pipelines.find((p) => String(p.id) === pipelineKey);
                if (!selected) return null;
                return (
                  <div className="mt-3 space-y-2 text-xs">
                    {selected.description ? (
                      <p className="text-muted-foreground text-pretty">{selected.description}</p>
                    ) : null}
                    <ol className="space-y-1">
                      {selected.steps.map((s, i) => (
                        <li
                          key={s.id ?? i}
                          className="flex items-center gap-2 rounded border border-border bg-background px-2 py-1.5 font-mono"
                        >
                          <span className="text-muted-foreground">{i + 1}.</span>
                          <span className="text-foreground">{s.protocol_key}</span>
                          {s.rounds ? (
                            <span className="text-muted-foreground">· {s.rounds} rounds</span>
                          ) : null}
                        </li>
                      ))}
                    </ol>
                  </div>
                );
              })()}
            </>
          )}
        </section>
      ) : null}

      <div className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground">
          {mode === "smart" ? (
            <span>Smart routing {decision?.plan ? `· ${decision.plan.protocol_id}` : ""}</span>
          ) : mode === "protocol" && selectedProtocol ? (
            <>
              <span className="font-mono">{selectedProtocol.key}</span> with{" "}
              <span className="font-mono">{agentKeys.join(", ") || "(no agents)"}</span>
            </>
          ) : mode === "pipeline" && pipelineKey ? (
            <span className="font-mono">pipeline #{pipelineKey}</span>
          ) : null}
        </div>
        <div className="flex gap-3">
          {running ? (
            <button
              onClick={cancel}
              className="rounded-md border border-border px-4 py-2 text-sm transition-colors hover:bg-secondary"
            >
              Cancel
            </button>
          ) : null}
          <button
            onClick={startRun}
            disabled={!canRun}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2 text-sm font-medium text-primary-foreground shadow-[var(--shadow-indigo)] transition-colors hover:bg-[rgb(var(--ce-indigo-500))] disabled:opacity-40 disabled:hover:bg-primary"
          >
            {running ? "Running..." : "Run"}
            {!running ? <ArrowRight size={14} /> : null}
          </button>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <strong>Run failed:</strong> {error}
        </div>
      ) : null}

      {(running || events.length > 0) && (
        <section className="space-y-3 border-t border-border pt-4">
          <div className="flex items-center justify-between">
            <h3 className="ce-label">
              {running ? "Live execution" : "Run output"}
              {runId ? (
                <span className="ml-3 font-mono text-muted-foreground">#{runId}</span>
              ) : null}
            </h3>
            {completedRunId ? (
              <a
                href={`/runs/${completedRunId}`}
                className="text-xs text-primary underline-offset-4 hover:underline"
              >
                View full run →
              </a>
            ) : null}
          </div>

          {Object.values(traces).map((t) => (
            <details key={t.agent_key} open className="rounded-xl border border-border bg-card">
              <summary className="flex cursor-pointer items-center justify-between p-3">
                <span className="font-mono text-sm text-primary">{t.agent_key}</span>
                <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
                  {t.cost_usd ? `$${t.cost_usd.toFixed(4)}` : ""}
                  {t.input_tokens ? ` ${t.input_tokens}↓` : ""}
                  {t.output_tokens ? ` ${t.output_tokens}↑` : ""}
                </span>
              </summary>
              <div className="px-4 pb-4">
                <pre className="whitespace-pre-wrap font-sans text-xs leading-relaxed text-foreground">
                  {t.text || <span className="italic text-muted-foreground">(no output yet)</span>}
                </pre>
              </div>
            </details>
          ))}

          {synthesis ? (
            <div className="rounded-xl border border-primary/40 bg-primary/5 p-4">
              <div className="ce-eyebrow mb-2">Synthesis</div>
              <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground">
                {synthesis}
              </pre>
            </div>
          ) : null}

          {running ? (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-primary" />
              Running... {events.length} events received
            </div>
          ) : null}
        </section>
      )}
    </div>
  );
}
