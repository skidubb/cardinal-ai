"use client";

import { useEffect, useState } from "react";
import { OrganizationSwitcher, UserButton } from "@clerk/nextjs";

export function TopbarClerkControls() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="h-9 w-44 rounded-md border border-border bg-secondary/50" />;
  }

  return (
    <>
      <OrganizationSwitcher
        hidePersonal
        appearance={{
          elements: {
            organizationSwitcherTrigger: "rounded-md border border-border px-3 py-1.5 hover:bg-secondary",
          },
        }}
      />
      <UserButton />
    </>
  );
}
