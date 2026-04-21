"use client";

import { useRef, useState } from "react";
import type { Agent, Protocol } from "@/lib/api";
import MemoryBrief from "./MemoryBrief";

type SseEvent = { event: string; data: Record<string, unknown> };

type AgentTrace = {
  agent_key: string;
  text: string;
  model?: string;
  cost_usd?: number;
  input_tokens?: number;
  output_tokens?: number;
};

const COMMON_TEAMS: Array<{ label: string; agents: string[] }> = [
  { label: "Full C-Suite", agents: ["ceo", "cfo", "cto", "cmo", "coo", "cpo", "cro"] },
  { label: "Strategic 3", agents: ["ceo", "cfo", "cto"] },
  { label: "Go-to-market", agents: ["cmo", "cro", "ceo"] },
  { label: "Build & ship", agents: ["cto", "cpo", "ceo"] },
];

export default function RunForm({
  protocols,
  agents,
}: {
  protocols: Protocol[];
  agents: Agent[];
}) {
  const [question, setQuestion] = useState("");
  const [protocolKey, setProtocolKey] = useState<string>(
    protocols.find((p) => p.key === "p04_multi_round_debate")?.key ?? protocols[0]?.key ?? "",
  );
  const [agentKeys, setAgentKeys] = useState<string[]>(["ceo", "cfo", "cto"]);
  const [rounds, setRounds] = useState<number>(2);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<SseEvent[]>([]);
  const [traces, setTraces] = useState<Record<string, AgentTrace>>({});
  const [synthesis, setSynthesis] = useState<string>("");
  const [runId, setRunId] = useState<number | null>(null);
  const [completedRunId, setCompletedRunId] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const selectedProtocol = protocols.find((p) => p.key === protocolKey);

  function toggleAgent(key: string) {
    setAgentKeys((curr) => (curr.includes(key) ? curr.filter((k) => k !== key) : [...curr, key]));
  }

  function applyTeam(team: string[]) {
    setAgentKeys(team);
  }

  async function startRun() {
    if (!question.trim() || !protocolKey || agentKeys.length === 0 || running) return;
    setRunning(true);
    setError(null);
    setEvents([]);
    setTraces({});
    setSynthesis("");
    setRunId(null);
    setCompletedRunId(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const resp = await fetch("/api/proxy/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          protocol_key: protocolKey,
          question,
          agent_keys: agentKeys,
          rounds: selectedProtocol?.max_agents && selectedProtocol.max_agents > 0 ? rounds : undefined,
          no_tools: false,
        }),
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

        // Split on SSE message boundary (double newline)
        const messages = buffer.split("\n\n");
        buffer = messages.pop() ?? "";

        for (const raw of messages) {
          if (!raw.trim() || raw.startsWith(":")) continue; // skip heartbeats / blank
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
        setError(String(d.message ?? "Run failed"));
        break;
    }
  }

  function cancel() {
    abortRef.current?.abort();
    setRunning(false);
  }

  // Group agents by category for the picker
  const agentsByCategory: Record<string, Agent[]> = {};
  for (const a of agents) {
    const cat = (a as Agent & { category?: string }).category ?? a.layer ?? "other";
    if (!agentsByCategory[cat]) agentsByCategory[cat] = [];
    agentsByCategory[cat].push(a);
  }
  const categoryOrder = ["executive", "c_suite", "cfo-team", "cto-team", "cmo-team", "cpo-team", "coo-team", "cro-team", "gtm-sales", "gtm-marketing", "direct_report", "functional", "other"];
  const sortedCategories = Object.keys(agentsByCategory).sort(
    (a, b) => (categoryOrder.indexOf(a) >= 0 ? categoryOrder.indexOf(a) : 999) - (categoryOrder.indexOf(b) >= 0 ? categoryOrder.indexOf(b) : 999),
  );

  return (
    <div className="space-y-6">
      {/* Question input */}
      <section className="rounded-xl border border-fuchsia-700/30 bg-gradient-to-br from-fuchsia-950/20 to-violet-950/10 p-5">
        <label className="block text-xs uppercase tracking-wider text-slate-400 mb-2">
          Strategic question
        </label>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. Should we expand into the European market in Q3? What pricing tier maximizes revenue without churn risk?"
          rows={3}
          className="w-full bg-slate-950/60 border border-slate-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-fuchsia-500"
          disabled={running}
        />
        <div className="mt-3">
          <MemoryBrief question={question} />
        </div>
      </section>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Protocol picker */}
        <section className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
          <label className="block text-xs uppercase tracking-wider text-slate-400 mb-2">
            Protocol ({protocols.length} available)
          </label>
          <select
            value={protocolKey}
            onChange={(e) => setProtocolKey(e.target.value)}
            className="w-full bg-slate-950/60 border border-slate-700 rounded-md px-3 py-2 text-sm font-mono"
            disabled={running}
          >
            {protocols.map((p) => (
              <option key={p.key} value={p.key}>
                {p.code ?? p.key.split("_")[0].toUpperCase()} — {p.name} ({p.category})
              </option>
            ))}
          </select>
          {selectedProtocol?.description ? (
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">{selectedProtocol.description}</p>
          ) : null}
          {selectedProtocol && (selectedProtocol.max_agents ?? 0) > 1 ? (
            <div className="mt-3">
              <label className="text-[10px] uppercase tracking-wider text-slate-500">Rounds</label>
              <input
                type="number"
                min={1}
                max={5}
                value={rounds}
                onChange={(e) => setRounds(Number(e.target.value))}
                className="ml-2 w-16 bg-slate-950/60 border border-slate-700 rounded px-2 py-1 text-sm tabular-nums"
                disabled={running}
              />
            </div>
          ) : null}
        </section>

        {/* Agent picker */}
        <section className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs uppercase tracking-wider text-slate-400">
              Agents ({agentKeys.length} selected)
            </label>
            <div className="flex gap-1">
              {COMMON_TEAMS.map((t) => (
                <button
                  key={t.label}
                  type="button"
                  onClick={() => applyTeam(t.agents)}
                  disabled={running}
                  className="text-[10px] px-2 py-0.5 rounded border border-slate-700 hover:bg-slate-800 transition disabled:opacity-50"
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>
          <div className="max-h-60 overflow-y-auto space-y-3 pr-1">
            {sortedCategories.map((cat) => (
              <div key={cat}>
                <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">{cat}</div>
                <div className="flex flex-wrap gap-1">
                  {agentsByCategory[cat].map((a) => (
                    <button
                      key={a.key}
                      type="button"
                      onClick={() => toggleAgent(a.key)}
                      disabled={running}
                      className={`text-xs px-2 py-1 rounded border transition ${
                        agentKeys.includes(a.key)
                          ? "bg-fuchsia-500/20 border-fuchsia-500/40 text-fuchsia-200"
                          : "bg-slate-950/60 border-slate-700 text-slate-300 hover:border-slate-600"
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

      {/* Action row */}
      <div className="flex items-center justify-between">
        <div className="text-xs text-slate-500">
          {selectedProtocol ? (
            <>
              <span className="font-mono">{selectedProtocol.key}</span>
              {" with "}
              <span className="font-mono">{agentKeys.join(", ") || "(no agents)"}</span>
            </>
          ) : null}
        </div>
        <div className="flex gap-3">
          {running ? (
            <button
              onClick={cancel}
              className="rounded-md border border-slate-700 px-4 py-2 text-sm hover:bg-slate-900"
            >
              Cancel
            </button>
          ) : null}
          <button
            onClick={startRun}
            disabled={running || !question.trim() || agentKeys.length === 0 || !protocolKey}
            className="rounded-md bg-fuchsia-600 px-5 py-2 text-sm font-medium hover:bg-fuchsia-500 transition disabled:opacity-40 disabled:hover:bg-fuchsia-600"
          >
            {running ? "Running..." : "Run protocol →"}
          </button>
        </div>
      </div>

      {error ? (
        <div className="rounded-lg border border-rose-700/40 bg-rose-950/20 p-4 text-sm text-rose-200">
          <strong>Run failed:</strong> {error}
        </div>
      ) : null}

      {/* Live execution view */}
      {(running || events.length > 0) && (
        <section className="space-y-3 pt-4 border-t border-slate-900">
          <div className="flex items-center justify-between">
            <h3 className="text-sm uppercase tracking-wider text-slate-400">
              {running ? "Live execution" : "Run output"}
              {runId ? <span className="ml-3 font-mono text-slate-500">#{runId}</span> : null}
            </h3>
            {completedRunId ? (
              <a
                href={`/runs/${completedRunId}`}
                className="text-xs text-fuchsia-400 hover:text-fuchsia-300"
              >
                View full run →
              </a>
            ) : null}
          </div>

          {/* Agent traces, ordered by completion */}
          {Object.values(traces).map((t) => (
            <details
              key={t.agent_key}
              open
              className="rounded-lg border border-slate-800 bg-slate-900/40"
            >
              <summary className="cursor-pointer p-3 flex items-center justify-between">
                <span className="font-mono text-sm text-fuchsia-300">{t.agent_key}</span>
                <span className="text-[10px] text-slate-500 tabular-nums">
                  {t.cost_usd ? `$${t.cost_usd.toFixed(4)}` : ""}
                  {t.input_tokens ? ` ${t.input_tokens}↓` : ""}
                  {t.output_tokens ? ` ${t.output_tokens}↑` : ""}
                </span>
              </summary>
              <div className="px-4 pb-4">
                <pre className="whitespace-pre-wrap text-xs text-slate-200 font-sans leading-relaxed">
                  {t.text || <span className="text-slate-500 italic">(no output yet)</span>}
                </pre>
              </div>
            </details>
          ))}

          {/* Synthesis */}
          {synthesis ? (
            <div className="rounded-lg border border-fuchsia-700/40 bg-fuchsia-950/10 p-4">
              <div className="text-[10px] uppercase tracking-wider text-fuchsia-400 mb-2">Synthesis</div>
              <pre className="whitespace-pre-wrap text-sm text-slate-100 font-sans leading-relaxed">
                {synthesis}
              </pre>
            </div>
          ) : null}

          {/* Status pulse */}
          {running ? (
            <div className="text-xs text-slate-500 flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-fuchsia-500 animate-pulse" />
              Running... {events.length} events received
            </div>
          ) : null}
        </section>
      )}
    </div>
  );
}
