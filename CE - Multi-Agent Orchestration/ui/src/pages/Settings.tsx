import { useEffect, useState } from 'react'
import { api } from '../api'

interface HealthData {
  status?: string
  version?: string
  agent_count?: number
  protocol_count?: number
  agent_mode?: string
  [key: string]: unknown
}

export default function Settings() {
  const [health, setHealth] = useState<HealthData | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadHealth()
  }, [])

  const loadHealth = async () => {
    setLoading(true)
    setHealthError(null)
    try {
      const data = await api.health() as HealthData
      setHealth(data)
    } catch (e: any) {
      setHealthError(e.message || 'Failed to connect to API')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl">
      <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-4">Configuration</p>
      <h2 className="text-2xl font-semibold text-text mb-6">Settings</h2>

      {/* API Health */}
      <div className="bg-card border border-border rounded-xl p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted">API Health</p>
          <button
            onClick={loadHealth}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg text-xs font-medium text-text-muted border border-border hover:bg-elevated transition disabled:opacity-50"
          >
            {loading ? 'Checking...' : 'Refresh'}
          </button>
        </div>

        {loading ? (
          <p className="text-sm text-text-muted">Checking API status...</p>
        ) : healthError ? (
          <div className="flex items-center gap-3">
            <span className="w-3 h-3 rounded-full bg-red-500 shrink-0" />
            <div>
              <p className="text-sm font-medium text-red-600">Unreachable</p>
              <p className="text-xs text-text-muted mt-0.5">{healthError}</p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <span className="w-3 h-3 rounded-full bg-green-500 shrink-0" />
              <p className="text-sm font-medium text-green-600">Connected</p>
            </div>
            {health && (
              <div className="grid grid-cols-2 gap-3 mt-3">
                {health.status && (
                  <InfoItem label="Status" value={health.status} />
                )}
                {health.version && (
                  <InfoItem label="Version" value={String(health.version)} />
                )}
                {health.agent_count != null && (
                  <InfoItem label="Agents" value={String(health.agent_count)} />
                )}
                {health.protocol_count != null && (
                  <InfoItem label="Protocols" value={String(health.protocol_count)} />
                )}
                {health.agent_mode && (
                  <InfoItem label="Agent Mode" value={health.agent_mode} />
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Model Configuration */}
      <div className="bg-card border border-border rounded-xl p-6 mb-6">
        <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-4">Model Configuration</p>
        <div className="grid grid-cols-1 gap-3">
          <div className="bg-white border border-border rounded-lg p-3">
            <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-1">Thinking Model</p>
            <p className="text-sm font-mono text-text">claude-opus-4-6</p>
            <p className="text-xs text-text-muted mt-1">Used for agent reasoning, synthesis, and creative stages</p>
          </div>
          <div className="bg-white border border-border rounded-lg p-3">
            <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-1">Orchestration Model</p>
            <p className="text-sm font-mono text-text">claude-haiku-4-5-20251001</p>
            <p className="text-xs text-text-muted mt-1">Used for mechanical stages (dedup, ranking, extraction, classification)</p>
          </div>
        </div>
      </div>

      {/* System Info */}
      <div className="bg-card border border-border rounded-xl p-6">
        <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-4">System Info</p>
        <div className="grid grid-cols-2 gap-3">
          <InfoItem label="Runtime" value="Python 3.11+" />
          <InfoItem label="SDK" value="Anthropic Claude Agent SDK" />
          <InfoItem label="Protocols" value="48 coordination patterns" />
          <InfoItem label="Agent Registry" value="56 agents, 14 categories" />
        </div>
      </div>
    </div>
  )
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white border border-border rounded-lg p-3">
      <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-1">{label}</p>
      <p className="text-sm text-text">{value}</p>
    </div>
  )
}
