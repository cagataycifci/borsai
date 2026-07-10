import { X } from "lucide-react";
import { useQuotesStore } from "../../store/useQuotesStore";
import { useWatchlistStore } from "../../store/useWatchlistStore";
import { cn } from "../../lib/cn";
import { formatPercent, formatPrice, trendClass } from "../../lib/format";
import { ExchangeBadge } from "../../components/ExchangeBadge";

/** A live, clickable list of watched symbols. Drives the active selection. */
export function WatchPanel(): JSX.Element {
  const symbols = useWatchlistStore((s) => s.symbols);
  const activeSymbol = useWatchlistStore((s) => s.activeSymbol);
  const setActive = useWatchlistStore((s) => s.setActive);
  const remove = useWatchlistStore((s) => s.remove);
  const quotes = useQuotesStore((s) => s.quotes);

  return (
    <div className="flex h-full flex-col bg-bg-panel">
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <span className="text-2xs font-semibold uppercase tracking-wider text-text-muted">
          Watchlist
        </span>
        <span className="text-2xs text-text-faint">{symbols.length}</span>
      </div>
      <div className="flex-1 overflow-auto">
        {symbols.map((symbol) => {
          const q = quotes[symbol];
          const active = symbol === activeSymbol;
          return (
            <div
              key={symbol}
              onClick={() => setActive(symbol)}
              className={cn(
                "group flex cursor-pointer items-center justify-between gap-2 border-l-2 px-3 py-2 hover:bg-bg-hover",
                active
                  ? "border-accent bg-bg-elevated"
                  : "border-transparent",
              )}
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm text-text">
                    {q?.display_symbol ?? symbol.replace(/\.IS$/, "")}
                  </span>
                  {q && <ExchangeBadge exchange={q.exchange} />}
                </div>
                <div className="truncate text-2xs text-text-faint">
                  {q?.name ?? "—"}
                </div>
              </div>
              <div className="flex items-center gap-2 text-right">
                <div>
                  <div className="tabular text-sm text-text">
                    {q ? formatPrice(q.price, q.currency) : "…"}
                  </div>
                  <div className={cn("tabular text-2xs", trendClass(q?.change_percent))}>
                    {q ? formatPercent(q.change_percent) : ""}
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    remove(symbol);
                  }}
                  className="no-drag opacity-0 transition-opacity group-hover:opacity-100"
                  title="Remove"
                >
                  <X className="h-3.5 w-3.5 text-text-faint hover:text-down" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
