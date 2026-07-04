"use client";

import { useState, type ReactNode } from "react";

type Tab = "story" | "analyst";

export function ArticleTabs({
  article,
  analyst,
  defaultTab = "story",
}: {
  article: ReactNode;
  analyst: ReactNode;
  defaultTab?: Tab;
}) {
  const [tab, setTab] = useState<Tab>(defaultTab);

  return (
    <div>
      <div className="mb-6 inline-flex gap-1 rounded-full border border-border bg-card p-1">
        <TabButton active={tab === "story"} onClick={() => setTab("story")}>
          Story
        </TabButton>
        <TabButton active={tab === "analyst"} onClick={() => setTab("analyst")}>
          Analyst view
        </TabButton>
      </div>
      <div className={tab === "story" ? "" : "hidden"}>{article}</div>
      <div className={tab === "analyst" ? "" : "hidden"}>{analyst}</div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
        active
          ? "bg-primary text-primary-foreground shadow-[var(--shadow-indigo)]"
          : "text-muted-foreground hover:text-foreground",
      ].join(" ")}
    >
      {children}
    </button>
  );
}
