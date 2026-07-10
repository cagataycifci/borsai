import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ChevronDown,
  LineChart,
  MousePointer2,
  TrendingUp,
  Minus,
  GitCommitHorizontal,
  Trash2,
} from "lucide-react";
import {
  ColorType,
  CrosshairMode,
  createChart,
  type IChartApi,
  type ISeriesApi,
} from "lightweight-charts";
import { api } from "../../lib/api";
import { useWatchlistStore } from "../../store/useWatchlistStore";
import { useQuotesStore } from "../../store/useQuotesStore";
import { cn } from "../../lib/cn";
import { ExchangeBadge } from "../../components/ExchangeBadge";
import {
  type ChartType,
  toCandlestickData,
  toHeikinAshiData,
  toLineData,
  toOverlayLineData,
  toVolumeData,
} from "./chartData";
import { OscillatorPane } from "./OscillatorPane";
import { VolumeProfileOverlay } from "./VolumeProfileOverlay";
import { DrawingCanvas } from "./DrawingCanvas";
import { type Drawing, type DrawTool } from "./drawings";
import { ChartSync } from "./chartSync";

/** Timeframe → engine (interval, range) pairs, chosen to respect yfinance limits. */
const TIMEFRAMES = [
  { label: "1m", interval: "1m", range: "1d" },
  { label: "5m", interval: "5m", range: "5d" },
  { label: "15m", interval: "15m", range: "1mo" },
  { label: "1h", interval: "1h", range: "3mo" },
  { label: "4h", interval: "4h", range: "6mo" },
  { label: "1D", interval: "1d", range: "1y" },
  { label: "1W", interval: "1wk", range: "5y" },
  { label: "1M", interval: "1mo", range: "max" },
] as const;

type TimeframeLabel = (typeof TIMEFRAMES)[number]["label"];

const CHART_TYPES: { value: ChartType; label: string }[] = [
  { value: "candles", label: "Candles" },
  { value: "heikin", label: "Heikin-Ashi" },
  { value: "line", label: "Line" },
  { value: "area", label: "Area" },
];

const UP = "#16c784";
const DOWN = "#ea3943";
const ACCENT = "#2f81f7";

/** Price-pane overlay indicators with their engine spec token. */
const OVERLAYS = [
  { id: "sma20", token: "sma:20", label: "SMA 20" },
  { id: "sma50", token: "sma:50", label: "SMA 50" },
  { id: "ema20", token: "ema:20", label: "EMA 20" },
  { id: "ema50", token: "ema:50", label: "EMA 50" },
  { id: "bbands", token: "bbands:20:2", label: "Bollinger (20,2)" },
  { id: "vwap", token: "vwap", label: "VWAP" },
] as const;

/** Per-series colour, keyed by the engine's series key. */
const OVERLAY_COLORS: Record<string, string> = {
  sma_20: "#f0b90b",
  sma_50: "#f97316",
  ema_20: "#2f81f7",
  ema_50: "#a855f7",
  bb_upper: "#8a97a8",
  bb_middle: "#5a6675",
  bb_lower: "#8a97a8",
  vwap: "#16c784",
};

/**
 * Oscillator indicators rendered in their own synced sub-pane below the price
 * chart. `pane` matches the engine's `IndicatorSeries.pane` hint.
 */
const OSCILLATORS = [
  { id: "rsi", token: "rsi:14", label: "RSI (14)", pane: "rsi", title: "RSI 14" },
  { id: "macd", token: "macd", label: "MACD", pane: "macd", title: "MACD (12,26,9)" },
  { id: "stoch", token: "stoch", label: "Stochastic", pane: "stoch", title: "Stoch (14,3)" },
  { id: "atr", token: "atr:14", label: "ATR (14)", pane: "atr", title: "ATR 14" },
] as const;

/** Drawing-tool buttons (cursor disables drawing). */
const DRAW_TOOLS: { id: DrawTool; icon: typeof Minus; title: string }[] = [
  { id: "none", icon: MousePointer2, title: "Cursor (no drawing)" },
  { id: "trend", icon: TrendingUp, title: "Trend line (click start, click end)" },
  { id: "hline", icon: Minus, title: "Horizontal line (click a level)" },
  { id: "fib", icon: GitCommitHorizontal, title: "Fibonacci retracement (click high, click low)" },
];

