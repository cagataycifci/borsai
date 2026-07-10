import { useEffect } from "react";
import { useEngineStore } from "../store/useEngineStore";
import { useWatchlistStore } from "../store/useWatchlistStore";

/**
 * Loads persisted watchlists from the engine once it's ready. The engine seeds a
 * starter watchlist on first run, so the UI is never empty.
 */
export function useWatchlistBootstrap(): void {
  const status = useEngineStore((s) => s.status);
  const loaded = useWatchlistStore((s) => s.loaded);
  const load = useWatchlistStore((s) => s.load);

  useEffect(() => {
    if (status === "ready" && !loaded) {
      load().catch(() => {
        /* transient; retried when the engine status next flips to ready */
      });
    }
  }, [status, loaded, load]);
}
