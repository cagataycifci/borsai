import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, BellRing, Plus, Trash2, Loader2 } from "lucide-react";
import { api } from "../../lib/api";
import { useEngineStore } from "../../store/useEngineStore";
import { useWatchlistStore } from "../../store/useWatchlistStore";
import { useAlertsStore } from "../../store/useAlertsStore";
import { cn } from "../../lib/cn";
import { formatRelativeTime } from "../../lib/format";
import type { AlertType } from "../../lib/contracts";

interface TypeMeta {
  value: AlertType;
  label: string;
  threshold: boolean;
  unit?: string;
}

const TYPES: TypeMeta[] = [
  { value: "price_above", label: "Price above", threshold: true },
  { value: "price_below", label: "Price below", threshold: true },
  { value: "percent_up", label: "Up % today", threshold: true, unit: "%" },
  { value: "percent_down", label: "Down % today", threshold: true, unit: "%" },
  { value: "volume_above", label: "Volume above", threshold: true },
  { value: "rsi_above", label: "RSI above", threshold: true },
  { value: "rsi_below", label: "RSI below", threshold: true },
  { value: "macd_cross_up", label: "MACD cross ↑", threshold: false },
  { value: "macd_cross_down", label: "MACD cross ↓", threshold: false },
  { value: "golden_cross", label: "Golden cross (50/200)", threshold: false },
  { value: "death_cross", label: "Death cross (50/200)", threshold: false },
];

const TYPE_LABEL = Object.fromEntries(TYPES.map((t) => [t.value, t.label])) as Record<
  AlertType,
  string
>;

/** Alerts: create price/technical conditions and watch them fire live. */
export function AlertsPanel(): JSX.Element {
  const ready = useEngineStore((s) => s.status === "ready");
  const activeSymbol = useWatchlistStore((s) => s.activeSymbol);
  const queryClient = useQueryClient();

  const events = useAlertsStore((s) => s.events);
  const setEvents = useAlertsStore((s) => s.setEvents);
  const clearUnseen = useAlertsStore((s) => s.clearUnseen);

  const { data: alerts = [] } = useQuery({
    queryKey: ["alerts"],
    queryFn: ({ signal }) => api.listAlerts(signal),
    enabled: ready,
  });

  // Seed the triggered feed from history; clear the unseen badge on view.
  useEffect(() => {
    if (!ready) return;
    const ctrl = new AbortController();
    api.listAlertEvents(50, ctrl.signal).then(setEvents).catch(() => {});
    clearUnseen();
    return () => ctrl.abort();
  }, [ready, setEvents, clearUnseen]);

  // Form state.
  const [symbol, setSymbol] = useState("");
  const [type, setType] = useState<AlertType>("price_above");
  const [threshold, setThreshold] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const meta = TYPES.find((t) => t.value === type)!;
  const effectiveSymbol = (symbol || activeSymbol || "").trim().toUpperCase();

  async function invalidate(): Promise<void> {
    await queryClient.invalidateQueries({ queryKey: ["alerts"] });
  }

  async function create(): Promise<void> {
    if (!effectiveSymbol) {
      setError("Enter a symbol.");
      return;
    }
    if (meta.threshold && !threshold.trim()) {
      setError("This alert needs a threshold.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.createAlert({
        symbol: effectiveSymbol,
        type,
        threshold: meta.threshold ? Number(threshold) : null,
      });
      setThreshold("");
      setSymbol("");
      await invalidate();
    } catch {
      setError("Failed to create alert.");
    } finally {
      setBusy(false);
    }
  }

  async function toggle(id: number, active: boolean): Promise<void> {
    await api.updateAlert(id, { active });
    await invalidate();
  }

  async function remove(id: number): Promise<void> {
    await api.deleteAlert(id);
    await invalidate();
  }

  return (
    <div className="flex h-full flex-col bg-bg-panel">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <Bell className="h-4 w-4 text-accent" />
        <span className="text-2xs font-semibold uppercase tracking-wider text-text-muted">
          Alerts
        </span>
      </div>

      {/* New alert form */}
      <div className="flex flex-col gap-2 border-b border-border p-3">
        <div className="flex gap-2">
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder={activeSymbol ? activeSymbol.replace(/\.IS$/, "") : "Symbol"}
            className="input w-28 font-mono uppercase"
          />
          <select
            value={type}
            onChange={(e) => setType(e.target.value as AlertType)}
            className="input min-w-0 flex-1"
          >
            {TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex gap-2">
          {meta.threshold && (
            <input
              type="number"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              placeholder={`Threshold${meta.unit ? ` (${meta.unit})` : ""}`}
              className="input min-w-0 flex-1"
            />
          )}
          <button
            onClick={() => void create()}
            disabled={busy || !ready}
            className="no-drag ml-auto flex items-center gap-1.5 rounded-md border border-accent/40 bg-accent/10 px-3 py-1.5 text-sm text-accent hover:bg-accent/20 disabled:opacity-50"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Add alert
          </button>
        </div>
        {error && <p className="text-2xs text-down">{error}</p>}
      </div>

      {/* Alert list + triggered feed */}
      <div className="min-h-0 flex-1 overflow-auto">
        <div className="px-3 py-2 text-2xs font-semibold uppercase tracking-wider text-text-faint">
          Active & saved
        </div>
        {alerts.length === 0 && (
          <div className="px-3 pb-3 text-2xs text-text-faint">No alerts yet.</div>
        )}
        {alerts.map((a) => (
          <div
            key={a.id}
            className="flex items-center gap-2 border-b border-border/50 px-3 py-2 text-sm"
          >
            <span className="w-16 shrink-0 font-mono text-text">
              {a.symbol.replace(/\.IS$/, "")}
            </span>
            <span className="min-w-0 flex-1 truncate text-text-muted">
              {TYPE_LABEL[a.type]}
              {a.threshold != null ? ` ${a.threshold}` : ""}
            </span>
            <button
              onClick={() => void toggle(a.id, !a.active)}
              title={a.active ? "Active — click to pause" : "Paused — click to activate"}
              className={cn(
                "rounded px-2 py-0.5 text-2xs font-medium",
                a.active
                  ? "bg-up/15 text-up"
                  : "bg-bg-elevated text-text-faint hover:text-text",
              )}
            >
              {a.active ? "On" : "Off"}
            </button>
            <button
              onClick={() => void remove(a.id)}
              title="Delete"
              className="no-drag text-text-faint hover:text-down"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}

        <div className="mt-2 flex items-center gap-1.5 px-3 py-2 text-2xs font-semibold uppercase tracking-wider text-text-faint">
          <BellRing className="h-3.5 w-3.5" />
          Recently triggered
        </div>
        {events.length === 0 && (
          <div className="px-3 pb-3 text-2xs text-text-faint">
            Nothing triggered yet.
          </div>
        )}
        {events.map((e, i) => (
          <div
            key={e.id ?? i}
            className="border-b border-border/40 px-3 py-2 text-sm"
          >
            <div className="flex items-center gap-2">
              <span className="font-mono text-text">{e.symbol.replace(/\.IS$/, "")}</span>
              <span className="ml-auto text-2xs text-text-faint">
                {formatRelativeTime(e.created_at)}
              </span>
            </div>
            <div className="text-2xs text-text-muted">{e.message}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
