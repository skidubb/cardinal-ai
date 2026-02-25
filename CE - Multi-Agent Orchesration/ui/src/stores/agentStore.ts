import { create } from 'zustand'
import type { Agent } from '../types'
import { api } from '../api'

interface AgentState {
  agents: Agent[]
  loading: boolean
  error: string | null
  selectedCategory: string | null
  searchQuery: string
  fetch: () => Promise<void>
  setCategory: (cat: string | null) => void
  setSearch: (q: string) => void
  filtered: () => Agent[]
}

export const useAgentStore = create<AgentState>((set, get) => ({
  agents: [],
  loading: false,
  error: null,
  selectedCategory: null,
  searchQuery: '',
  fetch: async () => {
    set({ loading: true, error: null })
    try {
      const agents = await api.agents.list()
      set({ agents, loading: false })
    } catch (e) {
      set({ error: (e as Error).message, loading: false })
    }
  },
  setCategory: (cat) => set({ selectedCategory: cat }),
  setSearch: (q) => set({ searchQuery: q }),
  filtered: () => {
    const { agents, selectedCategory, searchQuery } = get()
    return agents.filter((a) => {
      if (selectedCategory && a.category !== selectedCategory) return false
      if (searchQuery) {
        const q = searchQuery.toLowerCase()
        return (
          a.name.toLowerCase().includes(q) ||
          a.key.toLowerCase().includes(q) ||
          a.system_prompt.toLowerCase().includes(q)
        )
      }
      return true
    })
  },
}))
