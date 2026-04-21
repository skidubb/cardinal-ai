"use client";

import {
  Sparkles,
  FolderClock,
  Workflow,
  Users,
  Zap,
  Plug,
  Database,
  BookOpen,
  FileSearch,
  type LucideIcon,
} from "lucide-react";
import { NavGroup, type NavItem } from "./nav-group";

type Group = { label: string; items: NavItem[] };

const GROUPS: Group[] = [
  {
    label: "Work",
    items: [
      { href: "/discover", label: "Discover", icon: FileSearch as LucideIcon },
      { href: "/run", label: "Ask", icon: Sparkles as LucideIcon },
      { href: "/runs", label: "Runs", icon: FolderClock as LucideIcon },
    ],
  },
  {
    label: "Build",
    items: [
      { href: "/agents", label: "Agents", icon: Users as LucideIcon },
      { href: "/teams", label: "Teams", icon: Zap as LucideIcon },
      { href: "/pipelines", label: "Pipelines", icon: Workflow as LucideIcon },
    ],
  },
  {
    label: "Connect",
    items: [
      { href: "/integrations", label: "Tools", icon: Plug as LucideIcon },
      { href: "/knowledge", label: "Graph", icon: Database as LucideIcon },
      { href: "/protocols", label: "Protocols", icon: BookOpen as LucideIcon },
    ],
  },
  {
    label: "Learn",
    items: [
      { href: "/corrections", label: "Corrections", icon: BookOpen as LucideIcon },
    ],
  },
];

export function Sidebar() {
  return (
    <aside className="hidden w-60 shrink-0 border-r border-border bg-background md:flex md:flex-col">
      <nav className="flex-1 overflow-y-auto px-3 py-6">
        {GROUPS.map((g) => (
          <NavGroup key={g.label} label={g.label} items={g.items} />
        ))}
      </nav>
      <footer className="border-t border-border p-4 font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
        Cardinal Element
      </footer>
    </aside>
  );
}
