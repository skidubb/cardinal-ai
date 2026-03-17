import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { ToolCallEvent } from '../types'
import { useProtocolStore } from '../stores/protocolStore'
import { useTeamStore } from '../stores/teamStore'
import { useAgentStore } from '../stores/agentStore'
import { useRunStream, type CostSummary, type AgentOutputEvent, type JudgeVerdict } from '../hooks/useRunStream'
import { ProtocolReport } from '../components/ProtocolReport'
import type { ProtocolReportData } from '../components/ProtocolReport'
import { getApiKey } from '../api'

export default function RunView() {
  const { protocols, fetch: fetchProtocols } = useProtocolStore()
  const { currentTeamKeys } = useTeamStore()
  const { agents: allAgents, fetch: fetchAgents } = useAgentStore()
  const stream = useRunStream()

  const [protocolKey, setProtocolKey] = useState('')
  const [question, setQuestion] = useState('')
  const [rounds, setRounds] = useState<number>(3)
  const [toolsEnabled, setToolsEnabled] = useState(true)

  const [searchParams] = useSearchParams()

  useEffect(() => {
    fetchProtocols()
    fetchAgents()
  }, [fetchProtocols, fetchAgents])

  useEffect(() => {
    const preselect = searchParams.get('protocol')
    if (preselect && protocols.length > 0 && !protocolKey) {
      setProtocolKey(preselect)
    }
  }, [searchParams, protocols, protocolKey])

  // Auto-start pipeline run from Pipelines page
  useEffect(() => {
    if (searchParams.get('mode') !== 'pipeline') return
    const raw = sessionStorage.getItem('pipeline_run')
    if (!raw) return
    sessionStorage.removeItem('pipeline_run')
    try {
      const config = JSON.parse(raw)
      if (config.question && config.steps?.length > 0 && config.agent_keys?.length > 0) {
        setQuestion(config.question)
        stream.startPipelineRun(config)
      }
    } catch { /* ignore bad data */ }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const proto = protocols.find(p => p.key === protocolKey)
  const teamAgents = allAgents.filter(a => currentTeamKeys.includes(a.key))

  const canRun = protocolKey && question && currentTeamKeys.length > 0 && stream.status === 'idle'

  const handleRun = () => {
    if (!canRun) return
    stream.startProtocolRun({
      protocol_key: protocolKey,
      question,
      agent_keys: currentTeamKeys,
      rounds: proto?.supports_rounds ? rounds : undefined,
      no_tools: !toolsEnabled,
    })
  }

  const isActive = stream.status === 'running' || stream.status === 'starting'

  return (
    <div className="max-w-5xl">
      <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-4">Execute</p>

      {/* Config panel — only when idle */}
      {stream.status === 'idle' && (
        <div className="bg-card border border-border rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold text-text mb-4">Run Protocol</h2>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-xs text-text-muted mb-1 block">Protocol</label>
              <select
                value={protocolKey}
                onChange={e => {
                  const key = e.target.value
                  setProtocolKey(key)
                  const p = protocols.find(x => x.key === key)
                  setToolsEnabled(p?.tools_enabled ?? true)
                }}
                className="w-full px-3 py-2 rounded-lg bg-white border border-border text-sm text-text focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">Select a protocol...</option>
                {protocols.map(p => (
                  <option key={p.key} value={p.key}>{p.name} ({p.problem_types[0] || p.category})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-text-muted mb-1 block">Team</label>
              <p className="px-3 py-2 text-sm text-text">
                {teamAgents.length > 0
                  ? `${teamAgents.length} agents: ${teamAgents.map(a => a.name).join(', ')}`
                  : <span className="text-text-muted">No team selected — add agents from the Registry</span>
                }
              </p>
            </div>
          </div>

          <div className="flex items-center gap-6 mb-4">
            {proto?.supports_rounds && (
              <div>
                <label className="text-xs text-text-muted mb-1 block">Rounds</label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={rounds}
                  onChange={e => setRounds(parseInt(e.target.value) || 3)}
                  className="w-20 px-3 py-2 rounded-lg bg-white border border-border text-sm text-text"
                />
              </div>
            )}
            <label className="flex items-center gap-2 text-sm text-text cursor-pointer">
              <input
                type="checkbox"
                checked={toolsEnabled}
                onChange={e => setToolsEnabled(e.target.checked)}
                className="rounded border-border"
              />
              Enable tools
            </label>
          </div>

          <div className="mb-4">
            <label className="text-xs text-text-muted mb-1 block">Question</label>
            <textarea
              value={question}
              onChange={e => setQuestion(e.target.value)}
              placeholder="What strategic question should the team analyze?"
              rows={3}
              className="w-full px-3 py-2 rounded-lg bg-white border border-border text-sm text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary resize-none"
            />
          </div>

          {proto && (
            <div className="flex items-center gap-4 text-xs text-text-muted mb-4">
              <span>Cost tier: <strong className="text-text">{proto.cost_tier}</strong></span>
              <span>Min agents: <strong className="text-text">{proto.min_agents}</strong></span>
              {proto.supports_rounds && <span>Multi-round</span>}
            </div>
          )}

          <button
            onClick={handleRun}
            disabled={!canRun}
            className="px-6 py-2.5 rounded-lg text-sm font-medium bg-primary text-white hover:bg-primary-hover shadow-lg shadow-primary/20 transition disabled:opacity-50"
          >
            Run Protocol
          </button>
        </div>
      )}

      {/* Live run view */}
      {stream.status !== 'idle' && (
        <div>
          {/* Status header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <StatusIndicator status={stream.status} />
              <div>
                <h2 className="text-lg font-semibold text-text">
                  {proto?.name || protocolKey}
                </h2>
                <p className="text-xs text-text-muted">{question}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {stream.elapsedSeconds !== null && (
                <span className="text-xs text-text-muted">{stream.elapsedSeconds}s</span>
              )}
              {isActive && (
                <button
                  onClick={stream.abort}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium text-red-600 border border-red-200 hover:bg-red-50 transition"
                >
                  Abort
                </button>
              )}
              {stream.status === 'completed' && (
                <button
                  onClick={() => window.location.reload()}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium text-primary border border-primary/20 hover:bg-primary/5 transition"
                >
                  New Run
                </button>
              )}
            </div>
          </div>

          {/* Error */}
          {stream.error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-4">
              <p className="text-sm font-medium text-red-700">Error</p>
              <p className="text-xs text-red-600 mt-1 font-mono whitespace-pre-wrap">{stream.error}</p>
            </div>
          )}

          {/* Agent roster */}
          {stream.agents.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-6">
              {stream.agents.map(a => (
                <span key={a.key} className="px-2.5 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary border border-primary/20">
                  {a.name}
                </span>
              ))}
            </div>
          )}

          {/* Live stage progress */}
          {isActive && stream.currentStage && (
            <div className="flex items-center gap-2.5 mb-4 px-4 py-2.5 bg-blue-50 border border-blue-200 rounded-lg">
              <span className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin flex-shrink-0" />
              <span className="text-sm font-medium text-blue-700">{stream.currentStage}</span>
            </div>
          )}

          {/* Active agents indicator */}
          {isActive && (
            <div className="bg-card border border-border rounded-xl p-4 mb-4">
              {stream.activeAgents.length > 0 ? (
                <div className="space-y-2">
                  {stream.activeAgents.map(name => (
                    <div key={name} className="flex items-center gap-2 text-sm">
                      <span className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin flex-shrink-0" />
                      <span className="font-medium text-text">{name}</span>
                      <span className="text-xs text-text-muted">thinking...</span>
                    </div>
                  ))}
                </div>
              ) : stream.outputs.length === 0 && stream.toolCalls.length === 0 ? (
                <div className="text-center py-4">
                  <div className="inline-block w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3" />
                  <p className="text-sm text-text-muted">Initializing agents...</p>
                </div>
              ) : null}
            </div>
          )}

          {/* Tool Activity */}
          {stream.toolCalls.length > 0 && (
            <ToolActivityPanel toolCalls={stream.toolCalls} />
          )}

          {/* Agent outputs */}
          <div className="space-y-4">
            {stream.outputs.map((out, i) => (
              <div key={i} className="bg-card border border-border rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-elevated text-text-muted">
                    {out.agent_name || out.agent_key}
                  </span>
                  {out.round !== undefined && (
                    <span className="text-xs text-text-muted">Round {out.round}</span>
                  )}
                  {out.step !== undefined && (
                    <span className="text-xs text-text-muted">Step {out.step + 1}</span>
                  )}
                </div>
                <div className="text-sm text-text whitespace-pre-wrap font-mono leading-relaxed max-h-96 overflow-y-auto">
                  {out.text}
                </div>
                <CopyButton text={out.text} />
              </div>
            ))}
          </div>

          {/* Synthesis */}
          {stream.synthesis && (
            <div className="mt-6 bg-primary/5 border border-primary/20 rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold tracking-wider uppercase text-primary">Synthesis</span>
                <CopyButton text={stream.synthesis} />
              </div>
              <div className="text-sm text-text whitespace-pre-wrap leading-relaxed">
                {stream.synthesis}
              </div>
            </div>
          )}

          {/* Judge verdict */}
          {stream.judgeVerdict && (
            <JudgeVerdictCard verdict={stream.judgeVerdict} />
          )}

          {/* Structured Protocol Report — primary content when available */}
          {stream.status === 'completed' && stream.protocolReport && (
            <div className="mt-6">
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-bold tracking-wider uppercase text-text-muted">Protocol Report</p>
                {stream.runId && (
                  <a
                    href={`/share/${stream.runId}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary hover:underline"
                  >
                    Share Report
                  </a>
                )}
              </div>
              <ProtocolReport report={stream.protocolReport as ProtocolReportData} />
            </div>
          )}

          {/* Cost breakdown */}
          {stream.status === 'completed' && stream.cost && (
            <CostBreakdown cost={stream.cost} />
          )}

          {/* Download report */}
          {stream.status === 'completed' && (
            <div className="mt-4 flex gap-3">
              <button
                onClick={() => downloadReport({
                  protocolName: proto?.name || protocolKey,
                  protocolKey,
                  question,
                  agents: stream.agents,
                  outputs: stream.outputs,
                  toolCalls: stream.toolCalls,
                  synthesis: stream.synthesis,
                  judgeVerdict: stream.judgeVerdict,
                  cost: stream.cost,
                  traceId: stream.traceId,
                  elapsedSeconds: stream.elapsedSeconds,
                })}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-elevated border border-border text-text hover:bg-white transition"
              >
                Download Report (.md)
              </button>
              {stream.runId && (
                <button
                  onClick={async () => {
                    const apiKey = getApiKey()
                    const res = await fetch(`/api/reports/${stream.runId}/pdf`, {
                      headers: apiKey ? { 'X-API-Key': apiKey } : {},
                    })
                    if (!res.ok) {
                      alert(`PDF generation failed: ${res.status} ${res.statusText}`)
                      return
                    }
                    const blob = await res.blob()
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = `run-${protocolKey}-${stream.runId}.pdf`
                    a.click()
                    URL.revokeObjectURL(url)
                  }}
                  className="px-4 py-2 rounded-lg text-sm font-medium bg-elevated border border-border text-text hover:bg-white transition"
                >
                  Download PDF
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function StatusIndicator({ status }: { status: string }) {
  const config: Record<string, { color: string; label: string; pulse: boolean }> = {
    starting: { color: 'bg-blue-500', label: 'Starting', pulse: true },
    running: { color: 'bg-blue-500', label: 'Running', pulse: true },
    completed: { color: 'bg-green-500', label: 'Completed', pulse: false },
    failed: { color: 'bg-red-500', label: 'Failed', pulse: false },
  }
  const c = config[status] || config.starting
  return (
    <span className="flex items-center gap-1.5">
      <span className={`w-2.5 h-2.5 rounded-full ${c.color} ${c.pulse ? 'animate-pulse' : ''}`} />
      <span className="text-xs font-medium text-text-muted">{c.label}</span>
    </span>
  )
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500) }}
      className="mt-2 text-xs text-text-muted hover:text-primary transition"
    >
      {copied ? 'Copied!' : 'Copy'}
    </button>
  )
}

const TOOL_DOMAIN_COLORS: Record<string, string> = {
  sec_edgar: 'bg-blue-100 text-blue-700 border-blue-200',
  brave_search: 'bg-orange-100 text-orange-700 border-orange-200',
  notion: 'bg-gray-100 text-gray-700 border-gray-200',
  pinecone: 'bg-teal-100 text-teal-700 border-teal-200',
  github: 'bg-purple-100 text-purple-700 border-purple-200',
}

function toolBadgeColor(toolName: string): string {
  for (const [domain, cls] of Object.entries(TOOL_DOMAIN_COLORS)) {
    if (toolName.toLowerCase().includes(domain)) return cls
  }
  return 'bg-elevated text-text-muted border-border'
}

function CostBreakdown({ cost }: { cost: CostSummary }) {
  return (
    <div className="mt-6 bg-card border border-border rounded-xl p-5">
      <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-3">Cost Breakdown</p>
      <div className="flex items-baseline gap-2 mb-4">
        <span className="text-2xl font-semibold text-text">${cost.total_usd.toFixed(4)}</span>
        <span className="text-xs text-text-muted">{cost.calls} API calls</span>
      </div>

      {Object.keys(cost.by_model).length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-medium text-text-muted mb-2">By Model</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-text-muted border-b border-border">
                  <th className="pb-1.5 pr-4">Model</th>
                  <th className="pb-1.5 pr-4 text-right">Calls</th>
                  <th className="pb-1.5 pr-4 text-right">Input</th>
                  <th className="pb-1.5 pr-4 text-right">Output</th>
                  <th className="pb-1.5 text-right">Cost</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(cost.by_model).map(([model, m]) => (
                  <tr key={model} className="border-b border-border/50">
                    <td className="py-1.5 pr-4 font-mono text-text">{model}</td>
                    <td className="py-1.5 pr-4 text-right text-text-muted">{m.calls}</td>
                    <td className="py-1.5 pr-4 text-right text-text-muted">{m.input_tokens.toLocaleString()}</td>
                    <td className="py-1.5 pr-4 text-right text-text-muted">{m.output_tokens.toLocaleString()}</td>
                    <td className="py-1.5 text-right font-medium text-text">${m.cost_usd.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {Object.keys(cost.by_agent).length > 0 && (
        <div>
          <p className="text-xs font-medium text-text-muted mb-2">By Agent</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-text-muted border-b border-border">
                  <th className="pb-1.5 pr-4">Agent</th>
                  <th className="pb-1.5 pr-4">Model</th>
                  <th className="pb-1.5 pr-4 text-right">Calls</th>
                  <th className="pb-1.5 pr-4 text-right">Input</th>
                  <th className="pb-1.5 pr-4 text-right">Output</th>
                  <th className="pb-1.5 text-right">Cost</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(cost.by_agent).map(([agent, a]) => (
                  <tr key={agent} className="border-b border-border/50">
                    <td className="py-1.5 pr-4 font-medium text-text">{agent}</td>
                    <td className="py-1.5 pr-4 font-mono text-text-muted">{a.primary_model}</td>
                    <td className="py-1.5 pr-4 text-right text-text-muted">{a.calls}</td>
                    <td className="py-1.5 pr-4 text-right text-text-muted">{a.input_tokens.toLocaleString()}</td>
                    <td className="py-1.5 pr-4 text-right text-text-muted">{a.output_tokens.toLocaleString()}</td>
                    <td className="py-1.5 text-right font-medium text-text">${a.cost_usd.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function scoreColor(score: number): string {
  if (score >= 4) return 'bg-green-100 text-green-700 border-green-200'
  if (score >= 3) return 'bg-yellow-100 text-yellow-700 border-yellow-200'
  return 'bg-red-100 text-red-700 border-red-200'
}

function JudgeVerdictCard({ verdict }: { verdict: JudgeVerdict }) {
  const dimensions = [
    { label: 'Completeness', score: verdict.completeness },
    { label: 'Consistency', score: verdict.consistency },
    { label: 'Actionability', score: verdict.actionability },
    { label: 'Overall', score: verdict.overall },
  ]
  const isAccept = verdict.recommendation === 'accept'

  return (
    <div className="mt-6 bg-card border border-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-bold tracking-wider uppercase text-text-muted">Quality Judge</span>
        <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${isAccept ? 'bg-green-100 text-green-700 border-green-200' : 'bg-amber-100 text-amber-700 border-amber-200'}`}>
          {isAccept ? 'Accepted' : 'Revise'}
        </span>
      </div>
      <div className="flex gap-3 mb-3">
        {dimensions.map(d => (
          <div key={d.label} className="flex flex-col items-center gap-1">
            <span className={`w-10 h-10 rounded-lg border flex items-center justify-center text-sm font-bold ${scoreColor(d.score)}`}>
              {d.score}
            </span>
            <span className="text-[10px] text-text-muted">{d.label}</span>
          </div>
        ))}
      </div>
      {verdict.flags.length > 0 && (
        <div className="space-y-1">
          {verdict.flags.map((flag, i) => (
            <div key={i} className="flex items-start gap-1.5 text-xs text-amber-700">
              <span className="mt-0.5 flex-shrink-0">&#9888;</span>
              <span>{flag}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function downloadReport(data: {
  protocolName: string
  protocolKey: string
  question: string
  agents: { key: string; name: string }[]
  outputs: AgentOutputEvent[]
  toolCalls: ToolCallEvent[]
  synthesis: string
  judgeVerdict: JudgeVerdict | null
  cost: CostSummary | null
  traceId: string | null
  elapsedSeconds: number | null
}) {
  const ts = new Date().toISOString()
  const lines: string[] = [
    `# Protocol Run Report`,
    '',
    `**Protocol:** ${data.protocolName} (\`${data.protocolKey}\`)`,
    `**Question:** ${data.question}`,
    `**Timestamp:** ${ts}`,
    `**Duration:** ${data.elapsedSeconds != null ? `${data.elapsedSeconds}s` : 'N/A'}`,
    `**Agents:** ${data.agents.map(a => a.name).join(', ')}`,
    '',
  ]

  if (data.traceId) {
    lines.push(`**Langfuse Trace:** [View in Langfuse](https://us.cloud.langfuse.com/trace/${data.traceId})`, '')
  }

  lines.push('---', '', '## Agent Outputs', '')
  for (const out of data.outputs) {
    const label = out.agent_name || out.agent_key
    const meta = [out.round !== undefined && `Round ${out.round}`, out.step !== undefined && `Step ${out.step + 1}`].filter(Boolean).join(' | ')
    lines.push(`### ${label}${meta ? ` (${meta})` : ''}`, '', out.text, '')
  }

  if (data.toolCalls.length > 0) {
    lines.push('---', '', '## Tool Activity', '', `${data.toolCalls.length} tool calls total.`, '')
    const grouped: Record<string, typeof data.toolCalls> = {}
    for (const tc of data.toolCalls) {
      const k = tc.agent_name || 'unknown'
      if (!grouped[k]) grouped[k] = []
      grouped[k].push(tc)
    }
    for (const [agent, calls] of Object.entries(grouped)) {
      lines.push(`**${agent}:**`)
      for (const tc of calls) {
        const ms = tc.elapsed_ms != null ? ` (${Math.round(tc.elapsed_ms)}ms)` : ''
        lines.push(`- \`${tc.tool_name}\`${ms}`)
      }
      lines.push('')
    }
  }

  if (data.synthesis) {
    lines.push('---', '', '## Synthesis', '', data.synthesis, '')
  }

  if (data.judgeVerdict) {
    const v = data.judgeVerdict
    lines.push('---', '', '## Quality Judge', '')
    lines.push(`**Recommendation:** ${v.recommendation === 'accept' ? 'Accept' : 'Revise'}`, '')
    lines.push('| Dimension | Score |', '|-----------|------:|')
    lines.push(`| Completeness | ${v.completeness}/5 |`)
    lines.push(`| Consistency | ${v.consistency}/5 |`)
    lines.push(`| Actionability | ${v.actionability}/5 |`)
    lines.push(`| Overall | ${v.overall}/5 |`)
    lines.push('')
    if (v.flags.length > 0) {
      lines.push('**Flags:**')
      for (const flag of v.flags) {
        lines.push(`- ${flag}`)
      }
      lines.push('')
    }
  }

  if (data.cost) {
    lines.push('---', '', '## Cost Breakdown', '')
    lines.push(`**Total:** $${data.cost.total_usd.toFixed(4)} (${data.cost.calls} calls)`, '')

    if (Object.keys(data.cost.by_model).length > 0) {
      lines.push('### By Model', '', '| Model | Calls | Input Tokens | Output Tokens | Cost |', '|-------|------:|-------------:|--------------:|-----:|')
      for (const [model, m] of Object.entries(data.cost.by_model)) {
        lines.push(`| \`${model}\` | ${m.calls} | ${m.input_tokens.toLocaleString()} | ${m.output_tokens.toLocaleString()} | $${m.cost_usd.toFixed(4)} |`)
      }
      lines.push('')
    }

    if (Object.keys(data.cost.by_agent).length > 0) {
      lines.push('### By Agent', '', '| Agent | Model | Calls | Input | Output | Cost |', '|-------|-------|------:|------:|-------:|-----:|')
      for (const [agent, a] of Object.entries(data.cost.by_agent)) {
        lines.push(`| ${agent} | \`${a.primary_model}\` | ${a.calls} | ${a.input_tokens.toLocaleString()} | ${a.output_tokens.toLocaleString()} | $${a.cost_usd.toFixed(4)} |`)
      }
      lines.push('')
    }
  }

  const blob = new Blob([lines.join('\n')], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `run-${data.protocolKey}-${new Date().toISOString().slice(0, 10)}.md`
  a.click()
  URL.revokeObjectURL(url)
}

function ToolActivityPanel({ toolCalls }: { toolCalls: ToolCallEvent[] }) {
  const [collapsed, setCollapsed] = useState(false)

  // Group by agent_name
  const grouped: Record<string, ToolCallEvent[]> = {}
  for (const tc of toolCalls) {
    const key = tc.agent_name || 'unknown'
    if (!grouped[key]) grouped[key] = []
    grouped[key].push(tc)
  }

  return (
    <div className="bg-card border border-border rounded-xl mb-4 overflow-hidden">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-elevated/50 transition"
      >
        <span className="text-xs font-bold tracking-wider uppercase text-text-muted">
          Tool Activity ({toolCalls.length})
        </span>
        <span className="text-xs text-text-muted">{collapsed ? '+' : '-'}</span>
      </button>
      {!collapsed && (
        <div className="px-4 pb-4 space-y-3">
          {Object.entries(grouped).map(([agentName, calls]) => (
            <div key={agentName}>
              <p className="text-xs font-medium text-text-muted mb-1.5">{agentName}</p>
              <div className="space-y-1.5">
                {calls.map((tc, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    {tc.status === 'running' ? (
                      <span className="w-3 h-3 border border-primary border-t-transparent rounded-full animate-spin flex-shrink-0" />
                    ) : (
                      <span className="text-green-500 flex-shrink-0">&#10003;</span>
                    )}
                    <span className={`px-1.5 py-0.5 rounded border text-[10px] font-medium ${toolBadgeColor(tc.tool_name)}`}>
                      {tc.tool_name}
                    </span>
                    {tc.elapsed_ms != null && (
                      <span className="text-text-muted">{Math.round(tc.elapsed_ms)}ms</span>
                    )}
                    {tc.result_preview && (
                      <span className="text-text-muted truncate max-w-xs" title={tc.result_preview}>
                        {tc.result_preview.slice(0, 80)}{tc.result_preview.length > 80 ? '...' : ''}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
