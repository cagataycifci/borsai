import { DockviewReact, type DockviewReadyEvent } from "dockview";
import "dockview/dist/styles/dockview.css";
import { RotateCcw } from "lucide-react";
import { buildDefaultLayout, components } from "../features/workspace/panelRegistry";
import { useWorkspaceStore } from "../store/useWorkspaceStore";

/**
 * The dockable workspace (Bloomberg/TradingView-style). Panels can be dragged,
 * split, stacked into tabs, resized, floated and closed. The live dockview api
 * is published to {@link useWorkspaceStore} so the Sidebar and the TitleBar
 * "Panels" menu can open/focus panels and reset the layout. If every panel is
 * closed, an empty-state overlay offers a one-click layout restore so the app
 * can never get stuck blank.
 */
export function Workspace(): JSX.Element {
  const setApi = useWorkspaceStore((s) => s.setApi);
  const syncOpen = useWorkspaceStore((s) => s.syncOpen);
  const resetLayout = useWorkspaceStore((s) => s.resetLayout);
  const isEmpty = useWorkspaceStore((s) => s.openIds.length === 0);

  function onReady(event: DockviewReadyEvent): void {
    const api = event.api;
    // Guard against StrictMode/double-ready: only seed when truly empty.
    if (api.panels.length === 0) buildDefaultLayout(api);
    setApi(api);
    api.onDidAddPanel(() => syncOpen());
    api.onDidRemovePanel(() => syncOpen());
  }

  return (
    <div className="relative h-full w-full">
      <DockviewReact
        className="dockview-theme-borsa h-full w-full"
        components={components}
        onReady={onReady}
      />
      {isEmpty && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-4 bg-bg">
          <div className="text-center">
            <p className="text-sm font-medium text-text">All panels are closed</p>
            <p className="mt-1 text-2xs text-text-muted">
              Reopen panels from the “Panels” menu in the top bar, or restore the
              default layout.
            </p>
          </div>
          <button
            onClick={resetLayout}
            className="no-drag flex items-center gap-2 rounded-md border border-accent/40 bg-accent/10 px-4 py-2 text-sm text-accent hover:bg-accent/20"
          >
            <RotateCcw className="h-4 w-4" />
            Reset Layout
          </button>
        </div>
      )}
    </div>
  );
}
