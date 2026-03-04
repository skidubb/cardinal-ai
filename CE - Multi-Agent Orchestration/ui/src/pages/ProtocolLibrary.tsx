import { useEffect, useState } from 'react'
import { useProtocolStore } from '../stores/protocolStore'
import type { Protocol } from '../types'

const COST_COLORS: Record<string, string> = {
  low: 'text-green-600 bg-green-50 border-green-200',
  medium: 'text-amber-600 bg-amber-50 border-amber-200',
  high: 'text-red-600 bg-red-50 border-red-200',
}

export default function ProtocolLibrary() {
  const { loading, error, selectedProblemType, searchQuery, fetch, setProblemType, setSearch, filtered, problemTypes } =
    useProtocolStore()
  const [selectedProtocol, setSelectedProtocol] = useState<Protocol | null>(null)

  useEffect(() => { fetch() }, [fetch])

  const protocols = filtered()
  const pts = problemTypes()

  return (
    <div className="flex gap-6 h-full">
      {/* Left column — filter + list */}
      <div className="w-80 shrink-0 flex flex-col">
        <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-4">Protocol Library</p>

        <input
          type="text"
          placeholder="Search protocols..."
          value={searchQuery}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full mb-3 px-3 py-2 rounded-lg bg-white border border-border text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary text-sm"
        />

        <div className="flex flex-wrap gap-1.5 mb-4">
          <button
            onClick={() => setProblemType(null)}
            className={`px-2.5 py-1 rounded-full text-xs font-medium transition ${
              !selectedProblemType
                ? 'bg-primary text-white'
                : 'bg-elevated text-text-muted hover:text-text border border-border'
            }`}
          >
            All ({protocols.length})
          </button>
          {pts.map((pt) => (
            <button
              key={pt}
              onClick={() => setProblemType(pt === selectedProblemType ? null : pt)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium transition ${
                pt === selectedProblemType
                  ? 'bg-primary text-white'
                  : 'bg-elevated text-text-muted hover:text-text border border-border'
              }`}
            >
              {pt}
            </button>
          ))}
        </div>

        {loading && <p className="text-text-muted text-sm">Loading...</p>}
        {error && <p className="text-red-500 text-sm">Error: {error}</p>}

        <div className="flex-1 overflow-auto space-y-1">
          {protocols.map((p) => (
            <button
              key={p.key}
              onClick={() => setSelectedProtocol(p)}
              className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition border ${
                selectedProtocol?.key === p.key
                  ? 'bg-primary/5 border-primary/30 text-text'
                  : 'bg-white border-border hover:bg-elevated/50 text-text'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium truncate">{p.name}</span>
                <span className={`shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium border ${COST_COLORS[p.cost_tier] || 'text-text-muted bg-elevated border-border'}`}>
                  {p.cost_tier || '?'}
                </span>
              </div>
              <span className="text-xs text-text-muted">{p.category}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Right column — detail card */}
      <div className="flex-1 min-w-0">
        {selectedProtocol ? (
          <ProtocolDetail protocol={selectedProtocol} />
        ) : (
          <div className="flex items-center justify-center h-full text-text-muted">
            Select a protocol to view details
          </div>
        )}
      </div>
    </div>
  )
}

function ProtocolDetail({ protocol }: { protocol: Protocol }) {
  return (
    <div className="bg-card border border-border rounded-xl p-6 max-w-2xl">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-xl font-semibold text-text">{protocol.name}</h2>
          <div className="flex items-center gap-2 mt-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-elevated border border-border text-text-muted">
              {protocol.category}
            </span>
            <span className="text-xs text-text-muted font-mono">{protocol.protocol_id}</span>
            {protocol.supports_rounds && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 border border-blue-200 text-blue-600">
                Multi-round
              </span>
            )}
          </div>
        </div>
        <button className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-white hover:bg-primary-hover shadow-lg shadow-primary/20 transition">
          Run This Protocol
        </button>
      </div>

      <p className="text-sm text-text mb-4 leading-relaxed">{protocol.description}</p>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-white border border-border rounded-lg p-3">
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-1">Agents</p>
          <p className="text-sm text-text">
            {protocol.min_agents}{protocol.max_agents ? `–${protocol.max_agents}` : '+'} agents
          </p>
        </div>
        <div className="bg-white border border-border rounded-lg p-3">
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-1">Cost Tier</p>
          <p className={`text-sm font-medium ${
            protocol.cost_tier === 'low' ? 'text-green-600' :
            protocol.cost_tier === 'medium' ? 'text-amber-600' :
            protocol.cost_tier === 'high' ? 'text-red-600' : 'text-text'
          }`}>
            {protocol.cost_tier || 'Unknown'}
          </p>
        </div>
      </div>

      {protocol.problem_types.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-2">Problem Types</p>
          <div className="flex flex-wrap gap-1.5">
            {protocol.problem_types.map((pt) => (
              <span key={pt} className="px-2.5 py-1 rounded-full text-xs bg-elevated border border-border text-text-muted">
                {pt}
              </span>
            ))}
          </div>
        </div>
      )}

      {protocol.when_to_use && (
        <div className="mb-4">
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-2">When to Use</p>
          <p className="text-sm text-text leading-relaxed">{protocol.when_to_use}</p>
        </div>
      )}

      {protocol.when_not_to_use && (
        <div>
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-2">When Not to Use</p>
          <p className="text-sm text-text leading-relaxed">{protocol.when_not_to_use}</p>
        </div>
      )}
    </div>
  )
}
