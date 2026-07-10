import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, RefreshCw } from "lucide-react";
import { api } from "../lib/api";
import { useEngineStore } from "../store/useEngineStore";
import { cn } from "../lib/cn";

/** Shows the local symbol-universe size with a one-click refresh. */
export function UniverseBadge(): JSX.Element | null {
  const engineReady = useEngineStore((s) => s.status === "ready");
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["universe-stats"],
    queryFn: ({ signal }) => api.getUniverseStats(signal),
    enabled: engineReady,
    staleTime: 60_000,
  });

  const refresh = useMutation({
    mutationFn: api.refreshUniverse,
    onSuccess: (stats) => queryClient.setQueryData(["universe-stats"], stats),
  });

  if (!engineReady) return null;

  const total = data?.total ?? 0;
  const breakdown = data
    ? Object.entries(data)
        .filter(([k]) => k !== "total")
        .map(([k, v]) => `${k}: ${v.toLocaleString()}`)
        .join(" · ")
    : "";

  return (
    <button
      onClick={() => refresh.mutate()}
      disabled={refresh.isPending}
      title={breakdown ? `${breakdown}\nClick to refresh` : "Refresh symbol universe"}
      className="no-drag flex items-center gap-2 rounded-md border border-border bg-bg-elevated px-2.5 py-1 text-2xs text-text-muted hover:border-border-strong"
    >
      <Database className="h-3.5 w-3.5 text-text-faint" />
      <span className="tabular">{total.toLocaleString()}</span>
      <span className="text-text-faint">symbols</span>
      <RefreshCw
        className={cn("h-3 w-3 text-text-faint", refresh.isPending && "animate-spin")}
      />
    </button>
  );
}
