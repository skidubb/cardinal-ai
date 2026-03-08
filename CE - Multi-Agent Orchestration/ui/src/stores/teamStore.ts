import { create } from 'zustand'
import type { Team } from '../types'
import { api } from '../api'

interface TeamState {
  teams: Team[]
  currentTeamKeys: string[]
  currentTeamName: string
  editingTeamId: number | null
  loading: boolean
  fetch: () => Promise<void>
  addAgent: (key: string) => void
  removeAgent: (key: string) => void
  setTeamName: (name: string) => void
  clearTeam: () => void
  saveTeam: () => Promise<void>
  updateTeam: () => Promise<void>
  startEditing: (team: Team) => void
  cancelEditing: () => void
  deleteTeam: (id: number) => Promise<void>
}

export const useTeamStore = create<TeamState>((set, get) => ({
  teams: [],
  currentTeamKeys: [],
  currentTeamName: 'Untitled Team',
  editingTeamId: null,
  loading: false,
  fetch: async () => {
    set({ loading: true })
    try {
      const teams = await api.teams.list()
      set({ teams, loading: false })
    } catch {
      set({ loading: false })
    }
  },
  addAgent: (key) => {
    const { currentTeamKeys } = get()
    if (!currentTeamKeys.includes(key)) {
      set({ currentTeamKeys: [...currentTeamKeys, key] })
    }
  },
  removeAgent: (key) => {
    set({ currentTeamKeys: get().currentTeamKeys.filter((k) => k !== key) })
  },
  setTeamName: (name) => set({ currentTeamName: name }),
  clearTeam: () => set({ currentTeamKeys: [], currentTeamName: 'Untitled Team', editingTeamId: null }),
  saveTeam: async () => {
    const { currentTeamName, currentTeamKeys, fetch: refetch } = get()
    if (currentTeamKeys.length === 0) return
    await api.teams.create({ name: currentTeamName, agent_keys: currentTeamKeys } as Parameters<typeof api.teams.create>[0])
    set({ editingTeamId: null })
    refetch()
  },
  updateTeam: async () => {
    const { editingTeamId, currentTeamName, currentTeamKeys, fetch: refetch } = get()
    if (!editingTeamId || currentTeamKeys.length === 0) return
    await api.teams.update(editingTeamId, { name: currentTeamName, agent_keys: currentTeamKeys } as Parameters<typeof api.teams.update>[1])
    set({ editingTeamId: null })
    refetch()
  },
  startEditing: (team: Team) => {
    set({
      editingTeamId: team.id,
      currentTeamName: team.name,
      currentTeamKeys: [...team.agent_keys],
    })
  },
  cancelEditing: () => {
    set({ editingTeamId: null, currentTeamKeys: [], currentTeamName: 'Untitled Team' })
  },
  deleteTeam: async (id) => {
    await api.teams.delete(id)
    get().fetch()
  },
}))
