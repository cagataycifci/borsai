import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, ExternalLink } from "lucide-react";
import { api } from "../../lib/api";
import { useEngineStore } from "../../store/useEngineStore";
import { useWatchlistStore } from "../../store/useWatchlistStore";
import { cn } from "../../lib/cn";
import { formatRelativeTime } from "../../lib/format";

type Mode = "market" | "symbol";

/**
 * Aggregated news feed. Toggles between market-wide headlines and news for the
 * active symbol. Articles open in the OS browser (the main process routes
 * `target="_blank"` to `shell.openExternal`).
 */
export function NewsPanel(): JSX.Element {
  const ready = useEngineStore((s) => s.status === "ready");
  const activeSymbol = useWatchlistStore((s) => s.activeSymbol);
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<Mode>("market");

  const symbolMode = mode === "symbol" && !!activeSymbol;

  const { data = [], isFetching, isError, refetch } = useQuery({
    queryKey: symbolMode ? ["news", "symbol", activeSymbol] : ["news", "market"],
    queryFn: ({ signal }) =>
      symbolMode
        ? api.getNewsForSymbol(activeSymbol!, 30, signal)
        : api.getNews(60, signal),
    enabled: ready && (mode === "market" || !!activeSymbol),
    staleTime: 60_000,
  });

  async function refresh(): Promise<void> {
    if (mode === "market") {
      await api.refreshNews();
      void queryClient.invalidateQueries({ queryKey: ["news", "market"] });
    } else {
      void refetch();
    }
  }

  return (
    <div className="flex h-full flex-col bg-bg-panel">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <span className="text-2xs font-semibold uppercase tracking-wider text-text-muted">
          News
        </span>
        <div className="flex items-center gap-0.5 rounded-md border border-border bg-bg-elevated p-0.5">
          {(["market", "symbol"] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={cn(
                "rounded px-2 py-0.5 text-2xs font-medium capitalize transition-colors",
                mode === m ? "bg-accent/20 text-accent" : "text-text-muted hover:text-text",
              )}
            >
              {m === "symbol" ? (activeSymbol?.replace(/\.IS$/, "") ?? "Symbol") : "Market"}
            </button>
          ))}
        </div>
        <button
          onClick={() => void refresh()}
          title="Refresh"
          className="no-drag ml-auto flex items-center gap-1 rounded-md border border-border bg-bg-elevated px-2 py-1 text-2xs text-text-muted hover:text-text"
        >
          <RefreshCw className={cn("h-3 w-3", isFetching && "animate-spin")} />
          Refresh
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        {mode === "symbol" && !activeSymbol && (
          <div className="flex h-full items-center justify-center text-text-faint">
            Select a symbol to see its news.
          </div>
        )}
        {isError && (
          <div className="flex h-full items-center justify-center text-text-faint">
            Failed to load news.
          </div>
        )}
        {!isError && !isFetching && data.length === 0 && (
          <div className="flex h-full items-center justify-center text-text-faint">
            No news yet — try Refresh.
          </div>
        )}
        {data.map((article) => (
          <a
            key={article.id}
            href={article.url}
            target="_blank"
            rel="noreferrer"
            className="group block border-b border-border/60 px-3 py-2.5 hover:bg-bg-hover"
          >
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-sm leading-snug text-text group-hover:text-accent">
                {article.title}
              </h3>
              <ExternalLink className="mt-0.5 h-3 w-3 shrink-0 text-text-faint opacity-0 group-hover:opacity-100" />
            </div>
            {article.summary && (
              <p className="mt-1 line-clamp-2 text-2xs text-text-muted">{article.summary}</p>
            )}
            <div className="mt-1.5 flex items-center gap-2 text-2xs text-text-faint">
              <span className="text-text-muted">{article.source}</span>
              <span>·</span>
              <span>{formatRelativeTime(article.published_at)}</span>
              {article.symbols.slice(0, 4).map((sym) => (
                <span
                  key={sym}
                  className="rounded bg-bg-elevated px-1 py-0.5 font-mono text-[10px] text-text-muted"
                >
                  {sym.replace(/\.IS$/, "")}
                </span>
              ))}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
