/** Shared types + helpers for client-side chart drawings (trend/H-line/Fib). */
export type DrawTool = "none" | "trend" | "hline" | "fib";

/** A point stored in chart-logical coordinates so it survives pan/zoom/resize. */
export interface DrawPoint {
  time: number; // unix seconds (UTCTimestamp)
  price: number;
}

export interface Drawing {
  id: string;
  type: Exclude<DrawTool, "none">;
  a: DrawPoint;
  b: DrawPoint; // equals `a` for horizontal lines
}

/** Fibonacci retracement ratios (0 → 1 across the selected price range). */
export const FIB_LEVELS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1] as const;

let counter = 0;
/** Deterministic-enough unique id for a session (avoids Math.random). */
export function nextDrawingId(): string {
  counter += 1;
  return `d${counter}`;
}
