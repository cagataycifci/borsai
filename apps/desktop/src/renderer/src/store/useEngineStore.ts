import { create } from "zustand";

export type EngineStatus = "starting" | "ready" | "error" | "stopped";

interface EngineState {
  url: string;
  status: EngineStatus;
  streamConnected: boolean;
  setEngine: (url: string, status: EngineStatus) => void;
  setStreamConnected: (connected: boolean) => void;
}

export const useEngineStore = create<EngineState>((set) => ({
  url: "http://127.0.0.1:8787",
  status: "starting",
  streamConnected: false,
  setEngine: (url, status) => set({ url, status }),
  setStreamConnected: (streamConnected) => set({ streamConnected }),
}));
