import type { Agent, Integration, KBNamespace, KBSearchResult, Protocol, ProtocolStages, Team, Pipeline, Run, ToolRegistry } from './types'

const BASE = '/api'

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`)
  return res.json()
}

export const api = {
  agents: {
    list: () => fetchJSON<Agent[]>('/agents'),
    get: (key: string) => fetchJSON<Agent>(`/agents/${key}`),
    create: (agent: Partial<Agent>) =>
      fetchJSON<Agent>('/agents', { method: 'POST', body: JSON.stringify(agent) }),
    update: (key: string, agent: Partial<Agent>) =>
      fetchJSON<Agent>(`/agents/${key}`, { method: 'PUT', body: JSON.stringify(agent) }),
    importRich: () =>
      fetchJSON<{ status: string; executives_updated: number; sub_agents_updated: number }>(
        '/agents/import-rich',
        { method: 'POST' },
      ),
  },
  tools: {
    list: () => fetchJSON<ToolRegistry>('/tools'),
  },
  protocols: {
    list: () => fetchJSON<Protocol[]>('/protocols'),
    stages: (key: string) => fetchJSON<ProtocolStages>(`/protocols/${key}/stages`),
  },
  teams: {
    list: () => fetchJSON<Team[]>('/teams'),
    create: (team: Partial<Team>) =>
      fetchJSON<Team>('/teams', { method: 'POST', body: JSON.stringify(team) }),
    update: (id: number, team: Partial<Team>) =>
      fetchJSON<Team>(`/teams/${id}`, { method: 'PUT', body: JSON.stringify(team) }),
    delete: (id: number) =>
      fetchJSON<void>(`/teams/${id}`, { method: 'DELETE' }),
  },
  pipelines: {
    list: () => fetchJSON<Pipeline[]>('/pipelines'),
    create: (pipeline: Partial<Pipeline>) =>
      fetchJSON<Pipeline>('/pipelines', { method: 'POST', body: JSON.stringify(pipeline) }),
    delete: (id: number) =>
      fetchJSON<void>(`/pipelines/${id}`, { method: 'DELETE' }),
  },
  integrations: {
    list: () => fetchJSON<Integration[]>('/integrations'),
    update: (name: string, data: Partial<Integration>) =>
      fetchJSON<Integration>(`/integrations/${name}`, { method: 'PUT', body: JSON.stringify(data) }),
    create: (data: Partial<Integration>) =>
      fetchJSON<Integration>('/integrations', { method: 'POST', body: JSON.stringify(data) }),
    delete: (name: string) =>
      fetchJSON<void>(`/integrations/${name}`, { method: 'DELETE' }),
  },
  knowledge: {
    namespaces: () => fetchJSON<KBNamespace[]>('/knowledge/namespaces'),
    search: (ns: string, query: string) =>
      fetchJSON<{ results: KBSearchResult[]; error?: string }>(`/knowledge/namespaces/${ns}/search?q=${encodeURIComponent(query)}`),
    stats: (ns: string) => fetchJSON<{ vector_count: number | null }>(`/knowledge/namespaces/${ns}/stats`),
    upload: async (ns: string, file: File) => {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`/api/knowledge/namespaces/${ns}/upload`, { method: 'POST', body: form })
      if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`)
      return res.json()
    },
  },
  health: () => fetchJSON<Record<string, unknown>>('/health'),
  runs: {
    list: () => fetchJSON<Run[]>('/runs'),
    get: (id: number) => fetchJSON<Run & { outputs: any[]; steps: any[] }>(`/runs/${id}`),
  },
}
