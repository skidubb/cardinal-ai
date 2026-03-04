import { useEffect, useState } from 'react'
import { useAgentStore } from '../stores/agentStore'
import { useTeamStore } from '../stores/teamStore'
import AgentEditor from '../components/AgentEditor'
import { api } from '../api'
import type { Agent } from '../types'

const CATEGORIES = [
  'executive', 'ceo-team', 'cfo-team', 'cmo-team', 'coo-team', 'cpo-team', 'cto-team',
  'gtm-leadership', 'gtm-sales', 'gtm-marketing', 'gtm-partners', 'gtm-success', 'gtm-ops', 'external',
]

const CATEGORY_LABELS: Record<string, string> = {
  'executive': 'Executive',
  'ceo-team': 'CEO Team',
  'cfo-team': 'CFO Team',
  'cmo-team': 'CMO Team',
  'coo-team': 'COO Team',
  'cpo-team': 'CPO Team',
  'cto-team': 'CTO Team',
  'gtm-leadership': 'GTM Leadership',
  'gtm-sales': 'GTM Sales',
  'gtm-marketing': 'GTM Marketing',
  'gtm-partners': 'GTM Partners',
  'gtm-success': 'GTM Success',
  'gtm-ops': 'GTM Ops',
  'external': 'External',
}

const DOMAIN_COLORS: Record<string, string> = {
  sec_edgar: 'bg-blue-100 text-blue-700 border-blue-200',
  github: 'bg-gray-100 text-gray-700 border-gray-200',
  census: 'bg-green-100 text-green-700 border-green-200',
  bls: 'bg-teal-100 text-teal-700 border-teal-200',
  pricing: 'bg-amber-100 text-amber-700 border-amber-200',
  pinecone: 'bg-purple-100 text-purple-700 border-purple-200',
  image_gen: 'bg-pink-100 text-pink-700 border-pink-200',
  web: 'bg-sky-100 text-sky-700 border-sky-200',
  notion: 'bg-slate-100 text-slate-700 border-slate-200',
  output: 'bg-orange-100 text-orange-700 border-orange-200',
  qa: 'bg-red-100 text-red-700 border-red-200',
}

function getToolDomain(toolKey: string): string {
  if (toolKey.startsWith('sec_')) return 'sec_edgar'
  if (toolKey.startsWith('github_')) return 'github'
  if (toolKey.startsWith('census_')) return 'census'
  if (toolKey.startsWith('bls_')) return 'bls'
  if (toolKey.startsWith('pricing_')) return 'pricing'
  if (toolKey.startsWith('pinecone_')) return 'pinecone'
  if (toolKey.includes('generate_image')) return 'image_gen'
  if (toolKey.startsWith('web_')) return 'web'
  if (toolKey.startsWith('notion_')) return 'notion'
  if (toolKey === 'write_deliverable' || toolKey === 'export_pdf') return 'output'
  if (toolKey === 'qa_validate') return 'qa'
  return 'other'
}

