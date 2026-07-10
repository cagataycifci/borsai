import { useState } from "react";
import {
  LayoutDashboard,
  Star,
  Briefcase,
  Newspaper,
  Sparkles,
  Bell,
  FileText,
  Users,
  Settings,
  type LucideIcon,
} from "lucide-react";
import { cn } from "../lib/cn";
import { useWorkspaceStore } from "../store/useWorkspaceStore";

interface NavItem {
  id: string;
  label: string;
  icon: LucideIcon;
  /** Workspace panel id this opens; "dashboard" restores the default layout. */
  panelId: string;
}

const ITEMS: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, panelId: "dashboard" },
  { id: "watchlists", label: "Watchlists", icon: Star, panelId: "watchlists" },
  { id: "portfolio", label: "Portfolio", icon: Briefcase, panelId: "portfolio" },
  { id: "news", label: "News", icon: Newspaper, panelId: "news" },
  { id: "ai", label: "AI", icon: Sparkles, panelId: "ai" },
  { id: "alerts", label: "Alerts", icon: Bell, panelId: "alerts" },
  { id: "reports", label: "Reports", icon: FileText, panelId: "reports" },
  { id: "commentator", label: "Commentator", icon: Users, panelId: "commentator" },
];

export function Sidebar(): JSX.Element {
  const [active, setActive] = useState("dashboard");
  const openPanel = useWorkspaceStore((s) => s.openPanel);
  const openDashboard = useWorkspaceStore((s) => s.openDashboard);

  function go(item: { id: string; panelId: string }): void {
    setActive(item.id);
    if (item.panelId === "dashboard") openDashboard();
    else openPanel(item.panelId);
  }

  return (
    <nav className="flex w-14 flex-col items-center border-r border-border bg-bg-panel py-3">
      <div className="mb-4 flex h-8 w-8 items-center justify-center rounded-md bg-accent/15 font-mono text-sm font-bold text-accent">
        B
      </div>
      <div className="flex flex-1 flex-col gap-1">
        {ITEMS.map((item) => (
          <button
            key={item.id}
            title={item.label}
            onClick={() => go(item)}
            className={cn(
              "no-drag flex h-10 w-10 items-center justify-center rounded-md transition-colors",
              item.id === active
                ? "bg-bg-elevated text-accent"
                : "text-text-faint hover:bg-bg-hover hover:text-text",
            )}
          >
            <item.icon className="h-5 w-5" />
          </button>
        ))}
      </div>
      <button
        title="Settings"
        onClick={() => go({ id: "settings", panelId: "settings" })}
        className={cn(
          "no-drag flex h-10 w-10 items-center justify-center rounded-md transition-colors",
          active === "settings"
            ? "bg-bg-elevated text-accent"
            : "text-text-faint hover:bg-bg-hover hover:text-text",
        )}
      >
        <Settings className="h-5 w-5" />
      </button>
    </nav>
  );
}
