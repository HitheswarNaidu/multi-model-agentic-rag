"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface NavItem {
  label: string;
  href: string;
  icon: string;
}

const workspaceItems: NavItem[] = [
  { label: "Chat", href: "/chat", icon: "\u25C8" },
  { label: "Data Store", href: "/data-store", icon: "\u25A6" },
  { label: "Knowledge Graph", href: "/knowledge-graph", icon: "\u25E6" },
];

const systemItems: NavItem[] = [
  { label: "Admin", href: "/admin", icon: "\u2699" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-[200px] flex-col border-r border-sidebar-border bg-sidebar">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-5">
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary" />
        <span className="text-sm font-semibold text-sidebar-foreground">
          RAG Agent
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col gap-1 px-2">
        {/* Workspace section */}
        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
          Workspace
        </p>
        {workspaceItems.map((item) => (
          <NavLink
            key={item.href}
            item={item}
            isActive={pathname === item.href}
          />
        ))}

        {/* System section */}
        <p className="px-2 pb-1 pt-6 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
          System
        </p>
        {systemItems.map((item) => (
          <NavLink
            key={item.href}
            item={item}
            isActive={pathname === item.href}
          />
        ))}
      </nav>
    </aside>
  );
}

function NavLink({ item, isActive }: { item: NavItem; isActive: boolean }) {
  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
        isActive
          ? "bg-sidebar-accent font-semibold text-sidebar-foreground"
          : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
      )}
    >
      <span className="text-base leading-none">{item.icon}</span>
      {item.label}
    </Link>
  );
}
