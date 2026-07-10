import { useEffect, useRef } from "react";
import { api } from "../lib/api";
import { useEngineStore } from "../store/useEngineStore";
import { useQuotesStore } from "../store/useQuotesStore";
import { useWatchlistStore } from "../store/useWatchlistStore";

/**
 * Seeds the quotes store via REST for any watched/active symbol not yet present,
 * so the UI paints immediately instead of waiting for the first WebSocket frame.
 * Each symbol is fetched at most once here; the stream keeps it fresh afterwards.
 */
export function useQuoteSeeder(): void {
  const engineStatus = useEngineStore((s) => s.status);
  const symbols = useWatchlistStore((s) => s.symbols);
  const activeSymbol = useWatchlistStore((s) => s.activeSymbol);
  const upsertQuote = useQuotesStore((s) => s.upsertQuote);
  const seeded = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (engineStatus !== "ready") return;
    const wanted = new Set(symbols);
    if (activeSymbol) wanted.add(activeSymbol);

    const missing = [...wanted].filter((s) => !seeded.current.has(s));
    if (missing.length === 0) return;

    let cancelled = false;
    for (const symbol of missing) {
      seeded.current.add(symbol);
      api
        .getQuote(symbol)
        .then((quote) => {
          if (!cancelled) upsertQuote(quote);
        })
        .catch(() => {
          // Allow a later retry if this symbol failed (e.g. transient).
          seeded.current.delete(symbol);
        });
    }
    return () => {
      cancelled = true;
    };
  }, [engineStatus, symbols, activeSymbol, upsertQuote]);
}
