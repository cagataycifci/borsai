/**
 * Central registry of dockview panels. Everything that can appear in the
 * Workspace — real feature panels and "under construction" placeholders for
 * future phases — is described here once, so the Sidebar, the TitleBar "Panels"
 * menu, and the layout/reset logic all stay in sync from a single source.
 */
import type { DockviewApi, IDockviewPanelProps } from "dockview";
import { WatchPanel } from "../dashboard/WatchPanel";
import { DetailPanel } from "../dashboard/DetailPanel";
import { ChartPanel } from "../charts/ChartPanel";
import { WatchlistsPanel } from "../watchlists/WatchlistsPanel";
import { PortfolioPanel } from "../portfolio/PortfolioPanel";
import { NewsPanel } from "../news/NewsPanel";
import { AiPanel } from "../ai/AiPanel";
import { SettingsPanel } from "../settings/SettingsPanel";
import { AlertsPanel } from "../alerts/AlertsPanel";
import { ReportsPanel } from "../reports/ReportsPanel";
import { CommentatorPanel } from "../commentator/CommentatorPanel";

export interface PanelDef {
  id: string;
  title: string;
  /** When set, the panel is a placeholder for a not-yet-built module. */
  phase?: number;
}

/** Ordered list shown in the Panels menu; ids match dockview panel ids. */
export const PANELS: PanelDef[] = [
  { id: "chart", title: "Chart" },
  { id: "detail", title: "Quote" },
  { id: "watch", title: "Watchlist" },
  { id: "watchlists", title: "Watchlists" },
  { id: "portfolio", title: "Portfolio" },
  { id: "news", title: "News" },
  { id: "ai", title: "AI Analysis" },
  { id: "alerts", title: "Alerts" },
  { id: "reports", title: "Reports" },
  { id: "commentator", title: "Commentator" },
  { id: "settings", title: "Settings" },
];

export const PANEL_MAP: Record<string, PanelDef> = Object.fromEntries(
  PANELS.map((p) => [p.id, p]),
);

/** The panels that make up the default "Dashboard" layout. */
export const DEFAULT_LAYOUT_IDS = ["chart", "detail", "watch"] as const;

/** Centered placeholder for modules arriving in a later phase. */
function Placeholder(props: IDockviewPanelProps): JSX.Element {
  const title = (props.params?.title as string | undefined) ?? "Module";
  const phase = props.params?.phase as number | undefined;
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 bg-bg-panel p-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-border bg-bg-elevated text-text-faint">
        🚧
      </div>
      <div className="text-base font-semibold text-text">{title}</div>
      <div className="max-w-xs text-sm text-text-muted">
        This module is under construction
        {phase ? ` (Coming in Phase ${phase})` : ""}.
      </div>
    </div>
  );
}

/** dockview component map — feature panels plus the shared placeholder. */
export const components: Record<string, React.FC<IDockviewPanelProps>> = {
  chart: () => <ChartPanel />,
  detail: () => <DetailPanel />,
  watch: () => <WatchPanel />,
  watchlists: () => <WatchlistsPanel />,
  portfolio: () => <PortfolioPanel />,
  news: () => <NewsPanel />,
  ai: () => <AiPanel />,
  settings: () => <SettingsPanel />,
  alerts: () => <AlertsPanel />,
  reports: () => <ReportsPanel />,
  commentator: () => <CommentatorPanel />,
  placeholder: (props) => <Placeholder {...props} />,
};

type PanelPosition = {
  referencePanel: string;
  direction: "left" | "right" | "above" | "below" | "within";
};

/** Add a registered panel by id, routing placeholders to the shared component. */
export function addRegisteredPanel(
  api: DockviewApi,
  id: string,
  position?: PanelPosition,
): void {
  const def = PANEL_MAP[id];
  if (!def) return;
  api.addPanel({
    id,
    component: def.phase ? "placeholder" : id,
    title: def.title,
    params: def.phase ? { title: def.title, phase: def.phase } : undefined,
    position,
  });
}

/** Build the default Dashboard arrangement (chart + quote below + watch left). */
export function buildDefaultLayout(api: DockviewApi): void {
  addRegisteredPanel(api, "chart");
  addRegisteredPanel(api, "detail", { referencePanel: "chart", direction: "below" });
  addRegisteredPanel(api, "watch", { referencePanel: "chart", direction: "left" });

  // Give the watchlist a fixed-ish width and let the chart own the height.
  queueMicrotask(() => {
    api.getPanel("watch")?.api.setSize({ width: 300 });
    api.getPanel("detail")?.api.setSize({ height: 280 });
  });
}
