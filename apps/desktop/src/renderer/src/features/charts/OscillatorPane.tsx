import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import {
  ColorType,
  CrosshairMode,
  createChart,
  type IChartApi,
  type ISeriesApi,
} from "lightweight-charts";
import type { IndicatorSeries } from "../../lib/contracts";
import { toOscillatorHistogram, toOverlayLineData } from "./chartData";
import type { ChartSync } from "./chartSync";

/** Per-series colour for oscillator lines, keyed by the engine series key. */
const COLORS: Record<string, string> = {
  rsi_14: "#2f81f7",
  macd: "#2f81f7",
  macd_signal: "#f0b90b",
  stoch_k: "#2f81f7",
  stoch_d: "#f0b90b",
  atr_14: "#a855f7",
};

/** Horizontal guide levels per pane (overbought/oversold bands). */
const GUIDES: Record<string, number[]> = {
  rsi: [70, 30],
  stoch: [80, 20],
};

const GRID = "#161d28";
const AXIS = "#1e2733";

interface Props {
  /** Engine pane id: "rsi" | "macd" | "stoch" | "atr". */
  paneKey: string;
  title: string;
  series: IndicatorSeries[];
  sync: ChartSync;
  /** Show the time axis (only the bottom-most pane does). */
  showTimeAxis: boolean;
  onClose: () => void;
}

/**
 * A single oscillator sub-pane. Owns its own lightweight-charts instance (v4 has
 * no native multi-pane) and registers with {@link ChartSync} so it pans/zooms in
 * lock-step with the price chart above it.
 */
export function OscillatorPane({
  paneKey,
  title,
  series,
  sync,
  showTimeAxis,
  onClose,
}: Props): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<Map<string, ISeriesApi<"Line" | "Histogram">>>(new Map());

  // Create the chart once; register/unregister with the sync coordinator.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const chart = createChart(el, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#0f141c" },
        textColor: "#8a97a8",
        fontFamily: "Inter, Segoe UI, system-ui, sans-serif",
        fontSize: 10,
      },
      grid: { vertLines: { color: GRID }, horzLines: { color: GRID } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: AXIS, minimumWidth: 56 },
      timeScale: { borderColor: AXIS, visible: false },
      handleScale: { axisPressedMouseMove: { time: true, price: false } },
    });
    chartRef.current = chart;
    sync.add(chart);

    return () => {
      sync.remove(chart);
      chart.remove();
      chartRef.current = null;
      seriesRef.current.clear();
    };
  }, [sync]);

  // Keep the bottom pane's time axis visibility in sync with the stack.
  useEffect(() => {
    chartRef.current?.applyOptions({ timeScale: { visible: showTimeAxis } });
  }, [showTimeAxis]);

  // Reconcile series whenever the indicator data changes.
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    const existing = seriesRef.current;
    const wanted = new Set(series.map((s) => s.key));

    for (const [key, s] of existing) {
      if (!wanted.has(key)) {
        chart.removeSeries(s);
        existing.delete(key);
      }
    }

    for (const s of series) {
      let line = existing.get(s.key);
      if (!line) {
        if (s.style === "histogram") {
          line = chart.addHistogramSeries({
            priceLineVisible: false,
            lastValueVisible: false,
          });
        } else {
          const created = chart.addLineSeries({
            color: COLORS[s.key] ?? "#8a97a8",
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: true,
          });
          // Overbought/oversold guides on the pane's primary line.
          for (const level of GUIDES[paneKey] ?? []) {
            created.createPriceLine({
              price: level,
              color: "#3a4654",
              lineWidth: 1,
              lineStyle: 2, // dashed
              axisLabelVisible: true,
              title: "",
            });
          }
          line = created;
        }
        existing.set(s.key, line);
      }
      if (s.style === "histogram") {
        (line as ISeriesApi<"Histogram">).setData(toOscillatorHistogram(s.points));
      } else {
        (line as ISeriesApi<"Line">).setData(toOverlayLineData(s.points));
      }
    }

    sync.alignFromOthers(chart);
  }, [series, paneKey, sync]);

  return (
    <div className="relative h-[140px] shrink-0 border-t border-border">
      <div className="pointer-events-none absolute left-2 top-1 z-10 text-2xs font-medium text-text-muted">
        {title}
      </div>
      <button
        onClick={onClose}
        title={`Hide ${title}`}
        className="no-drag absolute right-1 top-1 z-10 rounded p-0.5 text-text-faint hover:bg-bg-hover hover:text-text"
      >
        <X className="h-3 w-3" />
      </button>
      <div ref={containerRef} className="absolute inset-0" />
    </div>
  );
}
