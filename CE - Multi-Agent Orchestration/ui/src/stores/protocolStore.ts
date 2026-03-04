import { create } from 'zustand'
import type { Protocol } from '../types'
import { api } from '../api'

interface ProtocolState {
  protocols: Protocol[]
  loading: boolean
  error: string | null
  selectedProblemType: string | null
  searchQuery: string
  fetch: () => Promise<void>
  setProblemType: (pt: string | null) => void
  setSearch: (q: string) => void
  filtered: () => Protocol[]
  problemTypes: () => string[]
}

export const useProtocolStore = create<ProtocolState>((set, get) => ({
  protocols: [],
  loading: false,
  error: null,
  selectedProblemType: null,
  searchQuery: '',
  fetch: async () => {
    set({ loading: true, error: null })
    try {
      const protocols = await api.protocols.list()
      set({ protocols, loading: false })
    } catch (e) {
      set({ error: (e as Error).message, loading: false })
    }
  },
  setProblemType: (pt) => set({ selectedProblemType: pt }),
  setSearch: (q) => set({ searchQuery: q }),
  filtered: () => {
    const { protocols, selectedProblemType, searchQuery } = get()
    return protocols.filter((p) => {
      if (selectedProblemType && !p.problem_types.includes(selectedProblemType)) return false
      if (searchQuery) {
        const q = searchQuery.toLowerCase()
        return p.name.toLowerCase().includes(q) || p.description.toLowerCase().includes(q)
      }
      return true
    })
  },
  problemTypes: () => {
    const { protocols } = get()
    const pts = new Set<string>()
    for (const p of protocols) {
      for (const pt of p.problem_types) pts.add(pt)
    }
    return Array.from(pts).sort()
  },
}))
