import Link from "next/link";
import { Logo } from "@/components/brand/logo";
import { TopbarClerkControls } from "@/components/shell/topbar-clerk-controls";
import { TopbarHydrationDebug } from "@/components/shell/topbar-hydration-debug";

export function Topbar() {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-border bg-background px-6">
      <TopbarHydrationDebug />
      <Link href="/dashboard" className="flex items-center gap-3">
        <Logo width={128} height={28} priority />
      </Link>
      <div className="flex items-center gap-3">
        <TopbarClerkControls />
      </div>
    </header>
  );
}
