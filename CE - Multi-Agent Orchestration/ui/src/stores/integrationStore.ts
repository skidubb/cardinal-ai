import { create } from 'zustand'
import type { Integration } from '../types'
import { api } from '../api'

interface IntegrationState {
  integrations: Integration[]
  loading: boolean
  searchQuery: string
  fetch: () => Promise<void>
  toggle: (name: string) => Promise<void>
  updateConfig: (name: string, config: Record<string, string> | string) => Promise<void>
  addMcpServer: (data: { name: string; description?: string; url?: string; transport?: string }) => Promise<void>
  remove: (name: string) => Promise<void>
  setSearch: (q: string) => void
  filtered: () => Integration[]
}

export const useIntegrationStore = create<IntegrationState>((set, get) => ({
  integrations: [],
  loading: false,
  searchQuery: '',
  fetch: async () => {
    set({ loading: true })
    try {
      const integrations = await api.integrations.list()
      set({ integrations, loading: false })
    } catch {
      set({ loading: false })
    }
  },
  toggle: async (name: string) => {
    const item = get().integrations.find((i) => i.name === name)
    if (!item) return
    await api.integrations.update(name, { enabled: !item.enabled } as Partial<Integration>)
    await get().fetch()
  },
  updateConfig: async (name: string, config: Record<string, string> | string) => {
    const configStr = typeof config === 'string' ? config : JSON.stringify(config)
    await api.integrations.update(name, { config_json: configStr } as any)
    await get().fetch()
  },
  addMcpServer: async (data) => {
    await api.integrations.create(data as any)
    await get().fetch()
  },
  remove: async (name: string) => {
    await api.integrations.delete(name)
    await get().fetch()
  },
  setSearch: (q) => set({ searchQuery: q }),
  filtered: () => {
    const { integrations, searchQuery } = get()
    if (!searchQuery) return integrations
    const q = searchQuery.toLowerCase()
    return integrations.filter(
      (i) =>
        i.name.toLowerCase().includes(q) ||
        i.description.toLowerCase().includes(q)
    )
  },
}))
