import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Calendar, RefreshCw, Sun, TrendingUp } from "lucide-react";
import { api } from "../../lib/api";
import { useEngineStore } from "../../store/useEngineStore";
import { cn } from "../../lib/cn";
import { formatRelativeTime } from "../../lib/format";
import type { ReportRegion } from "../../lib/contracts";

type Tab = "morning" | "watch" | "calendar";

const REGIONS: { id: ReportRegion; label: string }[] = [
  { id: "us", label: "US" },
  { id: "tr", label: "BIST" },
  { id: "global", label: "Global" },
];

/**
 * Scheduled reports: morning market summaries, stocks-to-watch digest,
 * and the economic calendar (Phase 8).
 */
export function ReportsPanel(): JSX.Element {
  const ready = useEngineStore((s) => s.status === "ready");
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("morning");
  const [region, setRegion] = useState<ReportRegion>("us");

  const morningQuery = useQuery({
    queryKey: ["reports", "morning", region],
    queryFn: ({ signal }) => api.getMorningSummary(region, signal),
    enabled: ready && tab === "morning",
    staleTime: 300_000,
  });

  const watchQuery = useQuery({
    queryKey: ["reports", "watch"],
    queryFn: ({ signal }) => api.getStocksToWatch(signal),
    enabled: ready && tab === "watch",
    staleTime: 300_000,
  });

  const calendarQuery = useQuery({
    queryKey: ["calendar"],
    queryFn: ({ signal }) => api.getEconomicCalendar(14, signal),
    enabled: ready && tab === "calendar",
    staleTime: 600_000,
  });

  const isFetching =
    (tab === "morning" && morningQuery.isFetching) ||
    (tab === "watch" && watchQuery.isFetching) ||
    (tab === "calendar" && calendarQuery.isFetching);

  async function refresh(): Promise<void> {
    if (tab === "morning") {
      await api.generateMorningSummary(region);
      void queryClient.invalidateQueries({ queryKey: ["reports", "morning", region] });
    } else if (tab === "watch") {
      await api.generateStocksToWatch();
      void queryClient.invalidateQueries({ queryKey: ["reports", "watch"] });
    } else {
      void queryClient.invalidateQueries({ queryKey: ["calendar"] });
    }
  }

  return (
    <div className="flex h-full flex-col bg-bg-panel">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <span className="text-2xs font-semibold uppercase tracking-wider text-text-muted">
          Reports
        </span>
        <div className="flex items-center gap-0.5 rounded-md border border-border bg-bg-elevated p-0.5">
          {(
            [
              { id: "morning" as Tab, label: "Morning", icon: Sun },
              { id: "watch" as Tab, label: "Watch", icon: TrendingUp },
              { id: "calendar" as Tab, label: "Calendar", icon: Calendar },
            ] as const
          ).map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={cn(
                "flex items-center gap-1 rounded px-2 py-0.5 text-2xs font-medium transition-colors",
                tab === id ? "bg-accent/20 text-accent" : "text-text-muted hover:text-text",
              )}
            >
              <Icon className="h-3 w-3" />
              {label}
            </button>
          ))}
        </div>
        {tab === "morning" && (
          <div className="flex items-center gap-0.5 rounded-md border border-border bg-bg-elevated p-0.5">
            {REGIONS.map((r) => (
              <button
                key={r.id}
                onClick={() => setRegion(r.id)}
                className={cn(
                  "rounded px-2 py-0.5 text-2xs font-medium transition-colors",
                  region === r.id ? "bg-accent/20 text-accent" : "text-text-muted hover:text-text",
                )}
              >
                {r.label}
              </button>
            ))}
          </div>
        )}
        <button
          onClick={() => void refresh()}
          title="Refresh"
          className="no-drag ml-auto flex items-center gap-1 rounded-md border border-border bg-bg-elevated px-2 py-1 text-2xs text-text-muted hover:text-text"
        >
          <RefreshCw className={cn("h-3 w-3", isFetching && "animate-spin")} />
          Refresh
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-3">
        {tab === "morning" && (
          <MorningView
            loading={morningQuery.isLoading}
            error={morningQuery.isError}
            data={morningQuery.data}
          />
        )}
        {tab === "watch" && (
          <WatchView
            loading={watchQuery.isLoading}
            error={watchQuery.isError}
            data={watchQuery.data}
          />
        )}
        {tab === "calendar" && (
          <CalendarView
            loading={calendarQuery.isLoading}
            error={calendarQuery.isError}
            data={calendarQuery.data}
          />
        )}
      </div>
    </div>
  );
}