/** TradingView-style price chart for the active symbol. */
export function ChartPanel(): JSX.Element {
  const activeSymbol = useWatchlistStore((s) => s.activeSymbol);
  const quote = useQuotesStore((s) =>
    activeSymbol ? s.quotes[activeSymbol] : undefined,
  );
  const [tf, setTf] = useState<TimeframeLabel>("1D");
  const [chartType, setChartType] = useState<ChartType>("candles");
  const [overlays, setOverlays] = useState<Set<string>>(new Set());
  const [oscillators, setOscillators] = useState<string[]>([]);
  const [volumeProfile, setVolumeProfile] = useState(false);
  const [overlayMenuOpen, setOverlayMenuOpen] = useState(false);
  const [tool, setTool] = useState<DrawTool>("none");
  const [drawingsBySymbol, setDrawingsBySymbol] = useState<Record<string, Drawing[]>>(
    {},
  );
  const drawings = activeSymbol ? (drawingsBySymbol[activeSymbol] ?? []) : [];

  const frame = TIMEFRAMES.find((t) => t.label === tf) ?? TIMEFRAMES[5];
  // Engine spec combines price overlays + active oscillators in one request.
  const indicatorSpec = [
    ...OVERLAYS.filter((o) => overlays.has(o.id)).map((o) => o.token),
    ...OSCILLATORS.filter((o) => oscillators.includes(o.id)).map((o) => o.token),
  ].join(",");
  const indicatorCount = overlays.size + oscillators.length + (volumeProfile ? 1 : 0);

  const containerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [chart, setChart] = useState<IChartApi | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const priceSeriesRef = useRef<ISeriesApi<"Candlestick" | "Line" | "Area"> | null>(
    null,
  );
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const overlaySeriesRef = useRef<Map<string, ISeriesApi<"Line">>>(new Map());

  // One sync coordinator keeps the price chart + oscillator panes in lock-step.
  const syncRef = useRef<ChartSync>();
  if (!syncRef.current) syncRef.current = new ChartSync();

  const {
    data: candles = [],
    isFetching,
    isError,
  } = useQuery({
    queryKey: ["history", activeSymbol, frame.interval, frame.range],
    queryFn: ({ signal }) =>
      api.getHistory(activeSymbol!, frame.interval, frame.range, signal),
    enabled: !!activeSymbol,
    staleTime: 30_000,
  });

  const { data: indicators } = useQuery({
    queryKey: ["indicators", activeSymbol, indicatorSpec, frame.interval, frame.range],
    queryFn: ({ signal }) =>
      api.getIndicators(activeSymbol!, indicatorSpec, frame.interval, frame.range, signal),
    enabled: !!activeSymbol && indicatorSpec.length > 0,
    staleTime: 30_000,
  });

  const { data: volProfile } = useQuery({
    queryKey: ["volprofile", activeSymbol, frame.interval, frame.range],
    queryFn: ({ signal }) =>
      api.getVolumeProfile(activeSymbol!, 24, frame.interval, frame.range, signal),
    enabled: !!activeSymbol && volumeProfile,
    staleTime: 30_000,
  });

  // Chart container is only in the DOM once a symbol is selected (early return
  // below). Depend on `hasSymbol` so we create the chart on that first render —
  // a bare `[]` effect runs while containerRef is still null and never retries.
  const hasSymbol = !!activeSymbol;
  useEffect(() => {
    if (!hasSymbol) return;
    const el = containerRef.current;
    if (!el) return;

    const newChart = createChart(el, {
      // Explicit size + ResizeObserver: Dockview often mounts panels at 0×0;
      // autoSize alone can miss the first non-zero layout pass.
      width: el.clientWidth || undefined,
      height: el.clientHeight || undefined,
      layout: {
        background: { type: ColorType.Solid, color: "#0f141c" },
        textColor: "#8a97a8",
        fontFamily: "Inter, Segoe UI, system-ui, sans-serif",
      },
      grid: {
        vertLines: { color: "#161d28" },
        horzLines: { color: "#161d28" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#1e2733", minimumWidth: 56 },
      timeScale: {
        borderColor: "#1e2733",
        timeVisible: true,
        secondsVisible: false,
      },
    });
    setChart(newChart);
    chartRef.current = newChart;
    const sync = syncRef.current!;
    sync.add(newChart);

    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) {
        newChart.applyOptions({ width, height });
      }
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      sync.remove(newChart);
      newChart.remove();
      setChart(null);
      chartRef.current = null;
      priceSeriesRef.current = null;
      volumeSeriesRef.current = null;
      overlaySeriesRef.current.clear();
    };
  }, [hasSymbol]);

  // (Re)build series whenever the data, chart type, or chart instance changes.
  useEffect(() => {
    if (!chart) return;

    if (priceSeriesRef.current) {
      chart.removeSeries(priceSeriesRef.current);
      priceSeriesRef.current = null;
    }
    if (volumeSeriesRef.current) {
      chart.removeSeries(volumeSeriesRef.current);
      volumeSeriesRef.current = null;
    }

    if (chartType === "line" || chartType === "area") {
      const series =
        chartType === "line"
          ? chart.addLineSeries({ color: ACCENT, lineWidth: 2 })
          : chart.addAreaSeries({
              lineColor: ACCENT,
              topColor: "rgba(47,129,247,0.35)",
              bottomColor: "rgba(47,129,247,0.02)",
              lineWidth: 2,
            });
      series.setData(toLineData(candles));
      priceSeriesRef.current = series;
    } else {
      const series = chart.addCandlestickSeries({
        upColor: UP,
        downColor: DOWN,
        borderUpColor: UP,
        borderDownColor: DOWN,
        wickUpColor: UP,
        wickDownColor: DOWN,
      });
      series.setData(
        chartType === "heikin"
          ? toHeikinAshiData(candles)
          : toCandlestickData(candles),
      );
      priceSeriesRef.current = series;
    }

    // Volume histogram pinned to the bottom on its own overlay scale.
    const volume = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "vol",
      priceLineVisible: false,
      lastValueVisible: false,
    });
    volume.priceScale().applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
    });
    volume.setData(toVolumeData(candles));
    volumeSeriesRef.current = volume;

    if (candles.length) chart.timeScale().fitContent();
  }, [chart, candles, chartType]);

  // Sync price-pane overlay indicator lines with the current selection/data.
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    const existing = overlaySeriesRef.current;
    const priceSeries = (indicators?.series ?? []).filter((s) => s.pane === "price");
    const wanted = new Set(priceSeries.map((s) => s.key));

    // Drop overlays no longer selected.
    for (const [key, series] of existing) {
      if (!wanted.has(key)) {
        chart.removeSeries(series);
        existing.delete(key);
      }
    }

    // Add / update selected overlays.
    for (const s of priceSeries) {
      let series = existing.get(s.key);
      if (!series) {
        series = chart.addLineSeries({
          color: OVERLAY_COLORS[s.key] ?? "#8a97a8",
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        existing.set(s.key, series);
      }
      series.setData(toOverlayLineData(s.points));
    }
  }, [indicators]);

  // Close the indicators menu on outside click.
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!menuRef.current?.contains(e.target as Node)) setOverlayMenuOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  // The price chart shows the time axis only when no oscillator sits below it
  // (otherwise the bottom-most oscillator pane owns the shared axis).
  useEffect(() => {
    chartRef.current?.applyOptions({
      timeScale: { visible: oscillators.length === 0 },
    });
  }, [oscillators.length]);

  function toggleOverlay(id: string) {
    setOverlays((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleOscillator(id: string) {
    setOscillators((prev) =>
      prev.includes(id) ? prev.filter((o) => o !== id) : [...prev, id],
    );
  }

  function commitDrawing(d: Drawing) {
    if (!activeSymbol) return;
    setDrawingsBySymbol((prev) => ({
      ...prev,
      [activeSymbol]: [...(prev[activeSymbol] ?? []), d],
    }));
  }

  function clearDrawings() {
    if (!activeSymbol) return;
    setDrawingsBySymbol((prev) => ({ ...prev, [activeSymbol]: [] }));
  }

  if (!activeSymbol) {
    return (
      <div className="flex h-full items-center justify-center bg-bg-panel text-text-faint">
        Select a symbol
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-bg-panel">
      <div className="no-drag flex flex-wrap items-center gap-3 border-b border-border px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-semibold text-text">
            {quote?.display_symbol ?? activeSymbol}
          </span>
          {quote && <ExchangeBadge exchange={quote.exchange} />}
        </div>

        <div className="flex items-center gap-0.5 rounded-md border border-border bg-bg-elevated p-0.5">
          {TIMEFRAMES.map((t) => (
            <button
              key={t.label}
              onClick={() => setTf(t.label)}
              className={cn(
                "rounded px-2 py-0.5 text-2xs font-medium tabular transition-colors",
                t.label === tf
                  ? "bg-accent/20 text-accent"
                  : "text-text-muted hover:text-text",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-0.5 rounded-md border border-border bg-bg-elevated p-0.5">
          {CHART_TYPES.map((c) => (
            <button
              key={c.value}
              onClick={() => setChartType(c.value)}
              className={cn(
                "rounded px-2 py-0.5 text-2xs font-medium transition-colors",
                c.value === chartType
                  ? "bg-accent/20 text-accent"
                  : "text-text-muted hover:text-text",
              )}
            >
              {c.label}
            </button>
          ))}
        </div>

        <div ref={menuRef} className="relative">
          <button
            onClick={() => setOverlayMenuOpen((o) => !o)}
            className={cn(
              "flex items-center gap-1 rounded-md border border-border bg-bg-elevated px-2 py-1 text-2xs font-medium transition-colors",
              indicatorCount > 0 ? "text-accent" : "text-text-muted hover:text-text",
            )}
          >
            <LineChart className="h-3.5 w-3.5" />
            Indicators
            {indicatorCount > 0 && (
              <span className="tabular text-accent">({indicatorCount})</span>
            )}
            <ChevronDown className="h-3 w-3" />
          </button>
          {overlayMenuOpen && (
            <div className="absolute z-50 mt-1 w-48 rounded-md border border-border bg-bg-panel py-1 shadow-xl">
              <div className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-text-faint">
                Overlays
              </div>
              {OVERLAYS.map((o) => (
                <button
                  key={o.id}
                  onClick={() => toggleOverlay(o.id)}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-2xs text-text-muted hover:bg-bg-hover hover:text-text"
                >
                  <span
                    className={cn(
                      "flex h-3 w-3 items-center justify-center rounded-sm border",
                      overlays.has(o.id)
                        ? "border-accent bg-accent/30 text-accent"
                        : "border-border",
                    )}
                  >
                    {overlays.has(o.id) && "✓"}
                  </span>
                  {o.label}
                </button>
              ))}
              <div className="my-1 border-t border-border" />
              <div className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-text-faint">
                Oscillators
              </div>
              {OSCILLATORS.map((o) => (
                <button
                  key={o.id}
                  onClick={() => toggleOscillator(o.id)}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-2xs text-text-muted hover:bg-bg-hover hover:text-text"
                >
                  <span
                    className={cn(
                      "flex h-3 w-3 items-center justify-center rounded-sm border",
                      oscillators.includes(o.id)
                        ? "border-accent bg-accent/30 text-accent"
                        : "border-border",
                    )}
                  >
                    {oscillators.includes(o.id) && "✓"}
                  </span>
                  {o.label}
                </button>
              ))}
              <div className="my-1 border-t border-border" />
              <div className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-text-faint">
                Volume
              </div>
              <button
                onClick={() => setVolumeProfile((v) => !v)}
                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-2xs text-text-muted hover:bg-bg-hover hover:text-text"
              >
                <span
                  className={cn(
                    "flex h-3 w-3 items-center justify-center rounded-sm border",
                    volumeProfile
                      ? "border-accent bg-accent/30 text-accent"
                      : "border-border",
                  )}
                >
                  {volumeProfile && "✓"}
                </span>
                Volume Profile
              </button>
            </div>
          )}
        </div>

        <div className="flex items-center gap-0.5 rounded-md border border-border bg-bg-elevated p-0.5">
          {DRAW_TOOLS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTool((cur) => (cur === t.id ? "none" : t.id))}
              title={t.title}
              className={cn(
                "flex items-center rounded px-1.5 py-1 transition-colors",
                tool === t.id
                  ? "bg-accent/20 text-accent"
                  : "text-text-muted hover:text-text",
              )}
            >
              <t.icon className="h-3.5 w-3.5" />
            </button>
          ))}
          <button
            onClick={clearDrawings}
            title="Clear drawings"
            disabled={drawings.length === 0}
            className={cn(
              "flex items-center rounded px-1.5 py-1 transition-colors",
              drawings.length === 0
                ? "text-text-faint opacity-40"
                : "text-text-muted hover:text-down",
            )}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>

        <span className="ml-auto text-2xs text-text-faint">
          {isError
            ? "Failed to load"
            : isFetching
              ? "Loading…"
              : `${candles.length} bars`}
        </span>
      </div>

      <div className="relative flex-1 min-h-[300px] w-full">
        <div ref={containerRef} className="absolute inset-0 h-full w-full" />
        {volumeProfile && volProfile && volProfile.bins.length > 0 && (
          <VolumeProfileOverlay
            chartRef={chartRef}
            seriesRef={priceSeriesRef}
            bins={volProfile.bins}
            maxVolume={volProfile.max_volume}
            redrawToken={`${chartType}:${candles.length}:${tf}`}
          />
        )}
        <DrawingCanvas
          chartRef={chartRef}
          seriesRef={priceSeriesRef}
          tool={tool}
          drawings={drawings}
          onCommit={commitDrawing}
          onToolReset={() => setTool("none")}
          redrawToken={`${chartType}:${candles.length}:${tf}`}
        />
        {!isFetching && !isError && candles.length === 0 && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-text-faint">
            No history for {activeSymbol}
          </div>
        )}
      </div>

      {OSCILLATORS.filter((o) => oscillators.includes(o.id)).map((o, i, arr) => (
        <OscillatorPane
          key={o.id}
          paneKey={o.pane}
          title={o.title}
          series={(indicators?.series ?? []).filter((s) => s.pane === o.pane)}
          sync={syncRef.current!}
          showTimeAxis={i === arr.length - 1}
          onClose={() => toggleOscillator(o.id)}
        />
      ))}
    </div>
  );
}
