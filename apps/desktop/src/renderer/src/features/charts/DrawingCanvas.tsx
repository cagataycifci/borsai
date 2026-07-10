import { useEffect, useRef, useState } from "react";
import type {
  IChartApi,
  ISeriesApi,
  Time,
  UTCTimestamp,
} from "lightweight-charts";
import {
  type Drawing,
  type DrawPoint,
  type DrawTool,
  FIB_LEVELS,
  nextDrawingId,
} from "./drawings";

interface Props {
  chartRef: React.MutableRefObject<IChartApi | null>;
  seriesRef: React.MutableRefObject<ISeriesApi<
    "Candlestick" | "Line" | "Area"
  > | null>;
  tool: DrawTool;
  drawings: Drawing[];
  onCommit: (drawing: Drawing) => void;
  /** Reset the active tool to "none" (after a shape is finished / cancelled). */
  onToolReset: () => void;
  /** Bumped by the parent when the price series is rebuilt, to force a redraw. */
  redrawToken: string;
}

const LINE = "#e6b450";
const FIB = "#2f81f7";

/**
 * Client-side drawing layer over the price chart: trend lines, horizontal
 * support/resistance, and Fibonacci retracements. Points are stored in chart
 * coordinates (time, price) and re-projected to pixels on every pan/zoom/resize,
 * so drawings stay glued to the data. The layer only captures pointer events
 * while a tool is active, so normal chart interaction is unaffected otherwise.
 */
export function DrawingCanvas({
  chartRef,
  seriesRef,
  tool,
  drawings,
  onCommit,
  onToolReset,
  redrawToken,
}: Props): JSX.Element {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [draft, setDraft] = useState<DrawPoint | null>(null);
  const [cursor, setCursor] = useState<{ x: number; y: number } | null>(null);
  const [, force] = useState(0);

  // Re-project on pan/zoom/resize.
  useEffect(() => {
    const chart = chartRef.current;
    const el = wrapRef.current;
    if (!chart || !el) return;
    const redraw = (): void => force((n) => n + 1);
    const ts = chart.timeScale();
    ts.subscribeVisibleLogicalRangeChange(redraw);
    const ro = new ResizeObserver(redraw);
    ro.observe(el);
    return () => {
      ts.unsubscribeVisibleLogicalRangeChange(redraw);
      ro.disconnect();
    };
  }, [chartRef, redrawToken]);

  // Escape cancels an in-progress draft and exits the tool.
  useEffect(() => {
    function onKey(e: KeyboardEvent): void {
      if (e.key === "Escape") {
        setDraft(null);
        onToolReset();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onToolReset]);

  const active = tool !== "none";

  function toPoint(e: React.MouseEvent): DrawPoint | null {
    const chart = chartRef.current;
    const series = seriesRef.current;
    const el = wrapRef.current;
    if (!chart || !series || !el) return null;
    const rect = el.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const time = chart.timeScale().coordinateToTime(x);
    const price = series.coordinateToPrice(y);
    if (time == null || price == null) return null;
    return { time: time as number, price };
  }

  function toXY(p: DrawPoint): { x: number; y: number } | null {
    const chart = chartRef.current;
    const series = seriesRef.current;
    if (!chart || !series) return null;
    const x = chart.timeScale().timeToCoordinate(p.time as UTCTimestamp as Time);
    const y = series.priceToCoordinate(p.price);
    if (x == null || y == null) return null;
    return { x, y };
  }

  function handleClick(e: React.MouseEvent): void {
    if (!active) return;
    const p = toPoint(e);
    if (!p) return;
    if (tool === "hline") {
      onCommit({ id: nextDrawingId(), type: "hline", a: p, b: p });
      onToolReset();
      return;
    }
    if (!draft) {
      setDraft(p);
    } else {
      onCommit({ id: nextDrawingId(), type: tool, a: draft, b: p });
      setDraft(null);
      onToolReset();
    }
  }

  function handleMove(e: React.MouseEvent): void {
    if (!active) return;
    const rect = wrapRef.current?.getBoundingClientRect();
    if (!rect) return;
    setCursor({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  }

  const width = wrapRef.current?.clientWidth ?? 0;

  // Build the renderable element for one committed/draft drawing.
  function render(d: { type: Drawing["type"]; a: DrawPoint; b: DrawPoint }, key: string) {
    const a = toXY(d.a);
    if (!a) return null;

    if (d.type === "hline") {
      return (
        <g key={key}>
          <line x1={0} y1={a.y} x2={width} y2={a.y} stroke={LINE} strokeWidth={1} />
          <text x={6} y={a.y - 3} fill={LINE} fontSize={10}>
            {d.a.price.toFixed(2)}
          </text>
        </g>
      );
    }

    const b = toXY(d.b);
    if (!b) return null;

    if (d.type === "trend") {
      return (
        <line key={key} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={LINE} strokeWidth={1.5} />
      );
    }

    // Fibonacci retracement: levels across the selected price range.
    const top = Math.max(d.a.price, d.b.price);
    const bottom = Math.min(d.a.price, d.b.price);
    const x1 = Math.min(a.x, b.x);
    const x2 = Math.max(a.x, b.x);
    return (
      <g key={key}>
        {FIB_LEVELS.map((r) => {
          const price = top - (top - bottom) * r;
          const xy = toXY({ time: d.a.time, price });
          if (!xy) return null;
          return (
            <g key={r}>
              <line
                x1={x1}
                y1={xy.y}
                x2={x2}
                y2={xy.y}
                stroke={FIB}
                strokeWidth={1}
                strokeOpacity={0.7}
                strokeDasharray="3 2"
              />
              <text x={x2 + 4} y={xy.y + 3} fill={FIB} fontSize={9}>
                {(r * 100).toFixed(1)}% · {price.toFixed(2)}
              </text>
            </g>
          );
        })}
      </g>
    );
  }

  // Live preview from the first placed point to the cursor.
  let preview: { type: Drawing["type"]; a: DrawPoint; b: DrawPoint } | null = null;
  if (draft && cursor && (tool === "trend" || tool === "fib")) {
    const chart = chartRef.current;
    const series = seriesRef.current;
    if (chart && series) {
      const time = chart.timeScale().coordinateToTime(cursor.x);
      const price = series.coordinateToPrice(cursor.y);
      if (time != null && price != null) {
        preview = { type: tool, a: draft, b: { time: time as number, price } };
      }
    }
  }

  return (
    <div
      ref={wrapRef}
      onClick={handleClick}
      onMouseMove={handleMove}
      onMouseLeave={() => setCursor(null)}
      className="absolute inset-0 z-20"
      style={{
        pointerEvents: active ? "auto" : "none",
        cursor: active ? "crosshair" : "default",
      }}
    >
      <svg className="h-full w-full" style={{ pointerEvents: "none" }}>
        {drawings.map((d) => render(d, d.id))}
        {preview && render(preview, "preview")}
      </svg>
    </div>
  );
}
