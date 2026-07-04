"use client";

import {
  Sparkles,
  FolderClock,
  Workflow,
  Users,
  Zap,
  Plug,
  Network,
  Share2,
  BookOpen,
  FileSearch,
  GraduationCap,
  CreditCard,
  type LucideIcon,
} from "lucide-react";
import { NavGroup, type NavItem } from "./nav-group";

type Group = { label: string; items: NavItem[] };

function buildGroups({
  hasKnowledgeGraph,
  hasCustom,
  hasPremium,
}: {
  hasKnowledgeGraph: boolean;
  hasCustom: boolean;
  hasPremium: boolean;
}): Group[] {
  return [
    {
      label: "",
      items: [
        { href: "/discover", label: "Discover", icon: FileSearch as LucideIcon },
        { href: "/run", label: "Ask", icon: Sparkles as LucideIcon },
      ],
    },
    {
      label: "Build",
      items: [
        { href: "/agents", label: "Agents", icon: Users as LucideIcon },
        { href: "/teams", label: "Teams", icon: Zap as LucideIcon },
        { href: "/protocols", label: "Protocols", icon: BookOpen as LucideIcon },
        {
          href: "/pipelines",
          label: "Pipelines",
          icon: Workflow as LucideIcon,
          pro: !hasPremium,
        },
      ],
    },
    {
      label: "Connect",
      items: [
        { href: "/integrations", label: "Tools", icon: Plug as LucideIcon },
        {
          href: "/knowledge",
          label: "Knowledge Graph",
          icon: Network as LucideIcon,
          pro: !hasKnowledgeGraph,
        },
        {
          href: "/knowledge/graph",
          label: "Graph map",
          icon: Share2 as LucideIcon,
          pro: !hasKnowledgeGraph,
        },
      ],
    },
    {
      label: "History",
      items: [
        { href: "/runs", label: "Runs", icon: FolderClock as LucideIcon },
        {
          href: "/corrections",
          label: "Corrections",
          icon: GraduationCap as LucideIcon,
          pro: !hasKnowledgeGraph,
        },
      ],
    },
    {
      label: "Account",
      items: [{ href: "/billing", label: "Billing", icon: CreditCard as LucideIcon }],
    },
  ];
}

export function Sidebar({
  hasKnowledgeGraph = true,
  hasCustom = true,
  hasPremium = true,
}: {
  hasKnowledgeGraph?: boolean;
  hasCustom?: boolean;
  hasPremium?: boolean;
}) {
  const groups = buildGroups({ hasKnowledgeGraph, hasCustom, hasPremium });
  return (
    <aside className="hidden w-60 shrink-0 border-r border-border bg-background md:flex md:flex-col">
      <nav className="flex-1 overflow-y-auto px-3 py-6">
        {groups.map((g) => (
          <NavGroup key={g.label} label={g.label} items={g.items} />
        ))}
      </nav>
      <footer className="border-t border-border p-4 font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
        Cardinal Element
      </footer>
    </aside>
  );
}
