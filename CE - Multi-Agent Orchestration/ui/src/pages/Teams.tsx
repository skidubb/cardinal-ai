import { useEffect, useState } from 'react'
import { useTeamStore } from '../stores/teamStore'
import { useAgentStore } from '../stores/agentStore'

export default function Teams() {
  const {
    teams, currentTeamKeys, currentTeamName, loading,
    fetch: fetchTeams, addAgent, removeAgent, setTeamName, clearTeam, saveTeam, deleteTeam,
  } = useTeamStore()
  const { agents, fetch: fetchAgents } = useAgentStore()
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [agentFilter, setAgentFilter] = useState('')
  const [deleting, setDeleting] = useState<number | null>(null)

  useEffect(() => { fetchTeams(); fetchAgents() }, [fetchTeams, fetchAgents])

  const teamAgents = agents.filter((a) => currentTeamKeys.includes(a.key))
  const availableAgents = agents.filter(
    (a) => !currentTeamKeys.includes(a.key) &&
      (agentFilter === '' || a.name.toLowerCase().includes(agentFilter.toLowerCase()) || a.category.toLowerCase().includes(agentFilter.toLowerCase()))
  )

  const categories = [...new Set(availableAgents.map((a) => a.category))].sort()

  const handleSave = async () => {
    if (currentTeamKeys.length === 0) return
    setSaving(true)
    try {
      await saveTeam()
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    setDeleting(id)
    try {
      await deleteTeam(id)
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="max-w-4xl">
      <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-4">Team Composition</p>

      {/* Current team builder */}
      <div className="bg-card border border-border rounded-xl p-6 mb-8">
        <div className="flex items-center justify-between mb-4">
          <input
            type="text"
            value={currentTeamName}
            onChange={(e) => setTeamName(e.target.value)}
            className="text-lg font-semibold text-text bg-transparent border-b border-transparent hover:border-border focus:border-primary focus:outline-none px-1 py-0.5 transition"
          />
          <div className="flex gap-2">
            <button
              onClick={clearTeam}
              className="px-3 py-1.5 rounded-lg text-xs font-medium text-text-muted border border-border hover:bg-elevated transition"
            >
              Clear
            </button>
            <button
              onClick={handleSave}
              disabled={saving || currentTeamKeys.length === 0}
              className="px-4 py-1.5 rounded-lg text-xs font-medium bg-primary text-white hover:bg-primary-hover shadow-sm shadow-primary/20 transition disabled:opacity-50"
            >
              {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Team'}
            </button>
          </div>
        </div>

        {teamAgents.length === 0 ? (
          <p className="text-sm text-text-muted py-4 text-center">
            No agents selected. Use the list below to add agents to your team.
          </p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
            {teamAgents.map((agent, i) => (
              <div key={agent.key} className="bg-white border border-border rounded-lg p-3 flex items-start justify-between">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-text-muted bg-elevated rounded px-1.5 py-0.5">{i + 1}</span>
                    <span className="text-sm font-medium text-text truncate">{agent.name}</span>
                  </div>
                  <span className="text-xs text-text-muted mt-0.5 block">{agent.category}</span>
                </div>
                <button
                  onClick={() => removeAgent(agent.key)}
                  className="shrink-0 text-text-muted hover:text-red-500 transition ml-2"
                  title="Remove"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Agent picker */}
        <div className="border-t border-border pt-4">
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-3">Add Agents</p>
          <input
            type="text"
            placeholder="Filter agents by name or category..."
            value={agentFilter}
            onChange={(e) => setAgentFilter(e.target.value)}
            className="w-full mb-3 px-3 py-2 rounded-lg bg-white border border-border text-sm text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <div className="max-h-64 overflow-y-auto space-y-3">
            {categories.map((cat) => {
              const catAgents = availableAgents.filter((a) => a.category === cat)
              if (catAgents.length === 0) return null
              return (
                <div key={cat}>
                  <p className="text-xs font-medium text-text-muted mb-1.5">{cat}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {catAgents.map((a) => (
                      <button
                        key={a.key}
                        onClick={() => addAgent(a.key)}
                        className="px-2.5 py-1 rounded-full text-xs font-medium bg-elevated text-text-muted hover:text-primary hover:bg-primary/5 border border-border hover:border-primary/20 transition"
                      >
                        + {a.name}
                      </button>
                    ))}
                  </div>
                </div>
              )
            })}
            {availableAgents.length === 0 && (
              <p className="text-xs text-text-muted text-center py-2">
                {agents.length === 0 ? 'No agents loaded.' : 'All agents are already in the team.'}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Saved teams library */}
      <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-4">Saved Teams</p>
      {loading ? (
        <p className="text-sm text-text-muted">Loading...</p>
      ) : teams.length === 0 ? (
        <p className="text-sm text-text-muted">No saved teams yet.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {teams.map((team) => (
            <div key={team.id} className="bg-card border border-border rounded-xl p-4">
              <div className="flex items-start justify-between">
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-text">{team.name}</h3>
                  <p className="text-xs text-text-muted mt-1">
                    {team.agent_keys.length} agents
                  </p>
                  {team.description && (
                    <p className="text-xs text-text-muted mt-1">{team.description}</p>
                  )}
                  <div className="flex flex-wrap gap-1 mt-2">
                    {team.agent_keys.slice(0, 6).map((k) => (
                      <span key={k} className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-elevated text-text-muted">
                        {k}
                      </span>
                    ))}
                    {team.agent_keys.length > 6 && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] text-text-muted">
                        +{team.agent_keys.length - 6} more
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(team.id)}
                  disabled={deleting === team.id}
                  className="shrink-0 ml-2 px-2 py-1 rounded-lg text-xs text-text-muted hover:text-red-500 hover:bg-red-50 border border-transparent hover:border-red-200 transition disabled:opacity-50"
                >
                  {deleting === team.id ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
