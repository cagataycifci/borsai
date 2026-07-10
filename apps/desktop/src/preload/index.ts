import { contextBridge, ipcRenderer } from "electron";

export type EngineStatus = "starting" | "ready" | "error" | "stopped";

export interface EngineInfo {
  url: string;
  status: EngineStatus;
}

/**
 * The privileged surface exposed to the renderer. This is the ONLY bridge
 * between the sandboxed UI and the main process. Secrets never cross it; the
 * renderer references the engine by URL and the engine resolves keys internally.
 */
const api = {
  /** Current engine URL + status (resolved on demand). */
  getEngineInfo: (): Promise<EngineInfo> => ipcRenderer.invoke("engine:getInfo"),

  /** Subscribe to engine status changes. Returns an unsubscribe function. */
  onEngineStatus: (cb: (info: EngineInfo) => void): (() => void) => {
    const listener = (_: unknown, info: EngineInfo) => cb(info);
    ipcRenderer.on("engine:status", listener);
    return () => ipcRenderer.removeListener("engine:status", listener);
  },

  /** Show a native OS notification. */
  notify: (title: string, body: string): Promise<void> =>
    ipcRenderer.invoke("notify", { title, body }),

  platform: process.platform,
};

contextBridge.exposeInMainWorld("borsa", api);

export type BorsaApi = typeof api;
