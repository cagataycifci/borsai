import { Sparkles } from "lucide-react";
import { useQuotesStore } from "../../store/useQuotesStore";
import { useWatchlistStore } from "../../store/useWatchlistStore";
import { useWorkspaceStore } from "../../store/useWorkspaceStore";
import { cn } from "../../lib/cn";
import {
  formatCompact,
  formatNumber,
  formatPercent,
  formatPrice,
  trendClass,
} from "../../lib/format";
import { ExchangeBadge } from "../../components/ExchangeBadge";
import type { Quote } from "../../lib/contracts";

interface Metric {
  label: string;
  value: string;
}

function metricsFor(q: Quote): Metric[] {
  return [
    { label: "Open", value: formatPrice(q.open, q.currency) },
    { label: "Prev Close", value: formatPrice(q.previous_close, q.currency) },
    { label: "Day High", value: formatPrice(q.day_high, q.currency) },
    { label: "Day Low", value: formatPrice(q.day_low, q.currency) },
    { label: "52W High", value: formatPrice(q.week52_high, q.currency) },
    { label: "52W Low", value: formatPrice(q.week52_low, q.currency) },
    { label: "Volume", value: formatCompact(q.volume) },
    { label: "Market Cap", value: formatCompact(q.market_cap) },
    { label: "P/E", value: formatNumber(q.pe_ratio) },
    { label: "EPS", value: formatNumber(q.eps) },
    {
      label: "Div Yield",
      value: q.dividend_yield != null ? `${q.dividend_yield.toFixed(2)}%` : "—",
    },
    { label: "Sector", value: q.sector ?? "—" },
  ];
}

/** Detailed quote view for the active symbol. */
export function DetailPanel(): JSX.Element {
  const activeSymbol = useWatchlistStore((s) => s.activeSymbol);
  const quote = useQuotesStore((s) => (activeSymbol ? s.quotes[activeSymbol] : undefined));
  const openPanel = useWorkspaceStore((s) => s.openPanel);

  if (!activeSymbol) {
    return (
      <div className="flex h-full items-center justify-center bg-bg-panel text-text-faint">
        Select a symbol
      </div>
    );
  }

  if (!quote) {
    return (
      <div className="flex h-full items-center justify-center bg-bg-panel text-text-faint">
        Loading {activeSymbol}…
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-auto bg-bg-panel p-5">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-mono text-2xl font-semibold text-text">
              {quote.display_symbol}
            </h1>
            <ExchangeBadge exchange={quote.exchange} />
          </div>
          <p className="mt-0.5 text-sm text-text-muted">{quote.name ?? "—"}</p>
          {quote.industry && (
            <p className="text-2xs text-text-faint">{quote.industry}</p>
          )}
        </div>
        <button
          onClick={() => openPanel("ai")}
          className="no-drag flex items-center gap-2 rounded-md border border-accent/40 bg-accent/10 px-3 py-1.5 text-sm text-accent hover:bg-accent/20"
          title="Open AI analysis"
        >
          <Sparkles className="h-4 w-4" />
          AI Analysis
        </button>
      </div>

      <div className="mt-5 flex items-baseline gap-3">
        <span className="tabular text-4xl font-semibold text-text">
          {formatPrice(quote.price, quote.currency)}
        </span>
        <span className={cn("tabular text-lg", trendClass(quote.change))}>
          {quote.change != null
            ? `${quote.change > 0 ? "+" : ""}${quote.change.toFixed(2)}`
            : "—"}{" "}
          ({formatPercent(quote.change_percent)})
        </span>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-3 lg:grid-cols-4">
        {metricsFor(quote).map((m) => (
          <div key={m.label} className="border-b border-border/60 pb-2">
            <div className="text-2xs uppercase tracking-wide text-text-faint">
              {m.label}
            </div>
            <div className="tabular text-sm text-text">{m.value}</div>
          </div>
        ))}
      </div>

      <div className="mt-auto pt-4 text-2xs text-text-faint">
        Source: {quote.source ?? "—"} · Delayed data · Not financial advice
      </div>
    </div>
  );
}