export default function AgentRegistry() {
  const { loading, error, selectedCategory, searchQuery, fetch, setCategory, setSearch, filtered } =
    useAgentStore()
  const { currentTeamKeys, addAgent, removeAgent } = useTeamStore()
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
  const [editorAgent, setEditorAgent] = useState<Agent | null>(null)
  const [importing, setImporting] = useState(false)

  useEffect(() => { fetch() }, [fetch])

  const agents = filtered()

  const handleImportRich = async () => {
    setImporting(true)
    try {
      const result = await api.agents.importRich()
      alert(`Imported: ${result.executives_updated} executives, ${result.sub_agents_updated} sub-agents`)
      fetch()
    } catch (e) {
      alert(`Import failed: ${(e as Error).message}`)
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="flex gap-6 h-full">
      {/* Left column — filter + list */}
      <div className="w-80 shrink-0 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted">Agent Registry</p>
          <button
            onClick={handleImportRich}
            disabled={importing}
            className="px-2.5 py-1 rounded text-xs font-medium bg-elevated border border-border text-text-muted hover:text-text disabled:opacity-50"
          >
            {importing ? 'Importing...' : 'Import Rich'}
          </button>
        </div>

        <input
          type="text"
          placeholder="Search agents..."
          value={searchQuery}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full mb-3 px-3 py-2 rounded-lg bg-white border border-border text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary text-sm"
        />

        <div className="flex flex-wrap gap-1.5 mb-4">
          <button
            onClick={() => setCategory(null)}
            className={`px-2.5 py-1 rounded-full text-xs font-medium transition ${
              !selectedCategory
                ? 'bg-primary text-white'
                : 'bg-elevated text-text-muted hover:text-text border border-border'
            }`}
          >
            All ({agents.length})
          </button>
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat === selectedCategory ? null : cat)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium transition ${
                cat === selectedCategory
                  ? 'bg-primary text-white'
                  : 'bg-elevated text-text-muted hover:text-text border border-border'
              }`}
            >
              {CATEGORY_LABELS[cat] || cat}
            </button>
          ))}
        </div>

        {loading && <p className="text-text-muted text-sm">Loading...</p>}
        {error && <p className="text-red-500 text-sm">Error: {error}</p>}

        <div className="flex-1 overflow-auto space-y-1">
          {agents.map((agent) => {
            const inTeam = currentTeamKeys.includes(agent.key)
            const hasTools = agent.tools && agent.tools.length > 0
            return (
              <button
                key={agent.key}
                onClick={() => setSelectedAgent(agent)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition border ${
                  selectedAgent?.key === agent.key
                    ? 'bg-primary/5 border-primary/30 text-text'
                    : 'bg-white border-border hover:bg-elevated/50 text-text'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium truncate">{agent.name}</span>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {hasTools && (
                      <span className="w-1.5 h-1.5 rounded-full bg-green-400" title="Has tools" />
                    )}
                    {inTeam && (
                      <span className="w-2 h-2 rounded-full bg-primary" title="In team" />
                    )}
                  </div>
                </div>
                <span className="text-xs text-text-muted">{CATEGORY_LABELS[agent.category] || agent.category}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Right column — detail card */}
      <div className="flex-1 min-w-0 overflow-y-auto">
        {selectedAgent ? (
          <AgentDetail
            agent={selectedAgent}
            inTeam={currentTeamKeys.includes(selectedAgent.key)}
            onAddToTeam={() => addAgent(selectedAgent.key)}
            onRemoveFromTeam={() => removeAgent(selectedAgent.key)}
            onEdit={() => setEditorAgent(selectedAgent)}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-text-muted">
            Select an agent to view details
          </div>
        )}
      </div>

      {/* Editor drawer */}
      {editorAgent && (
        <AgentEditor
          agent={editorAgent}
          onClose={() => setEditorAgent(null)}
          onSaved={() => {
            setEditorAgent(null)
            fetch()
          }}
        />
      )}
    </div>
  )
}

function AgentDetail({
  agent,
  inTeam,
  onAddToTeam,
  onRemoveFromTeam,
  onEdit,
}: {
  agent: Agent
  inTeam: boolean
  onAddToTeam: () => void
  onRemoveFromTeam: () => void
  onEdit: () => void
}) {
  const [promptExpanded, setPromptExpanded] = useState(false)
  const promptPreview = agent.system_prompt.length > 300 && !promptExpanded
    ? agent.system_prompt.slice(0, 300) + '...'
    : agent.system_prompt

  return (
    <div className="bg-card border border-border rounded-xl p-6 max-w-2xl">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-xl font-semibold text-text">{agent.name}</h2>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-elevated border border-border text-text-muted">
              {CATEGORY_LABELS[agent.category] || agent.category}
            </span>
            {agent.model && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-elevated border border-border text-text-muted">
                {agent.model}
              </span>
            )}
            <span className="text-xs text-text-muted font-mono">{agent.key}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onEdit}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-elevated border border-border text-text hover:bg-white shadow-sm"
          >
            Edit Agent
          </button>
          <button
            onClick={inTeam ? onRemoveFromTeam : onAddToTeam}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition shadow-sm ${
              inTeam
                ? 'bg-elevated border border-border text-text-muted hover:bg-red-50 hover:text-red-600 hover:border-red-200'
                : 'bg-primary text-white hover:bg-primary-hover shadow-lg shadow-primary/20'
            }`}
          >
            {inTeam ? 'Remove from Team' : 'Add to Team'}
          </button>
        </div>
      </div>

      {/* System Prompt */}
      <div className="mb-4">
        <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-2">
          System Prompt
          <span className="ml-2 font-normal normal-case">({agent.system_prompt.length} chars)</span>
        </p>
        <div
          className="bg-white border border-border rounded-lg p-4 font-mono text-sm text-text leading-relaxed whitespace-pre-wrap cursor-pointer"
          onClick={() => setPromptExpanded(!promptExpanded)}
        >
          {promptPreview}
        </div>
        {agent.system_prompt.length > 300 && (
          <button
            onClick={() => setPromptExpanded(!promptExpanded)}
            className="text-xs text-primary mt-1"
          >
            {promptExpanded ? 'Collapse' : 'Expand full prompt'}
          </button>
        )}
      </div>

      {/* Tools */}
      {agent.tools && agent.tools.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-2">
            Tools ({agent.tools.length})
          </p>
          <div className="flex flex-wrap gap-1.5">
            {agent.tools.map((tool) => {
              const domain = getToolDomain(tool)
              const colors = DOMAIN_COLORS[domain] || 'bg-gray-100 text-gray-600 border-gray-200'
              return (
                <span key={tool} className={`px-2 py-0.5 rounded text-xs font-medium border ${colors}`}>
                  {tool}
                </span>
              )
            })}
          </div>
        </div>
      )}

      {/* MCP Servers */}
      {agent.mcp_servers && agent.mcp_servers.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-2">MCP Servers</p>
          <div className="flex flex-wrap gap-1.5">
            {agent.mcp_servers.map((s) => (
              <span key={s} className="px-2.5 py-1 rounded-full text-xs bg-violet-50 border border-violet-200 text-violet-700">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* KB Namespaces */}
      {agent.kb_namespaces && agent.kb_namespaces.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-2">Knowledge Base</p>
          <div className="flex flex-wrap gap-1.5">
            {agent.kb_namespaces.map((ns) => (
              <span key={ns} className="px-2.5 py-1 rounded-full text-xs bg-purple-50 border border-purple-200 text-purple-700">
                {ns}
              </span>
            ))}
            {agent.kb_write_enabled && (
              <span className="px-2.5 py-1 rounded-full text-xs bg-green-50 border border-green-200 text-green-700">
                write: agent-insights
              </span>
            )}
          </div>
        </div>
      )}

      {/* Frameworks */}
      {agent.frameworks && agent.frameworks.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-2">Frameworks</p>
          <div className="space-y-2">
            {agent.frameworks.map((fw, i) => (
              <div key={i} className="bg-white border border-border rounded-lg p-3">
                <p className="text-sm font-medium text-text">{fw.name}</p>
                <p className="text-xs text-text-muted mt-0.5">{fw.description}</p>
                <p className="text-xs text-primary mt-0.5">Use when: {fw.when_to_use}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Delegation */}
      {agent.delegation && agent.delegation.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-2">Delegation</p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-text-muted">
                <th className="pb-1">Agent</th>
                <th className="pb-1">When</th>
              </tr>
            </thead>
            <tbody>
              {agent.delegation.map((d, i) => (
                <tr key={i} className="border-t border-border">
                  <td className="py-1.5 font-mono text-xs">{d.agent_key}</td>
                  <td className="py-1.5 text-text-muted">{d.delegate_when}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Deliverable Template */}
      {agent.deliverable_template && (
        <div className="mb-4">
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-2">Deliverable Template</p>
          <div className="bg-white border border-border rounded-lg p-3 font-mono text-xs text-text whitespace-pre-wrap">
            {agent.deliverable_template}
          </div>
        </div>
      )}

      {/* Context Scope (legacy) */}
      {agent.context_scope && agent.context_scope.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-2">Context Scope</p>
          <div className="flex flex-wrap gap-1.5">
            {agent.context_scope.map((scope) => (
              <span key={scope} className="px-2.5 py-1 rounded-full text-xs bg-elevated border border-border text-text-muted">
                {scope}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Constraints */}
      {agent.constraints && agent.constraints.length > 0 && (
        <div>
          <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-2">Constraints</p>
          <ul className="list-disc list-inside text-sm text-text space-y-1">
            {agent.constraints.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
