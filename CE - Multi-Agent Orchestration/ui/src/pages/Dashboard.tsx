import { useEffect, useState } from 'react'
import { useAgentStore } from '../stores/agentStore'
import { useProtocolStore } from '../stores/protocolStore'
import { useTeamStore } from '../stores/teamStore'
import { useRunStore } from '../stores/runStore'
import { useNavigate } from 'react-router-dom'

export default function Dashboard() {
  const { agents, fetch: fetchAgents } = useAgentStore()
  const { protocols, fetch: fetchProtocols } = useProtocolStore()
  const { currentTeamKeys } = useTeamStore()
  const { runs, fetch: fetchRuns } = useRunStore()
  const navigate = useNavigate()
  const [selectedProtocol, setSelectedProtocol] = useState<string>('')
  const [question, setQuestion] = useState('')

  useEffect(() => { fetchAgents(); fetchProtocols(); fetchRuns() }, [fetchAgents, fetchProtocols, fetchRuns])

  const proto = protocols.find((p) => p.key === selectedProtocol)

  return (
    <div className="max-w-4xl">
      <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-4">Overview</p>
      <h2 className="text-2xl font-semibold text-text mb-6">Dashboard</h2>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="Agents" value={agents.length} onClick={() => navigate('/agents')} />
        <StatCard label="Protocols" value={protocols.length} onClick={() => navigate('/protocols')} />
        <StatCard label="Team Size" value={currentTeamKeys.length} onClick={() => navigate('/teams')} />
        <StatCard label="Past Runs" value={runs.length} onClick={() => navigate('/runs')} />
      </div>

      {/* Quick run */}
      <div className="bg-card border border-border rounded-xl p-6 mb-8">
        <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-4">Quick Run</p>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-xs text-text-muted mb-1 block">Protocol</label>
            <select
              value={selectedProtocol}
              onChange={(e) => setSelectedProtocol(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-white border border-border text-sm text-text focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">Select a protocol...</option>
              {protocols.map((p) => (
                <option key={p.key} value={p.key}>{p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-text-muted mb-1 block">Team</label>
            <p className="px-3 py-2 text-sm text-text">
              {currentTeamKeys.length > 0
                ? `${currentTeamKeys.length} agents selected`
                : <span className="text-text-muted">No team selected</span>
              }
            </p>
          </div>
        </div>

        <div className="mb-4">
          <label className="text-xs text-text-muted mb-1 block">Question</label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What strategic question should the team analyze?"
            rows={3}
            className="w-full px-3 py-2 rounded-lg bg-white border border-border text-sm text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary resize-none"
          />
        </div>

        {proto && (
          <div className="flex items-center gap-4 text-xs text-text-muted mb-4">
            <span>Cost tier: <strong className="text-text">{proto.cost_tier}</strong></span>
            <span>Agents: <strong className="text-text">{proto.min_agents}+</strong></span>
            {proto.supports_rounds && <span>Multi-round</span>}
          </div>
        )}

        <button
          disabled={!selectedProtocol || !question || currentTeamKeys.length === 0}
          onClick={() => navigate('/run')}
          className="px-6 py-2.5 rounded-lg text-sm font-medium bg-primary text-white hover:bg-primary-hover shadow-lg shadow-primary/20 transition disabled:opacity-50"
        >
          Run Protocol
        </button>
      </div>

      {/* Recent runs */}
      {runs.length > 0 && (
        <>
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-4">Recent Runs</p>
          <div className="bg-card border border-border rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-2 text-xs font-bold tracking-wider uppercase text-text-muted">Protocol</th>
                  <th className="text-left px-4 py-2 text-xs font-bold tracking-wider uppercase text-text-muted">Status</th>
                  <th className="text-right px-4 py-2 text-xs font-bold tracking-wider uppercase text-text-muted">Cost</th>
                </tr>
              </thead>
              <tbody>
                {runs.slice(0, 5).map((run) => (
                  <tr key={run.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-2 text-text">{run.protocol_key || run.type}</td>
                    <td className="px-4 py-2">
                      <StatusBadge status={run.status} />
                    </td>
                    <td className="px-4 py-2 text-right text-text-muted">${run.cost_usd.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}

function StatCard({ label, value, onClick }: { label: string; value: number; onClick: () => void }) {
  return (
    <button onClick={onClick} className="bg-card border border-border rounded-xl p-4 text-left hover:border-primary/30 transition">
      <p className="text-xs font-bold tracking-wider uppercase text-text-muted">{label}</p>
      <p className="text-2xl font-semibold text-text mt-1">{value}</p>
    </button>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-600 border-gray-200',
    running: 'bg-blue-50 text-blue-600 border-blue-200',
    completed: 'bg-green-50 text-green-600 border-green-200',
    failed: 'bg-red-50 text-red-600 border-red-200',
  }
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium border ${styles[status] || styles.pending}`}>
      {status}
    </span>
  )
}
