import type { Agent, Protocol, Team, Pipeline, Run, ToolRegistry } from './types'

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
  },
  teams: {
    list: () => fetchJSON<Team[]>('/teams'),
    create: (team: Partial<Team>) =>
      fetchJSON<Team>('/teams', { method: 'POST', body: JSON.stringify(team) }),
  },
  pipelines: {
    list: () => fetchJSON<Pipeline[]>('/pipelines'),
    create: (pipeline: Partial<Pipeline>) =>
      fetchJSON<Pipeline>('/pipelines', { method: 'POST', body: JSON.stringify(pipeline) }),
  },
  runs: {
    list: () => fetchJSON<Run[]>('/runs'),
    get: (id: number) => fetchJSON<Run & { outputs: any[]; steps: any[] }>(`/runs/${id}`),
  },
}
