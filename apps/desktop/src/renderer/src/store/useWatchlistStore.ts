import { create } from "zustand";
import { api } from "../lib/api";
import type { Watchlist } from "../lib/contracts";

/**
 * Watchlists are persisted in the engine (Phase 4). This store mirrors the
 * server state and exposes the active watchlist's symbols + active symbol.
 *
 * The original single-list surface (`symbols`, `activeSymbol`, `setActive`,
 * `add`, `remove`) is preserved so existing consumers (WatchPanel, SearchBar,
 * ChartPanel, DetailPanel, the market stream + quote seeder) keep working; those
 * mutators now operate on the active watchlist and persist via the API
 * (optimistic update, reconciled with the server response).
 */
interface WatchlistState {
  watchlists: Watchlist[];
  activeWatchlistId: number | null;
  loaded: boolean;

  // Derived view of the active watchlist (kept in sync after every change).
  symbols: string[];
  activeSymbol: string | null;

  load: () => Promise<void>;
  createWatchlist: (name: string) => Promise<void>;
  renameWatchlist: (id: number, name: string) => Promise<void>;
  deleteWatchlist: (id: number) => Promise<void>;
  setActiveWatchlist: (id: number) => void;

  add: (symbol: string) => void;
  remove: (symbol: string) => void;
  reorder: (symbols: string[]) => void;
  setActive: (symbol: string | null) => void;
}

function symbolsOf(lists: Watchlist[], id: number | null): string[] {
  return lists.find((w) => w.id === id)?.symbols ?? [];
}

export const useWatchlistStore = create<WatchlistState>((set, get) => {
  /** Splice an updated watchlist back in and refresh the derived view. */
  function applyList(wl: Watchlist): void {
    set((st) => {
      const lists = st.watchlists.map((w) => (w.id === wl.id ? wl : w));
      const patch: Partial<WatchlistState> = { watchlists: lists };
      if (wl.id === st.activeWatchlistId) patch.symbols = wl.symbols;
      return patch;
    });
  }

  return {
    watchlists: [],
    activeWatchlistId: null,
    loaded: false,
    symbols: [],
    activeSymbol: null,

    load: async () => {
      const lists = await api.listWatchlists();
      set((st) => {
        const activeId =
          st.activeWatchlistId && lists.some((w) => w.id === st.activeWatchlistId)
            ? st.activeWatchlistId
            : (lists[0]?.id ?? null);
        const symbols = symbolsOf(lists, activeId);
        const activeSymbol =
          st.activeSymbol && symbols.includes(st.activeSymbol)
            ? st.activeSymbol
            : (symbols[0] ?? null);
        return { watchlists: lists, activeWatchlistId: activeId, symbols, activeSymbol, loaded: true };
      });
    },

    createWatchlist: async (name) => {
      const wl = await api.createWatchlist(name);
      set((st) => ({
        watchlists: [...st.watchlists, wl],
        activeWatchlistId: wl.id,
        symbols: wl.symbols,
        activeSymbol: wl.symbols[0] ?? st.activeSymbol,
      }));
    },

    renameWatchlist: async (id, name) => {
      const wl = await api.renameWatchlist(id, name);
      applyList(wl);
    },

    deleteWatchlist: async (id) => {
      await api.deleteWatchlist(id);
      set((st) => {
        const lists = st.watchlists.filter((w) => w.id !== id);
        if (st.activeWatchlistId !== id) return { watchlists: lists };
        const activeId = lists[0]?.id ?? null;
        const symbols = symbolsOf(lists, activeId);
        return {
          watchlists: lists,
          activeWatchlistId: activeId,
          symbols,
          activeSymbol: symbols[0] ?? null,
        };
      });
    },

    setActiveWatchlist: (id) =>
      set((st) => {
        const symbols = symbolsOf(st.watchlists, id);
        const activeSymbol =
          st.activeSymbol && symbols.includes(st.activeSymbol)
            ? st.activeSymbol
            : (symbols[0] ?? null);
        return { activeWatchlistId: id, symbols, activeSymbol };
      }),

    add: (symbol) => {
      const sym = symbol.trim().toUpperCase();
      const { activeWatchlistId } = get();
      if (!sym) return;
      if (activeWatchlistId == null) {
        set({ activeSymbol: sym });
        return;
      }
      // Optimistic: reflect immediately, then reconcile with the server.
      set((st) => {
        const lists = st.watchlists.map((w) =>
          w.id === activeWatchlistId && !w.symbols.includes(sym)
            ? { ...w, symbols: [...w.symbols, sym] }
            : w,
        );
        return { watchlists: lists, symbols: symbolsOf(lists, activeWatchlistId), activeSymbol: sym };
      });
      api
        .addWatchlistItem(activeWatchlistId, sym)
        .then(applyList)
        .catch(() => get().load());
    },

    remove: (symbol) => {
      const sym = symbol.trim().toUpperCase();
      const { activeWatchlistId } = get();
      if (activeWatchlistId == null) return;
      set((st) => {
        const lists = st.watchlists.map((w) =>
          w.id === activeWatchlistId
            ? { ...w, symbols: w.symbols.filter((s) => s !== sym) }
            : w,
        );
        return { watchlists: lists, symbols: symbolsOf(lists, activeWatchlistId) };
      });
      api
        .removeWatchlistItem(activeWatchlistId, sym)
        .then(applyList)
        .catch(() => get().load());
    },

    reorder: (symbols) => {
      const { activeWatchlistId } = get();
      if (activeWatchlistId == null) return;
      set((st) => {
        const lists = st.watchlists.map((w) =>
          w.id === activeWatchlistId ? { ...w, symbols } : w,
        );
        return { watchlists: lists, symbols };
      });
      api
        .reorderWatchlistItems(activeWatchlistId, symbols)
        .then(applyList)
        .catch(() => get().load());
    },

    setActive: (activeSymbol) => set({ activeSymbol }),
  };
});
