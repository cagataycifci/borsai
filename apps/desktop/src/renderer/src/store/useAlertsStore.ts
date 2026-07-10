import { create } from "zustand";
import type { AlertEvent } from "../lib/contracts";

const MAX_EVENTS = 100;

interface AlertsState {
  /** Most-recent triggered alert events, newest first. */
  events: AlertEvent[];
  /** Count of events received since the panel last cleared them (badge). */
  unseen: number;
  addEvent: (event: AlertEvent) => void;
  /** Seed the feed from the engine (recent history) without bumping `unseen`. */
  setEvents: (events: AlertEvent[]) => void;
  clearUnseen: () => void;
}

export const useAlertsStore = create<AlertsState>((set) => ({
  events: [],
  unseen: 0,
  addEvent: (event) =>
    set((s) => ({
      events: [event, ...s.events].slice(0, MAX_EVENTS),
      unseen: s.unseen + 1,
    })),
  setEvents: (events) => set({ events: events.slice(0, MAX_EVENTS) }),
  clearUnseen: () => set({ unseen: 0 }),
}));
