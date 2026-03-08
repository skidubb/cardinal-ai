import { useEffect, useState } from 'react'
import { useIntegrationStore } from '../stores/integrationStore'
import type { Integration } from '../types'

const DOMAIN_LABELS: Record<string, string> = {
  sec_edgar: 'SEC EDGAR',
  github: 'GitHub',
  census: 'Census Bureau',
  bls: 'Bureau of Labor Statistics',
  pricing: 'Pricing Models',
  pinecone: 'Pinecone',
  image_gen: 'Image Generation',
  web: 'Web',
  notion: 'Notion',
  output: 'Output',
  qa: 'QA',
}

function Toggle({ enabled, onToggle }: { enabled: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
        enabled ? 'bg-primary' : 'bg-border'
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${
          enabled ? 'translate-x-[18px]' : 'translate-x-[3px]'
        }`}
      />
    </button>
  )
}

function ToolDomainCard({ item, onToggle }: { item: Integration; onToggle: () => void }) {
  const toolCount = item.config?.tool_count ?? 0
  return (
    <div className="bg-card border border-border rounded-xl p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              item.enabled ? 'bg-green-500' : 'bg-gray-400'
            }`}
          />
          <h3 className="font-medium text-text text-sm">
            {DOMAIN_LABELS[item.name] ?? item.name}
          </h3>
        </div>
        <Toggle enabled={item.enabled} onToggle={onToggle} />
      </div>
      <p className="text-xs text-text-muted">{item.description}</p>
      <span className="text-[11px] text-text-muted/60">{toolCount} tool{toolCount !== 1 ? 's' : ''}</span>
    </div>
  )
}

function McpServerCard({
  item,
  onToggle,
  onDelete,
}: {
  item: Integration
  onToggle: () => void
  onDelete?: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const transport = item.config?.transport ?? 'stdio'

  return (
    <div className="bg-card border border-border rounded-xl p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              item.enabled ? 'bg-green-500' : 'bg-gray-400'
            }`}
          />
          <h3 className="font-medium text-text text-sm">{item.name}</h3>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-elevated text-text-muted border border-border">
            {transport}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {!item.is_builtin && onDelete && (
            <button
              onClick={onDelete}
              className="text-xs text-red-500 hover:text-red-400"
            >
              Remove
            </button>
          )}
          <Toggle enabled={item.enabled} onToggle={onToggle} />
        </div>
      </div>
      <p className="text-xs text-text-muted">{item.description}</p>
      {item.config?.url && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-[11px] text-primary hover:underline self-start"
        >
          {expanded ? 'Hide config' : 'Show config'}
        </button>
      )}
      {expanded && item.config?.url && (
        <div className="bg-elevated rounded-lg p-2 text-xs text-text-muted font-mono">
          {item.config.url}
        </div>
      )}
    </div>
  )
}

export default function ToolsHub() {
  const { loading, searchQuery, fetch, toggle, remove, setSearch, filtered, addMcpServer } =
    useIntegrationStore()
  const [showAddForm, setShowAddForm] = useState(false)
  const [newName, setNewName] = useState('')
  const [newUrl, setNewUrl] = useState('')
  const [newTransport, setNewTransport] = useState('stdio')
  const [newDescription, setNewDescription] = useState('')

  useEffect(() => {
    fetch()
  }, [fetch])

  const items = filtered()
  const toolDomains = items.filter((i) => i.type === 'tool_domain')
  const mcpServers = items.filter((i) => i.type === 'mcp_server')

  const handleAdd = async () => {
    if (!newName.trim()) return
    await addMcpServer({
      name: newName.trim(),
      url: newUrl.trim(),
      transport: newTransport,
      description: newDescription.trim(),
    })
    setNewName('')
    setNewUrl('')
    setNewTransport('stdio')
    setNewDescription('')
    setShowAddForm(false)
  }

  return (
    <div className="max-w-5xl space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text">Tools & MCP Integration Hub</h1>
          <p className="text-sm text-text-muted mt-1">
            Enable tool domains and MCP servers for your agents
          </p>
        </div>
        <input
          type="text"
          placeholder="Search integrations..."
          value={searchQuery}
          onChange={(e) => setSearch(e.target.value)}
          className="w-64 px-3 py-2 rounded-lg bg-elevated border border-border text-sm text-text placeholder:text-text-muted/50 focus:outline-none focus:border-primary"
        />
      </div>

      {loading && <p className="text-sm text-text-muted">Loading...</p>}

      {/* Tool Domains */}
      <section>
        <h2 className="text-sm font-bold tracking-wider uppercase text-text-muted/50 mb-3">
          Tool Domains
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {toolDomains.map((item) => (
            <ToolDomainCard key={item.name} item={item} onToggle={() => toggle(item.name)} />
          ))}
        </div>
      </section>

      {/* MCP Servers */}
      <section>
        <h2 className="text-sm font-bold tracking-wider uppercase text-text-muted/50 mb-3">
          MCP Servers
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {mcpServers.map((item) => (
            <McpServerCard
              key={item.name}
              item={item}
              onToggle={() => toggle(item.name)}
              onDelete={!item.is_builtin ? () => remove(item.name) : undefined}
            />
          ))}
        </div>

        {/* Add MCP Server */}
        {!showAddForm ? (
          <button
            onClick={() => setShowAddForm(true)}
            className="mt-4 px-4 py-2 rounded-lg bg-elevated border border-border text-sm text-text-muted hover:text-text hover:border-primary transition"
          >
            + Add MCP Server
          </button>
        ) : (
          <div className="mt-4 bg-card border border-border rounded-xl p-4 max-w-md space-y-3">
            <h3 className="text-sm font-medium text-text">Add MCP Server</h3>
            <input
              type="text"
              placeholder="Server name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-elevated border border-border text-sm text-text placeholder:text-text-muted/50 focus:outline-none focus:border-primary"
            />
            <input
              type="text"
              placeholder="URL (optional)"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-elevated border border-border text-sm text-text placeholder:text-text-muted/50 focus:outline-none focus:border-primary"
            />
            <select
              value={newTransport}
              onChange={(e) => setNewTransport(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-elevated border border-border text-sm text-text focus:outline-none focus:border-primary"
            >
              <option value="stdio">stdio</option>
              <option value="http">http</option>
            </select>
            <input
              type="text"
              placeholder="Description"
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-elevated border border-border text-sm text-text placeholder:text-text-muted/50 focus:outline-none focus:border-primary"
            />
            <div className="flex gap-2">
              <button
                onClick={handleAdd}
                className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:opacity-90 transition"
              >
                Add
              </button>
              <button
                onClick={() => setShowAddForm(false)}
                className="px-4 py-2 rounded-lg bg-elevated border border-border text-sm text-text-muted hover:text-text transition"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