function MorningView({
  loading,
  error,
  data,
}: {
  loading: boolean;
  error: boolean;
  data: Awaited<ReturnType<typeof api.getMorningSummary>> | undefined;
}): JSX.Element {
  if (loading) return <Loading />;
  if (error || !data) return <ErrorMsg />;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-text">{data.title}</h2>
        <p className="mt-1 text-2xs text-text-faint">
          {data.ai_enhanced ? "AI-enhanced" : "Template"} ·{" "}
          {data.generated_at ? formatRelativeTime(data.generated_at) : "just now"}
        </p>
      </div>
      <p className="text-sm leading-relaxed text-text-muted">{data.overview}</p>
      {data.highlights.length > 0 && (
        <ul className="list-inside list-disc space-y-1 text-sm text-text">
          {data.highlights.map((h) => (
            <li key={h}>{h}</li>
          ))}
        </ul>
      )}
      {data.benchmarks.length > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {data.benchmarks.map((b) => (
            <div
              key={b.symbol}
              className="rounded-md border border-border bg-bg-elevated px-3 py-2"
            >
              <div className="font-mono text-xs font-semibold text-text">{b.display_symbol}</div>
              <div className="text-2xs text-text-muted">{b.name}</div>
              <div
                className={cn(
                  "mt-1 font-mono text-sm",
                  (b.change_percent ?? 0) >= 0 ? "text-positive" : "text-negative",
                )}
              >
                {b.price?.toFixed(2)} ({b.change_percent != null ? `${b.change_percent >= 0 ? "+" : ""}${b.change_percent.toFixed(2)}%` : "—"})
              </div>
            </div>
          ))}
        </div>
      )}
      {data.headlines.length > 0 && (
        <div>
          <h3 className="mb-2 text-2xs font-semibold uppercase tracking-wider text-text-muted">
            Headlines
          </h3>
          <ul className="space-y-2">
            {data.headlines.map((h) => (
              <li key={h.url} className="text-sm">
                <a
                  href={h.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent hover:underline"
                >
                  {h.title}
                </a>
                <span className="ml-2 text-2xs text-text-faint">{h.source}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function WatchView({
  loading,
  error,
  data,
}: {
  loading: boolean;
  error: boolean;
  data: Awaited<ReturnType<typeof api.getStocksToWatch>> | undefined;
}): JSX.Element {
  if (loading) return <Loading />;
  if (error || !data) return <ErrorMsg />;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-text">{data.title}</h2>
        <p className="mt-1 text-sm text-text-muted">{data.overview}</p>
      </div>
      {data.picks.length === 0 ? (
        <p className="text-sm text-text-faint">Add symbols to your watchlists to populate this digest.</p>
      ) : (
        <div className="space-y-2">
          {data.picks.map((p) => (
            <div
              key={p.symbol}
              className="flex items-center justify-between rounded-md border border-border bg-bg-elevated px-3 py-2"
            >
              <div>
                <div className="font-mono text-xs font-semibold text-text">{p.display_symbol}</div>
                <div className="text-2xs text-text-muted">{p.reason}</div>
              </div>
              <div
                className={cn(
                  "font-mono text-sm",
                  (p.change_percent ?? 0) >= 0 ? "text-positive" : "text-negative",
                )}
              >
                {p.price?.toFixed(2)}
                {p.change_percent != null && (
                  <span className="ml-1 text-2xs">
                    {p.change_percent >= 0 ? "+" : ""}
                    {p.change_percent.toFixed(2)}%
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CalendarView({
  loading,
  error,
  data,
}: {
  loading: boolean;
  error: boolean;
  data: Awaited<ReturnType<typeof api.getEconomicCalendar>> | undefined;
}): JSX.Element {
  if (loading) return <Loading />;
  if (error || !data) return <ErrorMsg />;

  return (
    <div className="space-y-2">
      {data.events.length === 0 ? (
        <p className="text-sm text-text-faint">No upcoming events in this window.</p>
      ) : (
        data.events.map((ev, i) => (
          <div
            key={`${ev.title}-${ev.event_at}-${i}`}
            className="flex items-start gap-3 rounded-md border border-border bg-bg-elevated px-3 py-2"
          >
            <div className="min-w-[4.5rem] font-mono text-2xs text-text-faint">
              {new Date(ev.event_at).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
              })}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm text-text">{ev.title}</div>
              <div className="text-2xs text-text-muted">
                {ev.country}
                {ev.category ? ` · ${ev.category}` : ""}
              </div>
            </div>
            <ImpactBadge impact={ev.impact} />
          </div>
        ))
      )}
    </div>
  );
}

function ImpactBadge({ impact }: { impact: string }): JSX.Element {
  const colors =
    impact === "high"
      ? "bg-negative/15 text-negative"
      : impact === "medium"
        ? "bg-accent/15 text-accent"
        : "bg-bg-hover text-text-faint";
  return (
    <span className={cn("rounded px-1.5 py-0.5 text-2xs font-medium uppercase", colors)}>
      {impact}
    </span>
  );
}

function Loading(): JSX.Element {
  return (
    <div className="flex h-32 items-center justify-center text-text-faint">Loading…</div>
  );
}

function ErrorMsg(): JSX.Element {
  return (
    <div className="flex h-32 items-center justify-center text-negative">
      Failed to load report. Is the engine running?
    </div>
  );
}
