import { create } from 'zustand'
import type { KBNamespace, KBSearchResult } from '../types'
import { api } from '../api'

interface KnowledgeState {
  namespaces: KBNamespace[]
  selectedNamespace: string | null
  searchResults: KBSearchResult[]
  searchQuery: string
  searching: boolean
  loading: boolean
  searchError: string | null
  uploadMessage: string | null
  fetch: () => Promise<void>
  select: (ns: string | null) => void
  search: (query: string) => Promise<void>
  setSearchQuery: (q: string) => void
  upload: (file: File) => Promise<void>
  clearUploadMessage: () => void
}

export const useKnowledgeStore = create<KnowledgeState>((set, get) => ({
  namespaces: [],
  selectedNamespace: null,
  searchResults: [],
  searchQuery: '',
  searching: false,
  loading: false,
  searchError: null,
  uploadMessage: null,
  fetch: async () => {
    set({ loading: true })
    try {
      const namespaces = await api.knowledge.namespaces()
      set({ namespaces, loading: false })
    } catch {
      set({ loading: false })
    }
  },
  select: (ns) => set({ selectedNamespace: ns, searchResults: [], searchQuery: '', searchError: null }),
  search: async (query: string) => {
    const { selectedNamespace } = get()
    if (!selectedNamespace || !query.trim()) return
    set({ searching: true, searchError: null })
    try {
      const data = await api.knowledge.search(selectedNamespace, query)
      set({ searchResults: data.results, searchError: data.error || null, searching: false })
    } catch (e) {
      set({ searchError: (e as Error).message, searching: false })
    }
  },
  setSearchQuery: (q) => set({ searchQuery: q }),
  upload: async (file: File) => {
    const { selectedNamespace, fetch: refetch } = get()
    if (!selectedNamespace) return
    const result = await api.knowledge.upload(selectedNamespace, file)
    if (result?.message) {
      set({ uploadMessage: result.message })
    }
    refetch()
  },
  clearUploadMessage: () => set({ uploadMessage: null }),
}))
