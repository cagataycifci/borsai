import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Users } from "lucide-react";
import { api } from "../../lib/api";
import { useEngineStore } from "../../store/useEngineStore";
import { useWatchlistStore } from "../../store/useWatchlistStore";
import { cn } from "../../lib/cn";

/**
 * Commentator consensus view — attributed news opinions with agreement score
 * (Phase 9).
 */
export function CommentatorPanel(): JSX.Element {
  const ready = useEngineStore((s) => s.status === "ready");
  const activeSymbol = useWatchlistStore((s) => s.activeSymbol);

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["commentator", activeSymbol],
    queryFn: ({ signal }) => api.getCommentatorReport(activeSymbol!, signal),
    enabled: ready && !!activeSymbol,
    staleTime: 120_000,
  });

  if (!activeSymbol) {
    return (
      <div className="flex h-full items-center justify-center bg-bg-panel text-text-faint">
        Select a symbol to see commentator consensus.
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-bg-panel">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <Users className="h-4 w-4 text-accent" />
        <span className="text-2xs font-semibold uppercase tracking-wider text-text-muted">
          Commentator
        </span>
        <span className="font-mono text-xs text-text">{activeSymbol.replace(/\.IS$/, "")}</span>
        <button
          onClick={() => void refetch()}
          className="no-drag ml-auto text-2xs text-text-muted hover:text-text"
        >
          {isFetching ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-3">
        {isLoading && <div className="text-text-faint">Analyzing sources…</div>}
        {isError && <div className="text-negative">Failed to load commentator report.</div>}
        {data && (
          <div className="space-y-4">
            <div className="rounded-md border border-border bg-bg-elevated p-3">
              <div className="flex items-center gap-2">
                <ConsensusBadge consensus={data.consensus} />
                <span className="text-2xs text-text-muted">
                  Agreement {Math.round(data.agreement_score * 100)}%
                  {data.disagreement ? " · sources disagree" : ""}
                </span>
              </div>
              <p className="mt-2 text-sm text-text-muted">{data.summary}</p>
              <div className="mt-2 flex gap-3 text-2xs text-text-faint">
                <span className="text-positive">{data.bullish_count} bullish</span>
                <span className="text-negative">{data.bearish_count} bearish</span>
                <span>{data.neutral_count} neutral</span>
              </div>
            </div>

            {data.opinions.length === 0 ? (
              <p className="text-sm text-text-faint">No attributed headlines found.</p>
            ) : (
              <ul className="space-y-2">
                {data.opinions.map((op) => (
                  <li
                    key={op.url}
                    className="rounded-md border border-border bg-bg-elevated px-3 py-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <a
                        href={op.url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex min-w-0 items-start gap-1 text-sm text-accent hover:underline"
                      >
                        <span className="truncate">{op.title}</span>
                        <ExternalLink className="mt-0.5 h-3 w-3 shrink-0" />
                      </a>
                      <SentimentBadge sentiment={op.sentiment} />
                    </div>
                    <div className="mt-1 text-2xs text-text-faint">
                      {op.source} · importance {op.importance}/5
                    </div>
                    <p className="mt-1 text-2xs text-text-muted">{op.rationale}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ConsensusBadge({ consensus }: { consensus: string }): JSX.Element {
  const colors =
    consensus === "bullish"
      ? "bg-positive/15 text-positive"
      : consensus === "bearish"
        ? "bg-negative/15 text-negative"
        : consensus === "mixed"
          ? "bg-accent/15 text-accent"
          : "bg-bg-hover text-text-muted";
  return (
    <span className={cn("rounded px-2 py-0.5 text-2xs font-semibold uppercase", colors)}>
      {consensus}
    </span>
  );
}

function SentimentBadge({ sentiment }: { sentiment: string }): JSX.Element {
  const colors =
    sentiment === "bullish"
      ? "text-positive"
      : sentiment === "bearish"
        ? "text-negative"
        : "text-text-muted";
  return <span className={cn("shrink-0 text-2xs font-medium capitalize", colors)}>{sentiment}</span>;
}
