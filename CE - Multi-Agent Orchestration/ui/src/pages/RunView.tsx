import { useEffect, useState } from 'react'
import type { ToolCallEvent } from '../types'
import { useProtocolStore } from '../stores/protocolStore'
import { useTeamStore } from '../stores/teamStore'
import { useAgentStore } from '../stores/agentStore'
import { useRunStream } from '../hooks/useRunStream'

export default function RunView() {
  const { protocols, fetch: fetchProtocols } = useProtocolStore()
  const { currentTeamKeys } = useTeamStore()
  const { agents: allAgents, fetch: fetchAgents } = useAgentStore()
  const stream = useRunStream()

  const [protocolKey, setProtocolKey] = useState('')
  const [question, setQuestion] = useState('')
  const [rounds, setRounds] = useState<number>(3)
  const [toolsEnabled, setToolsEnabled] = useState(true)

  useEffect(() => { fetchProtocols(); fetchAgents() }, [fetchProtocols, fetchAgents])

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

          {/* Running indicator */}
          {isActive && stream.outputs.length === 0 && stream.toolCalls.length === 0 && (
            <div className="bg-card border border-border rounded-xl p-8 text-center mb-4">
              <div className="inline-block w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-sm text-text-muted">Agents are thinking...</p>
              <p className="text-xs text-text-muted mt-1">This may take several minutes depending on the protocol</p>
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
