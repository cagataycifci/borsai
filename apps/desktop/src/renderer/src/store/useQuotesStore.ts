import { create } from "zustand";
import type { Quote } from "../lib/contracts";

interface QuotesState {
  /** Latest quote per canonical symbol. */
  quotes: Record<string, Quote>;
  upsertQuote: (quote: Quote) => void;
}

export const useQuotesStore = create<QuotesState>((set) => ({
  quotes: {},
  upsertQuote: (quote) =>
    set((state) => ({ quotes: { ...state.quotes, [quote.symbol]: quote } })),
}));
