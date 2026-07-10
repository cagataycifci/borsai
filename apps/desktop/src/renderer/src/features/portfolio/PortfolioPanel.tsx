import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, RefreshCw, Newspaper } from "lucide-react";
import { api } from "../../lib/api";
import { useEngineStore } from "../../store/useEngineStore";
import { cn } from "../../lib/cn";
import {
  formatNumber,
  formatPercent,
  formatPrice,
  formatRelativeTime,
  trendClass,
} from "../../lib/format";
import type { Holding, PortfolioPosition } from "../../lib/contracts";
import { HoldingForm } from "./HoldingForm";

/** Signed currency amount for P&L (magnitude formatted, explicit sign). */
function signed(value: number | null, currency: string): string {
  if (value == null || !Number.isFinite(value)) return "—";
  const body = formatPrice(Math.abs(value), currency);
  return value < 0 ? `−${body}` : `+${body}`;
}

/** Holdings with live prices, P&L per position, and per-currency totals. */
export function PortfolioPanel(): JSX.Element {
  const ready = useEngineStore((s) => s.status === "ready");
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<Holding | null>(null);
  const [showForm, setShowForm] = useState(false);

  const { data, isFetching, isError } = useQuery({
    queryKey: ["portfolio"],
    queryFn: ({ signal }) => api.getPortfolio(signal),
    enabled: ready,
    refetchInterval: 15_000,
    staleTime: 10_000,
  });

  function invalidate(): void {
    void queryClient.invalidateQueries({ queryKey: ["portfolio"] });
  }

  async function handleDelete(id: number): Promise<void> {
    await api.deleteHolding(id);
    invalidate();
  }

  const positions = data?.positions ?? [];
  const totals = data?.totals ?? [];

  // Auto-refreshing news filtered to symbols we actually hold.
  const ownedBare = useMemo(
    () => new Set(positions.map((p) => p.holding.symbol.replace(/\.IS$/, ""))),
    [positions],
  );
  const { data: allNews = [] } = useQuery({
    queryKey: ["news", "market"],
    queryFn: ({ signal }) => api.getNews(80, signal),
    enabled: ready && ownedBare.size > 0,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
  const holdingsNews = useMemo(
    () =>
      allNews
        .filter((a) =>
          a.symbols.some((s) => ownedBare.has(s.replace(/\.IS$/, ""))),
        )
        .slice(0, 8),
    [allNews, ownedBare],
  );

  return (
    <div className="flex h-full flex-col bg-bg-panel">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <span className="text-2xs font-semibold uppercase tracking-wider text-text-muted">
          Portfolio
        </span>
        {isFetching && <RefreshCw className="h-3 w-3 animate-spin text-text-faint" />}
        <button
          onClick={() => {
            setEditing(null);
            setShowForm(true);
          }}
          className="no-drag ml-auto flex items-center gap-1 rounded-md border border-accent/40 bg-accent/10 px-2 py-1 text-2xs text-accent hover:bg-accent/20"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Holding
        </button>
      </div>

      {/* Per-currency totals */}
      {totals.length > 0 && (
        <div className="flex flex-wrap gap-2 border-b border-border px-3 py-2">
          {totals.map((t) => (
            <div
              key={t.currency}
              className="rounded-md border border-border bg-bg-elevated px-3 py-1.5"
            >
              <div className="text-[10px] uppercase tracking-wide text-text-faint">
                {t.currency} · Market Value
              </div>
              <div className="tabular text-sm font-semibold text-text">
                {formatPrice(t.market_value, t.currency)}
              </div>
              <div className={cn("tabular text-2xs", trendClass(t.unrealized_pnl))}>
                {signed(t.unrealized_pnl, t.currency)} ({formatPercent(t.unrealized_pnl_pct)})
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-auto">
        {isError && (
          <div className="flex h-full items-center justify-center text-text-faint">
            Failed to load portfolio.
          </div>
        )}
        {!isError && positions.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-text-faint">
            <p className="text-sm">No holdings yet.</p>
            <button
              onClick={() => {
                setEditing(null);
                setShowForm(true);
              }}
              className="no-drag rounded-md border border-accent/40 bg-accent/10 px-3 py-1.5 text-2xs text-accent hover:bg-accent/20"
            >
              Add your first holding
            </button>
          </div>
        )}
        {positions.length > 0 && (
          <table className="w-full border-collapse text-2xs">
            <thead className="sticky top-0 bg-bg-panel text-text-faint">
              <tr className="border-b border-border text-left">
                <th className="px-3 py-1.5 font-medium">Symbol</th>
                <th className="px-2 py-1.5 text-right font-medium">Qty</th>
                <th className="px-2 py-1.5 text-right font-medium">Avg Cost</th>
                <th className="px-2 py-1.5 text-right font-medium">Price</th>
                <th className="px-2 py-1.5 text-right font-medium">Mkt Value</th>
                <th className="px-2 py-1.5 text-right font-medium">Unreal. P&L</th>
                <th className="px-2 py-1.5 text-right font-medium">Day P&L</th>
                <th className="px-2 py-1.5" />
              </tr>
            </thead>
            <tbody>
              {positions.map((p: PortfolioPosition) => {
                const ccy = p.holding.currency;
                return (
                  <tr key={p.holding.id} className="group border-b border-border/60">
                    <td className="px-3 py-1.5">
                      <div className="font-mono text-sm text-text">
                        {p.holding.symbol.replace(/\.IS$/, "")}
                      </div>
                      {(p.holding.target_price != null || p.holding.stop_loss != null) && (
                        <div className="text-[10px] text-text-faint">
                          {p.holding.target_price != null &&
                            `T ${formatPrice(p.holding.target_price, ccy)}`}
                          {p.holding.target_price != null &&
                            p.holding.stop_loss != null &&
                            " · "}
                          {p.holding.stop_loss != null &&
                            `S ${formatPrice(p.holding.stop_loss, ccy)}`}
                        </div>
                      )}
                    </td>
                    <td className="tabular px-2 py-1.5 text-right text-text">
                      {formatNumber(p.holding.quantity)}
                    </td>
                    <td className="tabular px-2 py-1.5 text-right text-text-muted">
                      {formatPrice(p.holding.avg_cost, ccy)}
                    </td>
                    <td className="tabular px-2 py-1.5 text-right text-text">
                      {formatPrice(p.price, ccy)}
                    </td>
                    <td className="tabular px-2 py-1.5 text-right text-text">
                      {formatPrice(p.market_value, ccy)}
                    </td>
                    <td
                      className={cn(
                        "tabular px-2 py-1.5 text-right",
                        trendClass(p.unrealized_pnl),
                      )}
                    >
                      {signed(p.unrealized_pnl, ccy)}
                      <div className="text-[10px]">{formatPercent(p.unrealized_pnl_pct)}</div>
                    </td>
                    <td
                      className={cn("tabular px-2 py-1.5 text-right", trendClass(p.day_pnl))}
                    >
                      {signed(p.day_pnl, ccy)}
                    </td>
                    <td className="px-2 py-1.5">
                      <div className="flex items-center justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                        <button
                          onClick={() => {
                            setEditing(p.holding);
                            setShowForm(true);
                          }}
                          title="Edit"
                          className="no-drag text-text-faint hover:text-text"
                        >
                          <Pencil className="h-3 w-3" />
                        </button>
                        <button
                          onClick={() => void handleDelete(p.holding.id)}
                          title="Delete"
                          className="no-drag text-text-faint hover:text-down"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {holdingsNews.length > 0 && (
        <div className="max-h-48 shrink-0 overflow-auto border-t border-border">
          <div className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-text-faint">
            <Newspaper className="h-3 w-3" />
            News on your holdings
          </div>
          {holdingsNews.map((a) => (
            <a
              key={a.id}
              href={a.url}
              target="_blank"
              rel="noreferrer"
              className="group block border-b border-border/40 px-3 py-1.5 hover:bg-bg-hover"
            >
              <div className="line-clamp-1 text-2xs text-text group-hover:text-accent">
                {a.title}
              </div>
              <div className="flex items-center gap-1.5 text-[10px] text-text-faint">
                <span className="text-text-muted">{a.source}</span>
                <span>·</span>
                <span>{formatRelativeTime(a.published_at)}</span>
                {a.symbols
                  .filter((s) => ownedBare.has(s.replace(/\.IS$/, "")))
                  .slice(0, 3)
                  .map((s) => (
                    <span
                      key={s}
                      className="rounded bg-bg-elevated px-1 font-mono text-[10px] text-text-muted"
                    >
                      {s.replace(/\.IS$/, "")}
                    </span>
                  ))}
              </div>
            </a>
          ))}
        </div>
      )}

      <div className="border-t border-border px-3 py-1.5 text-[10px] text-text-faint">
        Live P&L · per-currency totals (no FX conversion) · Not financial advice
      </div>

      {showForm && (
        <HoldingForm
          holding={editing}
          onClose={() => setShowForm(false)}
          onSaved={() => {
            setShowForm(false);
            invalidate();
          }}
        />
      )}
    </div>
  );
}
