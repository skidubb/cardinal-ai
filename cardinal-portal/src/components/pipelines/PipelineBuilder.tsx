"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, ArrowDown, ArrowUp, Plus, Trash2, Info } from "lucide-react";
import type { Protocol } from "@/lib/api";

type StepDraft = {
  protocol_key: string;
  rounds: number | null;
  question_template: string;
  output_passthrough: boolean;
  no_tools: boolean;
};

function emptyStep(protocols: Protocol[]): StepDraft {
  return {
    protocol_key:
      protocols.find((p) => p.key === "p04_multi_round_debate")?.key ?? protocols[0]?.key ?? "",
    rounds: null,
    question_template: "",
    output_passthrough: true,
    no_tools: false,
  };
}

export function PipelineBuilder({ protocols }: { protocols: Protocol[] }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [steps, setSteps] = useState<StepDraft[]>(() => [emptyStep(protocols)]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateStep(i: number, patch: Partial<StepDraft>) {
    setSteps((curr) => curr.map((s, idx) => (idx === i ? { ...s, ...patch } : s)));
  }

  function move(i: number, dir: -1 | 1) {
    setSteps((curr) => {
      const j = i + dir;
      if (j < 0 || j >= curr.length) return curr;
      const next = [...curr];
      [next[i], next[j]] = [next[j], next[i]];
      return next;
    });
  }

  function remove(i: number) {
    setSteps((curr) => (curr.length === 1 ? curr : curr.filter((_, idx) => idx !== i)));
  }

  function addStep() {
    setSteps((curr) => [...curr, emptyStep(protocols)]);
  }

  async function save() {
    setError(null);
    if (!name.trim()) {
      setError("Name is required.");
      return;
    }
    if (steps.length === 0) {
      setError("Add at least one step.");
      return;
    }
    if (steps.some((s) => !s.protocol_key)) {
      setError("Every step needs a protocol.");
      return;
    }

    const body = {
      name: name.trim(),
      description: description.trim(),
      steps: steps.map((s) => ({
        protocol_key: s.protocol_key,
        rounds: s.rounds,
        question_template: s.question_template.trim() || null,
        output_passthrough: s.output_passthrough,
        no_tools: s.no_tools,
      })),
    };

    setBusy(true);
    try {
      const resp = await fetch("/api/proxy/pipelines", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(`${resp.status}: ${text.slice(0, 300)}`);
      }
      const created = await resp.json();
      router.push(`/pipelines/${created.id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Identity */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <div>
          <span className="ce-eyebrow">Identity</span>
          <h2 className="mt-1 text-base font-bold tracking-tight">Pipeline info</h2>
        </div>
        <div className="space-y-3">
          <Field label="Name" required>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Market Entry Analysis"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
            />
          </Field>
          <Field label="Description" hint="What does this pipeline do? When would you run it?">
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
              placeholder="Cynefin classifier → TRIZ inversion → Klein premortem. Use for any major market-entry decision."
            />
          </Field>
        </div>
      </section>

      {/* Steps */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <span className="ce-eyebrow">Chain</span>
            <h2 className="mt-1 text-base font-bold tracking-tight">
              Steps{" "}
              <span className="text-sm font-normal text-muted-foreground">({steps.length})</span>
            </h2>
          </div>
        </div>

        <div className="flex items-start gap-3 rounded-xl border border-[rgb(var(--ce-yellow-500))]/30 bg-[rgb(var(--ce-yellow-500))]/5 p-3 text-xs">
          <Info size={14} className="mt-0.5 shrink-0 text-[rgb(var(--ce-yellow-500))]" />
          <div className="text-muted-foreground">
            Each step receives the previous step&apos;s output as context. Use{" "}
            <code className="rounded bg-secondary px-1 font-mono">{`{{previous.output}}`}</code> in
            a question template to reference it explicitly. Leave template empty to use the
            pipeline&apos;s top-level question.
          </div>
        </div>

        <ol className="space-y-3">
          {steps.map((step, i) => {
            const protocol = protocols.find((p) => p.key === step.protocol_key);
            const supportsRounds = (protocol?.max_agents ?? 0) > 1;
            return (
              <li
                key={i}
                className="relative rounded-xl border border-border bg-card p-5"
              >
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                      {i + 1}
                    </span>
                    <span className="ce-label">Step {i + 1}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <IconBtn onClick={() => move(i, -1)} disabled={i === 0} label="Move up">
                      <ArrowUp size={14} />
                    </IconBtn>
                    <IconBtn
                      onClick={() => move(i, 1)}
                      disabled={i === steps.length - 1}
                      label="Move down"
                    >
                      <ArrowDown size={14} />
                    </IconBtn>
                    <IconBtn
                      onClick={() => remove(i)}
                      disabled={steps.length === 1}
                      label="Delete step"
                      tone="destructive"
                    >
                      <Trash2 size={14} />
                    </IconBtn>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <Field label="Protocol">
                    <select
                      value={step.protocol_key}
                      onChange={(e) => updateStep(i, { protocol_key: e.target.value })}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
                    >
                      {protocols.map((p) => (
                        <option key={p.key} value={p.key}>
                          {p.code ?? p.key.split("_")[0].toUpperCase()} — {p.name}
                        </option>
                      ))}
                    </select>
                    {protocol?.description ? (
                      <p className="text-[10px] leading-relaxed text-muted-foreground text-pretty">
                        {protocol.description}
                      </p>
                    ) : null}
                  </Field>

                  {supportsRounds ? (
                    <Field label="Rounds" hint="For multi-round protocols (debate, synthesis)">
                      <input
                        type="number"
                        min={1}
                        max={5}
                        value={step.rounds ?? ""}
                        onChange={(e) =>
                          updateStep(i, {
                            rounds: e.target.value ? Number(e.target.value) : null,
                          })
                        }
                        className="w-24 rounded border border-input bg-background px-2 py-1.5 text-sm tabular-nums text-foreground"
                        placeholder="2"
                      />
                    </Field>
                  ) : (
                    <div />
                  )}
                </div>

                <div className="mt-4 space-y-4">
                  <Field
                    label="Question template"
                    hint={`Optional. Use {{previous.output}} to chain step ${i}'s result. Empty = pipeline question.`}
                  >
                    <textarea
                      value={step.question_template}
                      onChange={(e) => updateStep(i, { question_template: e.target.value })}
                      rows={2}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-xs text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
                      placeholder={
                        i === 0
                          ? "(leave empty to use the pipeline's top-level question)"
                          : "Given this analysis: {{previous.output}}\n\nWhat are the three biggest risks?"
                      }
                    />
                  </Field>

                  <div className="flex flex-wrap gap-4 text-xs">
                    <label className="flex items-center gap-2 text-muted-foreground">
                      <input
                        type="checkbox"
                        checked={step.output_passthrough}
                        onChange={(e) => updateStep(i, { output_passthrough: e.target.checked })}
                        className="h-4 w-4 rounded border-input accent-[rgb(var(--ce-indigo-600))]"
                      />
                      Pass output to next step
                    </label>
                    <label className="flex items-center gap-2 text-muted-foreground">
                      <input
                        type="checkbox"
                        checked={step.no_tools}
                        onChange={(e) => updateStep(i, { no_tools: e.target.checked })}
                        className="h-4 w-4 rounded border-input accent-[rgb(var(--ce-indigo-600))]"
                      />
                      Disable tool use (faster, no external data)
                    </label>
                  </div>
                </div>
              </li>
            );
          })}
        </ol>

        <button
          type="button"
          onClick={addStep}
          className="flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border bg-transparent p-4 text-sm font-medium text-muted-foreground transition-colors hover:border-primary/50 hover:text-primary"
        >
          <Plus size={14} /> Add step
        </button>
      </section>

      {/* Save */}
      <div className="flex items-center justify-between border-t border-border pt-5">
        <div className="text-xs">
          {error ? <span className="text-destructive">{error}</span> : null}
        </div>
        <button
          type="button"
          onClick={save}
          disabled={busy || !name.trim() || steps.length === 0}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2 text-sm font-medium text-primary-foreground shadow-[var(--shadow-indigo)] transition-colors hover:bg-[rgb(var(--ce-indigo-500))] disabled:opacity-40 disabled:hover:bg-primary"
        >
          {busy ? "Saving…" : "Save pipeline"}
          {!busy ? <ArrowRight size={14} /> : null}
        </button>
      </div>
    </div>
  );
}

function Field({
  label,
  required,
  hint,
  children,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="ce-label block">
        {label} {required ? <span className="text-destructive">*</span> : null}
      </label>
      {children}
      {hint ? <div className="text-[10px] leading-relaxed text-muted-foreground">{hint}</div> : null}
    </div>
  );
}

function IconBtn({
  onClick,
  disabled,
  label,
  tone,
  children,
}: {
  onClick: () => void;
  disabled?: boolean;
  label: string;
  tone?: "destructive";
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      className={[
        "rounded-md border border-border p-1.5 text-muted-foreground transition-colors disabled:opacity-30 disabled:cursor-not-allowed",
        tone === "destructive"
          ? "hover:border-destructive/40 hover:bg-destructive/10 hover:text-destructive"
          : "hover:bg-secondary hover:text-foreground",
      ].join(" ")}
    >
      {children}
    </button>
  );
}
