import { useEffect, useState } from 'react'
import { useToolStore } from '../stores/toolStore'
import { useAgentStore } from '../stores/agentStore'
import { api } from '../api'
import type { Agent, Framework, Delegation } from '../types'

const CATEGORIES = [
  'executive', 'ceo-team', 'cfo-team', 'cmo-team', 'coo-team', 'cpo-team', 'cto-team',
  'gtm-leadership', 'gtm-sales', 'gtm-marketing', 'gtm-partners', 'gtm-success', 'gtm-ops', 'external',
]

const MODELS = ['claude-opus-4-6', 'claude-sonnet-4-6', 'claude-haiku-4-5-20251001']

const TOOL_DOMAINS: Record<string, string> = {
  sec_edgar: 'SEC EDGAR',
  github: 'GitHub',
  census: 'Census',
  bls: 'BLS',
  pricing: 'Pricing',
  pinecone: 'Pinecone',
  image_gen: 'Image Gen',
  web: 'Web',
  notion: 'Notion',
  output: 'Output',
  qa: 'QA',
}

const KB_NAMESPACES = [
  'ai-gtm', 'lennys-podcast', 'leadership', 'cmo-school', 'demand-gen',
  'cro-school', 'cco-school', 'meddic', 'forecasting', 'consulting',
  'revenue-architecture', 'finance-leadership', 'general-gtm', 'market-analysis',
]

interface Props {
  agent: Agent
  onClose: () => void
  onSaved: () => void
}

