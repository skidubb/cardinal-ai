import { create } from 'zustand'
import type { Run } from '../types'
import { api } from '../api'

interface RunState {
  runs: Run[]
  currentRun: (Run & { outputs: any[]; steps: any[] }) | null
  loading: boolean
  fetch: () => Promise<void>
  fetchById: (id: number) => Promise<void>
}

export const useRunStore = create<RunState>((set) => ({
  runs: [],
  currentRun: null,
  loading: false,
  fetch: async () => {
    set({ loading: true })
    try {
      const runs = await api.runs.list()
      set({ runs, loading: false })
    } catch {
      set({ loading: false })
    }
  },
  fetchById: async (id: number) => {
    set({ loading: true })
    try {
      const run = await api.runs.get(id)
      set({ currentRun: run, loading: false })
    } catch {
      set({ loading: false })
    }
  },
}))
