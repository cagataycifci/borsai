import { useEffect } from "react";
import { setEngineBaseUrl } from "../lib/api";
import { useEngineStore } from "../store/useEngineStore";

/**
 * Resolves the engine URL/status from the preload bridge on mount and keeps the
 * engine store in sync with main-process status updates.
 */
export function useEngineBootstrap(): void {
  const setEngine = useEngineStore((s) => s.setEngine);

  useEffect(() => {
    let unsub: (() => void) | undefined;

    void window.borsa.getEngineInfo().then((info) => {
      setEngineBaseUrl(info.url);
      setEngine(info.url, info.status);
    });

    unsub = window.borsa.onEngineStatus((info) => {
      setEngineBaseUrl(info.url);
      setEngine(info.url, info.status);
    });

    return () => unsub?.();
  }, [setEngine]);
}
