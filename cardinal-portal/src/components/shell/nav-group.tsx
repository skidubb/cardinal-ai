"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  match?: (pathname: string) => boolean;
}

export interface NavGroupProps {
  label: string;
  items: NavItem[];
}

export function NavGroup({ label, items }: NavGroupProps) {
  const pathname = usePathname();

  return (
    <div className="mb-5">
      {label ? (
        <div className="px-3 pb-2 font-mono text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
          {label}
        </div>
      ) : null}
      <ul className="space-y-0.5">
        {items.map((item) => {
          const active = item.match
            ? item.match(pathname)
            : pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                className={[
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                  active
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-foreground hover:bg-secondary",
                ].join(" ")}
              >
                <Icon size={16} strokeWidth={2} className={active ? "text-primary" : "text-muted-foreground"} />
                <span>{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
