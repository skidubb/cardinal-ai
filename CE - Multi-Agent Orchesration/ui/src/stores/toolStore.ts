import { create } from 'zustand'
import type { ToolRegistry } from '../types'
import { api } from '../api'

interface ToolState {
  registry: ToolRegistry | null
  loading: boolean
  error: string | null
  fetch: () => Promise<void>
}

export const useToolStore = create<ToolState>((set) => ({
  registry: null,
  loading: false,
  error: null,
  fetch: async () => {
    set({ loading: true, error: null })
    try {
      const registry = await api.tools.list()
      set({ registry, loading: false })
    } catch (e) {
      set({ error: (e as Error).message, loading: false })
    }
  },
}))
