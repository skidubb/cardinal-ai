import { Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { useUIStore } from './stores/uiStore'
import { useTeamStore } from './stores/teamStore'
import { useAgentStore } from './stores/agentStore'
import LoginGate, { useAuth } from './components/LoginGate'
import Dashboard from './pages/Dashboard'
import AgentRegistry from './pages/AgentRegistry'
import Teams from './pages/Teams'
import ToolsHub from './pages/ToolsHub'
import KnowledgeExplorer from './pages/KnowledgeExplorer'
import ProtocolLibrary from './pages/ProtocolLibrary'
import Pipelines from './pages/Pipelines'
import RunHistory from './pages/RunHistory'
import RunView from './pages/RunView'
import Settings from './pages/Settings'

interface NavItem {
  to: string
  label: string
  badge?: string
}

interface NavSection {
  label: string | null
  items: NavItem[]
}

const navSections: NavSection[] = [
  {
    label: null,
    items: [{ to: '/dashboard', label: 'Dashboard' }],
  },
  {
    label: 'Build',
    items: [
      { to: '/agents', label: 'Agents', badge: '56' },
      { to: '/teams', label: 'Teams' },
      { to: '/tools', label: 'Tools & MCP' },
      { to: '/knowledge', label: 'Knowledge' },
    ],
  },
  {
    label: 'Run',
    items: [
      { to: '/protocols', label: 'Protocols', badge: '48' },
      { to: '/pipelines', label: 'Pipelines' },
      { to: '/run', label: 'Run' },
    ],
  },
  {
    label: 'History',
    items: [{ to: '/runs', label: 'Run History' }],
  },
]

function NavItemLink({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.to}
      className={({ isActive }) =>
        `flex items-center justify-between px-3 py-2 rounded-md text-sm transition-colors ${
          isActive
            ? 'bg-elevated text-primary font-medium'
            : 'text-text-muted hover:text-text hover:bg-elevated/50'
        }`
      }
    >
      <span>{item.label}</span>
      {item.badge && (
        <span className="text-xs text-text-muted bg-elevated border border-border px-1.5 py-0.5 rounded">
          {item.badge}
        </span>
      )}
    </NavLink>
  )
}

function Sidebar() {
  const collapsed = useUIStore((s) => s.sidebarCollapsed)

  if (collapsed) return null

  return (
    <aside className="w-64 bg-card flex flex-col border-r border-border shrink-0">
      <div className="px-5 py-5">
        <h1 className="text-lg font-semibold text-text tracking-tight">CE Orchestrator</h1>
      </div>

      <nav className="flex-1 px-3 space-y-1">
        {navSections.map((section, si) => (
          <div key={si} className={section.label ? 'pt-3' : ''}>
            {section.label && (
              <p className="px-3 pb-1.5 text-[10px] font-bold tracking-widest uppercase text-text-muted/50">
                {section.label}
              </p>
            )}
            {section.items.map((item) => (
              <NavItemLink key={item.to} item={item} />
            ))}
          </div>
        ))}
      </nav>

      <div className="border-t border-border px-3 py-3">
        <NavItemLink item={{ to: '/settings', label: 'Settings' }} />
      </div>
    </aside>
  )
}

function TeamTray() {
  const { teamTrayExpanded, toggleTeamTray } = useUIStore()
  const { currentTeamKeys, currentTeamName, removeAgent } = useTeamStore()
  const { agents } = useAgentStore()
  const teamAgents = agents.filter((a) => currentTeamKeys.includes(a.key))

  return (
    <div
      className={`bg-card border-t border-border transition-all overflow-hidden ${
        teamTrayExpanded ? 'h-48' : 'h-11'
      }`}
    >
      <button
        onClick={toggleTeamTray}
        className="w-full flex items-center justify-between px-5 py-2.5 hover:bg-elevated/50 transition"
      >
        <span className="text-xs text-text-muted font-bold tracking-wider uppercase">
          {currentTeamName}
          {currentTeamKeys.length > 0 && (
            <span className="ml-2 text-primary font-semibold">{currentTeamKeys.length} agents</span>
          )}
        </span>
        <svg
          className={`w-4 h-4 text-text-muted transition-transform ${teamTrayExpanded ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
        </svg>
      </button>

      {teamTrayExpanded && (
        <div className="px-5 pb-3">
          {teamAgents.length === 0 ? (
            <p className="text-xs text-text-muted">No agents in team. Visit Agent Registry to add.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {teamAgents.map((a) => (
                <span
                  key={a.key}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-white border border-border text-text"
                >
                  {a.name}
                  <button
                    onClick={() => removeAgent(a.key)}
                    className="text-text-muted hover:text-red-500"
                  >
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function App() {
  const auth = useAuth()

  return (
    <LoginGate {...auth}>
      <div className="h-screen flex flex-col bg-bg">
        <div className="flex flex-1 overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-auto p-8">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/agents" element={<AgentRegistry />} />
              <Route path="/teams" element={<Teams />} />
              <Route path="/tools" element={<ToolsHub />} />
              <Route path="/knowledge" element={<KnowledgeExplorer />} />
              <Route path="/protocols" element={<ProtocolLibrary />} />
              <Route path="/pipelines" element={<Pipelines />} />
              <Route path="/run" element={<RunView />} />
              <Route path="/runs" element={<RunHistory />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
        <TeamTray />
      </div>
    </LoginGate>
  )
}
