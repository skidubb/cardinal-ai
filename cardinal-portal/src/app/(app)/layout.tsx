import type { ReactNode } from "react";
import { auth } from "@clerk/nextjs/server";
import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";

export default async function AppShellLayout({ children }: { children: ReactNode }) {
  const { has } = await auth();
  const hasKnowledgeGraph = has({ feature: "knowledge_graph" });
  const hasCustom = has({ feature: "custom_protocols_agents" });
  const hasPremium = has({ feature: "premium_protocols" });

  return (
    <div className="flex min-h-screen flex-col">
      <Topbar />
      <div className="flex flex-1">
        <Sidebar
          hasKnowledgeGraph={hasKnowledgeGraph}
          hasCustom={hasCustom}
          hasPremium={hasPremium}
        />
        <main className="flex-1 overflow-x-hidden bg-background">{children}</main>
      </div>
    </div>
  );
}