export default function AgentEditor({ agent, onClose, onSaved }: Props) {
  const { registry, fetch: fetchTools } = useToolStore()
  const [form, setForm] = useState<Agent>({ ...agent })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!registry) fetchTools()
  }, [registry, fetchTools])

  useEffect(() => {
    setForm({ ...agent })
  }, [agent])

  const updateField = <K extends keyof Agent>(key: K, value: Agent[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const toggleTool = (toolKey: string) => {
    const tools = form.tools || []
    updateField('tools', tools.includes(toolKey) ? tools.filter((t) => t !== toolKey) : [...tools, toolKey])
  }

  const toggleMcp = (serverKey: string) => {
    const servers = form.mcp_servers || []
    updateField('mcp_servers', servers.includes(serverKey) ? servers.filter((s) => s !== serverKey) : [...servers, serverKey])
  }

  const toggleNamespace = (ns: string) => {
    const namespaces = form.kb_namespaces || []
    updateField('kb_namespaces', namespaces.includes(ns) ? namespaces.filter((n) => n !== ns) : [...namespaces, ns])
  }

  const addFramework = () => {
    updateField('frameworks', [...(form.frameworks || []), { name: '', description: '', when_to_use: '' }])
  }

  const updateFramework = (i: number, fw: Framework) => {
    const fws = [...(form.frameworks || [])]
    fws[i] = fw
    updateField('frameworks', fws)
  }

  const removeFramework = (i: number) => {
    updateField('frameworks', (form.frameworks || []).filter((_, idx) => idx !== i))
  }

  const addDelegation = () => {
    updateField('delegation', [...(form.delegation || []), { agent_key: '', delegate_when: '' }])
  }

  const updateDelegation = (i: number, d: Delegation) => {
    const dels = [...(form.delegation || [])]
    dels[i] = d
    updateField('delegation', dels)
  }

  const removeDelegation = (i: number) => {
    updateField('delegation', (form.delegation || []).filter((_, idx) => idx !== i))
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      await api.agents.update(form.key, form)
      onSaved()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  // Group tools by domain
  const toolsByDomain: Record<string, { key: string; name: string; description: string }[]> = {}
  if (registry) {
    for (const [key, tool] of Object.entries(registry.tools)) {
      const domain = tool.domain || 'other'
      if (!toolsByDomain[domain]) toolsByDomain[domain] = []
      toolsByDomain[domain].push({ key, name: tool.name, description: tool.description })
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />

      {/* Drawer */}
      <div className="relative w-[640px] max-w-full bg-white border-l border-border overflow-y-auto shadow-2xl">
        <div className="sticky top-0 z-10 bg-white border-b border-border px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text">Edit Agent</h2>
          <div className="flex items-center gap-3">
            {error && <span className="text-red-500 text-xs">{error}</span>}
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
            <button onClick={onClose} className="text-text-muted hover:text-text text-xl">&times;</button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* 1. Identity */}
          <Section title="Identity">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Name</Label>
                <Input value={form.name} onChange={(v) => updateField('name', v)} />
              </div>
              <div>
                <Label>Key</Label>
                <Input value={form.key} onChange={(v) => updateField('key', v)} disabled={agent.is_builtin} />
              </div>
              <div>
                <Label>Category</Label>
                <select
                  value={form.category}
                  onChange={(e) => updateField('category', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-white border border-border text-sm text-text"
                >
                  <option value="">—</option>
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <Label>Model</Label>
                <div className="flex gap-1">
                  {MODELS.map((m) => (
                    <button
                      key={m}
                      onClick={() => updateField('model', m)}
                      className={`flex-1 px-2 py-1.5 rounded text-xs font-medium transition ${
                        form.model === m ? 'bg-primary text-white' : 'bg-elevated border border-border text-text-muted hover:text-text'
                      }`}
                    >
                      {m.includes('opus') ? 'Opus' : m.includes('sonnet') ? 'Sonnet' : 'Haiku'}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <Label>Temperature ({form.temperature})</Label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={form.temperature}
                  onChange={(e) => updateField('temperature', parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>
              <div>
                <Label>Max Tokens</Label>
                <Input
                  value={String(form.max_tokens || 8192)}
                  onChange={(v) => updateField('max_tokens', parseInt(v) || 8192)}
                />
              </div>
            </div>
          </Section>

          {/* 2. System Prompt */}
          <Section title="System Prompt">
            <textarea
              value={form.system_prompt}
              onChange={(e) => updateField('system_prompt', e.target.value)}
              rows={12}
              className="w-full px-3 py-2 rounded-lg bg-white border border-border font-mono text-sm text-text resize-y"
            />
            <p className="text-xs text-text-muted mt-1">{form.system_prompt.length} characters</p>
          </Section>

          {/* 3. Tools */}
          <Section title="Tools">
            {Object.entries(toolsByDomain).map(([domain, tools]) => (
              <div key={domain} className="mb-3">
                <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-1.5">
                  {TOOL_DOMAINS[domain] || domain}
                </p>
                <div className="space-y-1">
                  {tools.map((tool) => (
                    <label key={tool.key} className="flex items-start gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={(form.tools || []).includes(tool.key)}
                        onChange={() => toggleTool(tool.key)}
                        className="mt-0.5"
                      />
                      <div>
                        <span className="text-sm text-text">{tool.name}</span>
                        <p className="text-xs text-text-muted">{tool.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </Section>

          {/* 4. MCP Servers */}
          <Section title="MCP Servers">
            {registry && Object.entries(registry.mcp_servers).map(([key, server]) => (
              <label key={key} className="flex items-start gap-2 cursor-pointer mb-2">
                <input
                  type="checkbox"
                  checked={(form.mcp_servers || []).includes(key)}
                  onChange={() => toggleMcp(key)}
                  className="mt-0.5"
                />
                <div>
                  <span className="text-sm text-text">{server.name}</span>
                  <span className="ml-2 text-xs text-text-muted">({server.transport})</span>
                  <p className="text-xs text-text-muted">{server.description}</p>
                </div>
              </label>
            ))}
          </Section>

          {/* 5. Knowledge Base */}
          <Section title="Knowledge Base">
            <div className="flex flex-wrap gap-1.5 mb-3">
              {KB_NAMESPACES.map((ns) => (
                <button
                  key={ns}
                  onClick={() => toggleNamespace(ns)}
                  className={`px-2.5 py-1 rounded-full text-xs font-medium transition ${
                    (form.kb_namespaces || []).includes(ns)
                      ? 'bg-primary text-white'
                      : 'bg-elevated text-text-muted hover:text-text border border-border'
                  }`}
                >
                  {ns}
                </button>
              ))}
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.kb_write_enabled || false}
                onChange={(e) => updateField('kb_write_enabled', e.target.checked)}
              />
              <span className="text-sm text-text">Enable KB write (agent-insights namespace)</span>
            </label>
          </Section>

          {/* 6. Deliverable Template */}
          <Section title="Deliverable Template">
            <textarea
              value={form.deliverable_template || ''}
              onChange={(e) => updateField('deliverable_template', e.target.value)}
              rows={4}
              placeholder="Structured output template (e.g., Strategic Brief format)"
              className="w-full px-3 py-2 rounded-lg bg-white border border-border font-mono text-sm text-text resize-y placeholder:text-text-muted"
            />
          </Section>

          {/* 7. Frameworks */}
          <Section title="Frameworks">
            {(form.frameworks || []).map((fw, i) => (
              <div key={i} className="border border-border rounded-lg p-3 mb-2">
                <div className="flex justify-between mb-2">
                  <Input
                    value={fw.name}
                    onChange={(v) => updateFramework(i, { ...fw, name: v })}
                    placeholder="Framework name"
                  />
                  <button onClick={() => removeFramework(i)} className="text-red-400 hover:text-red-600 text-sm ml-2">&times;</button>
                </div>
                <textarea
                  value={fw.description}
                  onChange={(e) => updateFramework(i, { ...fw, description: e.target.value })}
                  placeholder="Description"
                  rows={2}
                  className="w-full px-3 py-1.5 rounded bg-white border border-border text-sm text-text mb-1 resize-y"
                />
                <Input
                  value={fw.when_to_use}
                  onChange={(v) => updateFramework(i, { ...fw, when_to_use: v })}
                  placeholder="When to use"
                />
              </div>
            ))}
            <button onClick={addFramework} className="text-sm text-primary hover:text-primary-hover font-medium">+ Add Framework</button>
          </Section>

          {/* 8. Delegation */}
          <Section title="Delegation">
            {(form.delegation || []).map((d, i) => (
              <div key={i} className="flex gap-2 mb-2 items-start">
                <Input
                  value={d.agent_key}
                  onChange={(v) => updateDelegation(i, { ...d, agent_key: v })}
                  placeholder="Agent key"
                />
                <Input
                  value={d.delegate_when}
                  onChange={(v) => updateDelegation(i, { ...d, delegate_when: v })}
                  placeholder="Delegate when..."
                />
                <button onClick={() => removeDelegation(i)} className="text-red-400 hover:text-red-600 text-sm">&times;</button>
              </div>
            ))}
            <button onClick={addDelegation} className="text-sm text-primary hover:text-primary-hover font-medium">+ Add Delegation</button>
          </Section>

          {/* 9. Constraints */}
          <Section title="Constraints">
            <textarea
              value={(form.constraints || []).join('\n')}
              onChange={(e) => updateField('constraints', e.target.value.split('\n').filter(Boolean))}
              rows={3}
              placeholder="One constraint per line"
              className="w-full px-3 py-2 rounded-lg bg-white border border-border text-sm text-text resize-y placeholder:text-text-muted"
            />
          </Section>

          {/* 10. Personality & Style */}
          <Section title="Personality & Style">
            <Label>Personality</Label>
            <textarea
              value={form.personality || ''}
              onChange={(e) => updateField('personality', e.target.value)}
              rows={3}
              placeholder="Personality traits"
              className="w-full px-3 py-2 rounded-lg bg-white border border-border text-sm text-text resize-y mb-3 placeholder:text-text-muted"
            />
            <Label>Communication Style</Label>
            <textarea
              value={form.communication_style || ''}
              onChange={(e) => updateField('communication_style', e.target.value)}
              rows={3}
              placeholder="Communication rules and preferences"
              className="w-full px-3 py-2 rounded-lg bg-white border border-border text-sm text-text resize-y placeholder:text-text-muted"
            />
          </Section>
        </div>
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-2">{title}</p>
      {children}
    </div>
  )
}

function Label({ children }: { children: React.ReactNode }) {
  return <p className="text-xs font-medium text-text-muted mb-1">{children}</p>
}

function Input({
  value,
  onChange,
  placeholder,
  disabled,
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  disabled?: boolean
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      className="w-full px-3 py-2 rounded-lg bg-white border border-border text-sm text-text placeholder:text-text-muted disabled:opacity-50"
    />
  )
}
