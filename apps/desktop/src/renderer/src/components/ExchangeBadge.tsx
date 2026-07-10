import type { Exchange } from "../lib/contracts";
import { cn } from "../lib/cn";

const STYLES: Record<Exchange, string> = {
  BIST: "bg-warn/15 text-warn",
  NASDAQ: "bg-accent/15 text-accent",
  NYSE: "bg-accent/15 text-accent",
  AMEX: "bg-accent/15 text-accent",
  OTHER: "bg-border-strong text-text-muted",
};

export function ExchangeBadge({ exchange }: { exchange: Exchange }): JSX.Element {
  return (
    <span
      className={cn(
        "rounded px-1.5 py-0.5 text-2xs font-medium tracking-wide",
        STYLES[exchange] ?? STYLES.OTHER,
      )}
    >
      {exchange}
    </span>
  );
}
