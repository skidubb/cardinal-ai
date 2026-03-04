import { create } from 'zustand'

interface UIState {
  sidebarCollapsed: boolean
  teamTrayExpanded: boolean
  toggleSidebar: () => void
  toggleTeamTray: () => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  teamTrayExpanded: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  toggleTeamTray: () => set((s) => ({ teamTrayExpanded: !s.teamTrayExpanded })),
}))
