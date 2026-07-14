"use client";

import { cn } from "@/lib/utils";
import { Shield, LayoutDashboard, AlertTriangle, FolderKanban, FlaskConical, Settings2, Boxes, ScrollText, LogOut, ChevronRight } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type PageKey =
  | "command-center"
  | "alerts"
  | "cases"
  | "simulation"
  | "rules"
  | "model-registry"
  | "audit";

interface NavItem {
  key: PageKey;
  label: string;
  icon: LucideIcon;
  badge?: string;
  group?: string;
}

const NAV: NavItem[] = [
  { key: "command-center", label: "Command Center", icon: LayoutDashboard, group: "Operations" },
  { key: "alerts", label: "Alerts Monitoring", icon: AlertTriangle, badge: "12", group: "Operations" },
  { key: "cases", label: "Case Management", icon: FolderKanban, badge: "8", group: "Operations" },
  { key: "simulation", label: "Simulation Lab", icon: FlaskConical, group: "Tools" },
  { key: "rules", label: "Rules Engine", icon: Settings2, group: "Configuration" },
  { key: "model-registry", label: "Model Registry", icon: Boxes, group: "Configuration" },
  { key: "audit", label: "Audit Logs", icon: ScrollText, group: "Compliance" },
];

interface SidebarProps {
  active: PageKey;
  onNavigate: (page: PageKey) => void;
  user?: { name: string; role: string };
}

export function Sidebar({ active, onNavigate, user }: SidebarProps) {
  const grouped = NAV.reduce<Record<string, NavItem[]>>((acc, item) => {
    const g = item.group ?? "Other";
    (acc[g] ??= []).push(item);
    return acc;
  }, {});

  return (
    <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      {/* Brand */}
      <div className="flex h-16 items-center gap-2.5 border-b border-sidebar-border px-5">
        <div className="relative flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary/90 to-primary/60 shadow-lg shadow-primary/20">
          <Shield className="h-5 w-5 text-primary-foreground" />
          <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-sidebar bg-emerald-400 pulse-dot text-emerald-400" />
        </div>
        <div className="leading-tight">
          <div className="font-mono text-sm font-bold tracking-tight">SENTINEL</div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Fraud Intel</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="scroll-thin flex-1 overflow-y-auto px-3 py-4">
        {Object.entries(grouped).map(([group, items]) => (
          <div key={group} className="mb-5">
            <div className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
              {group}
            </div>
            <div className="space-y-0.5">
              {items.map((item) => {
                const Icon = item.icon;
                const isActive = active === item.key;
                return (
                  <button
                    key={item.key}
                    onClick={() => onNavigate(item.key)}
                    className={cn(
                      "group relative flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-all",
                      isActive
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                    )}
                  >
                    {isActive && (
                      <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-primary" />
                    )}
                    <Icon
                      className={cn(
                        "h-4 w-4 shrink-0 transition-colors",
                        isActive ? "text-primary" : "text-muted-foreground group-hover:text-sidebar-foreground"
                      )}
                    />
                    <span className="flex-1 text-left">{item.label}</span>
                    {item.badge && (
                      <span className="rounded-full bg-primary/15 px-1.5 py-0.5 text-[10px] font-semibold tabular text-primary">
                        {item.badge}
                      </span>
                    )}
                    {isActive && <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* User card */}
      <div className="border-t border-sidebar-border p-3">
        <div className="flex items-center gap-3 rounded-md p-2 hover:bg-sidebar-accent/50 transition-colors cursor-pointer">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-violet-500/30 to-violet-700/30 text-xs font-semibold text-violet-300">
            {(user?.name ?? "U").slice(0, 2).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-xs font-semibold">{user?.name ?? "Analyst"}</div>
            <div className="truncate text-[10px] text-muted-foreground">
              {user?.role ?? "Fraud Analyst"}
            </div>
          </div>
          <LogOut className="h-3.5 w-3.5 text-muted-foreground hover:text-red-400" />
        </div>
      </div>
    </aside>
  );
}
