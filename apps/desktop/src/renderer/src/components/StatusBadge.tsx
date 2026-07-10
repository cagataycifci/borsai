import { useEngineStore } from "../store/useEngineStore";
import { cn } from "../lib/cn";

const LABELS: Record<string, string> = {
  starting: "Connecting…",
  ready: "Live",
  error: "Engine offline",
  stopped: "Stopped",
};

/** Compact engine + stream connection indicator for the title bar. */
export function StatusBadge(): JSX.Element {
  const status = useEngineStore((s) => s.status);
  const streamConnected = useEngineStore((s) => s.streamConnected);

  const live = status === "ready";
  const dotColor = live
    ? streamConnected
      ? "bg-up"
      : "bg-warn"
    : status === "error"
      ? "bg-down"
      : "bg-text-faint";

  const label = live
    ? streamConnected
      ? "Live"
      : "Polling"
    : (LABELS[status] ?? status);

  return (
    <div className="no-drag flex items-center gap-2 rounded-md border border-border bg-bg-elevated px-2.5 py-1 text-2xs text-text-muted">
      <span className={cn("h-2 w-2 rounded-full", dotColor, live && "animate-pulse")} />
      <span className="uppercase tracking-wide">{label}</span>
    </div>
  );
}
