import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useRunStore } from '../stores/runStore'

export default function RunHistory() {
  const { runs, loading, fetch: fetchRuns } = useRunStore()
  const [filterProtocol, setFilterProtocol] = useState('')
  const [filterStatus, setFilterStatus] = useState('')

  useEffect(() => { fetchRuns() }, [fetchRuns])

  const protocolKeys = [...new Set(runs.map((r) => r.protocol_key).filter(Boolean))].sort()
  const statuses = [...new Set(runs.map((r) => r.status))].sort()

  const filtered = runs.filter((r) => {
    if (filterProtocol && r.protocol_key !== filterProtocol) return false
    if (filterStatus && r.status !== filterStatus) return false
    return true
  })

  return (
    <div className="max-w-5xl">
      <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-4">History</p>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <select
          value={filterProtocol}
          onChange={(e) => setFilterProtocol(e.target.value)}
          className="px-3 py-2 rounded-lg bg-white border border-border text-sm text-text focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="">All protocols</option>
          {protocolKeys.map((k) => (
            <option key={k} value={k}>{k}</option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="px-3 py-2 rounded-lg bg-white border border-border text-sm text-text focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="">All statuses</option>
          {statuses.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        {(filterProtocol || filterStatus) && (
          <button
            onClick={() => { setFilterProtocol(''); setFilterStatus('') }}
            className="px-3 py-2 rounded-lg text-xs font-medium text-text-muted border border-border hover:bg-elevated transition"
          >
            Clear filters
          </button>
        )}
        <span className="flex items-center text-xs text-text-muted ml-auto">
          {filtered.length} run{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {loading ? (
        <p className="text-sm text-text-muted">Loading...</p>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-text-muted">
          {runs.length === 0
            ? 'No runs yet. Go to the Run page to execute a protocol.'
            : 'No runs match the selected filters.'}
        </p>
      ) : (
        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left px-4 py-2 text-xs font-bold tracking-wider uppercase text-text-muted">ID</th>
                <th className="text-left px-4 py-2 text-xs font-bold tracking-wider uppercase text-text-muted">Type</th>
                <th className="text-left px-4 py-2 text-xs font-bold tracking-wider uppercase text-text-muted">Protocol</th>
                <th className="text-left px-4 py-2 text-xs font-bold tracking-wider uppercase text-text-muted">Question</th>
                <th className="text-left px-4 py-2 text-xs font-bold tracking-wider uppercase text-text-muted">Status</th>
                <th className="text-left px-4 py-2 text-xs font-bold tracking-wider uppercase text-text-muted">Started</th>
                <th className="text-right px-4 py-2 text-xs font-bold tracking-wider uppercase text-text-muted">Cost</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((run) => (
                <tr key={run.id} className="border-b border-border last:border-0 hover:bg-elevated/50 transition">
                  <td className="px-4 py-2">
                    <Link to={`/runs/${run.id}`} className="text-primary hover:underline font-medium">
                      #{run.id}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-text">{run.type}</td>
                  <td className="px-4 py-2 text-text">{run.protocol_key || '\u2014'}</td>
                  <td className="px-4 py-2 text-text truncate max-w-xs" title={run.question}>{run.question}</td>
                  <td className="px-4 py-2">
                    <StatusBadge status={run.status} />
                  </td>
                  <td className="px-4 py-2 text-xs text-text-muted">
                    {run.started_at ? new Date(run.started_at).toLocaleString() : '\u2014'}
                  </td>
                  <td className="px-4 py-2 text-right text-text-muted">${run.cost_usd.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
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
