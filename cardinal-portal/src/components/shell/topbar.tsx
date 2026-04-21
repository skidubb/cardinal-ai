import Link from "next/link";
import { OrganizationSwitcher, UserButton } from "@clerk/nextjs";
import { Logo } from "@/components/brand/logo";

export function Topbar() {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-border bg-background px-6">
      <Link href="/dashboard" className="flex items-center gap-3">
        <Logo width={128} height={28} priority />
      </Link>
      <div className="flex items-center gap-3">
        <OrganizationSwitcher
          hidePersonal
          appearance={{
            elements: {
              organizationSwitcherTrigger: "rounded-md border border-border px-3 py-1.5 hover:bg-secondary",
            },
          }}
        />
        <UserButton />
      </div>
    </header>
  );
}
