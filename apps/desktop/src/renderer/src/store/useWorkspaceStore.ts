import { create } from "zustand";
import type { DockviewApi } from "dockview";
import {
  addRegisteredPanel,
  buildDefaultLayout,
  DEFAULT_LAYOUT_IDS,
} from "../features/workspace/panelRegistry";

interface WorkspaceState {
  /** The live dockview api, or null before the Workspace mounts. */
  api: DockviewApi | null;
  /** Ids of currently open panels (kept in sync with dockview events). */
  openIds: string[];

  setApi: (api: DockviewApi | null) => void;
  /** Recompute openIds from the live api (called on add/remove events). */
  syncOpen: () => void;
  /** Focus a panel if open, otherwise create it. */
  openPanel: (id: string) => void;
  /** Restore the default Dashboard panels (used by the Dashboard nav button). */
  openDashboard: () => void;
  /** Wipe the layout and rebuild the default arrangement. */
  resetLayout: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  api: null,
  openIds: [],

  setApi: (api) => set({ api, openIds: api ? api.panels.map((p) => p.id) : [] }),

  syncOpen: () => {
    const { api } = get();
    set({ openIds: api ? api.panels.map((p) => p.id) : [] });
  },

  openPanel: (id) => {
    const { api } = get();
    if (!api) return;
    const existing = api.getPanel(id);
    if (existing) {
      existing.api.setActive();
    } else {
      addRegisteredPanel(api, id);
    }
  },

  openDashboard: () => {
    const { api, resetLayout } = get();
    if (!api) return;
    const anyOpen = DEFAULT_LAYOUT_IDS.some((id) => api.getPanel(id));
    if (!anyOpen) {
      resetLayout();
      return;
    }
    // Re-add any missing dashboard panels relative to the chart, then focus it.
    if (!api.getPanel("chart")) addRegisteredPanel(api, "chart");
    if (!api.getPanel("detail")) {
      addRegisteredPanel(api, "detail", { referencePanel: "chart", direction: "below" });
    }
    if (!api.getPanel("watch")) {
      addRegisteredPanel(api, "watch", { referencePanel: "chart", direction: "left" });
    }
    api.getPanel("chart")?.api.setActive();
  },

  resetLayout: () => {
    const { api } = get();
    if (!api) return;
    api.clear();
    buildDefaultLayout(api);
  },
}));
