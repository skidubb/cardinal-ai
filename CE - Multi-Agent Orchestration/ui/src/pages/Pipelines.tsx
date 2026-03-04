import { useEffect, useState } from 'react'
import { useProtocolStore } from '../stores/protocolStore'
import { api } from '../api'
import type { Pipeline } from '../types'

interface StepDraft {
  protocol_key: string
  question_template: string
  rounds: number | null
  thinking_model: string
  orchestration_model: string
  output_passthrough: boolean
  no_tools: boolean
}

function emptyStep(): StepDraft {
  return {
    protocol_key: '',
    question_template: '',
    rounds: null,
    thinking_model: 'claude-opus-4-6',
    orchestration_model: 'claude-haiku-4-5-20251001',
    output_passthrough: true,
    no_tools: false,
  }
}

export default function Pipelines() {
  const { protocols, fetch: fetchProtocols } = useProtocolStore()
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [name, setName] = useState('Untitled Pipeline')
  const [steps, setSteps] = useState<StepDraft[]>([emptyStep()])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [deleting, setDeleting] = useState<number | null>(null)

  useEffect(() => { fetchProtocols(); loadPipelines() }, [fetchProtocols])

  const loadPipelines = async () => {
    try {
      const list = await api.pipelines.list()
      setPipelines(list)
    } catch { /* ignore */ }
  }

  const updateStep = (i: number, patch: Partial<StepDraft>) => {
    setSteps((prev) => prev.map((s, j) => j === i ? { ...s, ...patch } : s))
  }

  const removeStep = (i: number) => {
    setSteps((prev) => prev.filter((_, j) => j !== i))
  }

  const addStep = (afterIndex: number) => {
    setSteps((prev) => [...prev.slice(0, afterIndex + 1), emptyStep(), ...prev.slice(afterIndex + 1)])
  }

  const handleSave = async () => {
    const valid = steps.every((s) => s.protocol_key && s.question_template)
    if (!valid) return
    setSaving(true)
    try {
      await api.pipelines.create({
        name,
        steps: steps.map((s, i) => ({
          order: i,
          protocol_key: s.protocol_key,
          question_template: s.question_template,
          rounds: s.rounds,
          thinking_model: s.thinking_model,
          orchestration_model: s.orchestration_model,
          output_passthrough: s.output_passthrough,
          no_tools: s.no_tools,
        })),
      } as Parameters<typeof api.pipelines.create>[0])
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
      loadPipelines()
    } finally {
      setSaving(false)
    }
  }

  // Validation
  const step1HasPrevOutput = steps.length > 0 && steps[0].question_template.includes('{prev_output}')

  return (
    <div className="max-w-3xl">
      <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-4">Pipeline Builder</p>

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="text-lg font-semibold text-text bg-transparent border-b border-transparent hover:border-border focus:border-primary focus:outline-none px-1 py-0.5 transition"
        />
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={saving || steps.length === 0}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-white hover:bg-primary-hover shadow-lg shadow-primary/20 transition disabled:opacity-50"
          >
            {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Pipeline'}
          </button>
        </div>
      </div>

      {step1HasPrevOutput && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-600 mb-4">
          Step 1 cannot use &#123;prev_output&#125; — there is no previous step.
        </div>
      )}

      {/* Step cards */}
      <div className="space-y-3">
        {steps.map((step, i) => {
          const proto = protocols.find((p) => p.key === step.protocol_key)
          return (
            <div key={i}>
              <div className="bg-card border border-border rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="flex items-center gap-2">
                    <span className="w-7 h-7 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center">
                      {i + 1}
                    </span>
                    <span className="text-sm font-medium text-text">
                      {proto ? proto.name : 'Select protocol'}
                    </span>
                  </span>
                  {steps.length > 1 && (
                    <button onClick={() => removeStep(i)} className="text-text-muted hover:text-red-500 transition">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </div>

                <select
                  value={step.protocol_key}
                  onChange={(e) => {
                    const key = e.target.value
                    const p = protocols.find(x => x.key === key)
                    updateStep(i, { protocol_key: key, no_tools: p ? !p.tools_enabled : false })
                  }}
                  className="w-full mb-3 px-3 py-2 rounded-lg bg-white border border-border text-sm text-text focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="">Select a protocol...</option>
                  {protocols.map((p) => (
                    <option key={p.key} value={p.key}>{p.name} ({p.problem_types[0] || p.category})</option>
                  ))}
                </select>

                <textarea
                  value={step.question_template}
                  onChange={(e) => updateStep(i, { question_template: e.target.value })}
                  placeholder={i > 0 ? 'Question or prompt... use {prev_output} to reference previous step' : 'Question or prompt...'}
                  rows={2}
                  className="w-full mb-3 px-3 py-2 rounded-lg bg-white border border-border text-sm text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                />

                <div className="flex items-center gap-4 text-xs">
                  {proto?.supports_rounds && (
                    <label className="flex items-center gap-1.5 text-text-muted">
                      Rounds:
                      <input
                        type="number"
                        min={1}
                        max={10}
                        value={step.rounds ?? 3}
                        onChange={(e) => updateStep(i, { rounds: parseInt(e.target.value) || null })}
                        className="w-14 px-2 py-1 rounded border border-border text-text bg-white"
                      />
                    </label>
                  )}
                  <label className="flex items-center gap-1.5 text-text-muted cursor-pointer">
                    <input
                      type="checkbox"
                      checked={step.output_passthrough}
                      onChange={(e) => updateStep(i, { output_passthrough: e.target.checked })}
                      className="rounded border-border"
                    />
                    Pass output to next step
                  </label>
                  <label className="flex items-center gap-1.5 text-text-muted cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!step.no_tools}
                      onChange={(e) => updateStep(i, { no_tools: !e.target.checked })}
                      className="rounded border-border"
                    />
                    Tools
                  </label>
                </div>
              </div>

              {/* Insert button between steps */}
              <div className="flex justify-center py-1">
                <button
                  onClick={() => addStep(i)}
                  className="flex items-center gap-1 px-3 py-1 rounded-full text-xs text-text-muted hover:text-primary hover:bg-primary/5 border border-transparent hover:border-primary/20 transition"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Add step
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {/* Saved pipelines */}
      {pipelines.length > 0 && (
        <>
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted mt-10 mb-4">Saved Pipelines</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {pipelines.map((p) => (
              <div key={p.id} className="bg-card border border-border rounded-xl p-4">
                <div className="flex items-start justify-between">
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-text">{p.name}</h3>
                    <p className="text-xs text-text-muted mt-1">{p.steps?.length || 0} steps</p>
                    {p.description && (
                      <p className="text-xs text-text-muted mt-1">{p.description}</p>
                    )}
                    {p.steps && p.steps.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {p.steps.map((s, i) => (
                          <span key={i} className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-elevated text-text-muted">
                            {i + 1}. {s.protocol_key}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={async () => {
                      setDeleting(p.id)
                      try {
                        await api.pipelines.delete(p.id)
                        loadPipelines()
                      } finally {
                        setDeleting(null)
                      }
                    }}
                    disabled={deleting === p.id}
                    className="shrink-0 ml-2 px-2 py-1 rounded-lg text-xs text-text-muted hover:text-red-500 hover:bg-red-50 border border-transparent hover:border-red-200 transition disabled:opacity-50"
                  >
                    {deleting === p.id ? 'Deleting...' : 'Delete'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
