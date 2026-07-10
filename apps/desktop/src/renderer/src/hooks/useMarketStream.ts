import { useEffect, useRef } from "react";
import { QuoteStream } from "../lib/ws";
import { useEngineStore } from "../store/useEngineStore";
import { useQuotesStore } from "../store/useQuotesStore";
import { useWatchlistStore } from "../store/useWatchlistStore";
import { useAlertsStore } from "../store/useAlertsStore";

/**
 * Owns the single QuoteStream connection for the app. Mounts once (in the shell),
 * forwards quote frames into the quotes store, and keeps the subscription in sync
 * with the watchlist + active symbol.
 */
export function useMarketStream(): void {
  const streamRef = useRef<QuoteStream | null>(null);
  const url = useEngineStore((s) => s.url);
  const engineStatus = useEngineStore((s) => s.status);
  const setStreamConnected = useEngineStore((s) => s.setStreamConnected);
  const upsertQuote = useQuotesStore((s) => s.upsertQuote);
  const addAlertEvent = useAlertsStore((s) => s.addEvent);
  const symbols = useWatchlistStore((s) => s.symbols);
  const activeSymbol = useWatchlistStore((s) => s.activeSymbol);

  // Create / connect the stream once the engine is ready.
  useEffect(() => {
    if (engineStatus !== "ready") return;

    if (!streamRef.current) {
      streamRef.current = new QuoteStream(url);
    } else {
      streamRef.current.setBaseUrl(url);
    }
    const stream = streamRef.current;

    const offFrame = stream.onFrame((frame) => {
      if (frame.type === "quote") {
        upsertQuote(frame.data);
      } else if (frame.type === "alert") {
        addAlertEvent(frame.data);
        const bare = frame.data.symbol.replace(/\.IS$/, "");
        void window.borsa?.notify?.(`Alert · ${bare}`, frame.data.message);
      }
    });
    const offStatus = stream.onStatus(setStreamConnected);
    stream.connect();

    return () => {
      offFrame();
      offStatus();
    };
  }, [engineStatus, url, upsertQuote, addAlertEvent, setStreamConnected]);

  // Keep the subscription set aligned with the watchlist + active symbol.
  useEffect(() => {
    const stream = streamRef.current;
    if (!stream) return;
    const wanted = new Set(symbols);
    if (activeSymbol) wanted.add(activeSymbol);
    stream.setSymbols([...wanted]);
  }, [symbols, activeSymbol]);

  // Tear down on unmount.
  useEffect(() => {
    return () => {
      streamRef.current?.close();
      streamRef.current = null;
    };
  }, []);
}
