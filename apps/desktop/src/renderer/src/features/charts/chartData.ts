/**
 * Pure transforms from engine OHLCV candles to lightweight-charts series data.
 * Kept separate from the React component so they're trivially unit-testable and
 * free of chart/DOM concerns.
 */
import type {
  CandlestickData,
  HistogramData,
  LineData,
  UTCTimestamp,
} from "lightweight-charts";
import type { Candle } from "../../lib/contracts";

export type ChartType = "candles" | "line" | "area" | "heikin";

const UP = "#16c784";
const DOWN = "#ea3943";

function toTime(iso: string): UTCTimestamp {
  return Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;
}

/**
 * lightweight-charts requires data sorted ascending with strictly unique
 * timestamps. yfinance is usually clean, but DST folds and provider quirks can
 * produce duplicates — keep the last bar for any repeated timestamp.
 */
function normalize(candles: Candle[]): { t: UTCTimestamp; c: Candle }[] {
  const byTime = new Map<number, Candle>();
  for (const c of candles) byTime.set(toTime(c.time), c);
  return [...byTime.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([t, c]) => ({ t: t as UTCTimestamp, c }));
}

export function toCandlestickData(candles: Candle[]): CandlestickData[] {
  return normalize(candles).map(({ t, c }) => ({
    time: t,
    open: c.open,
    high: c.high,
    low: c.low,
    close: c.close,
  }));
}

export function toLineData(candles: Candle[]): LineData[] {
  return normalize(candles).map(({ t, c }) => ({ time: t, value: c.close }));
}

/**
 * Heikin-Ashi smoothing. haClose is the OHLC average; haOpen is the running mean
 * of the previous HA bar's open/close (seeded from the first real bar).
 */
export function toHeikinAshiData(candles: Candle[]): CandlestickData[] {
  const rows = normalize(candles);
  const out: CandlestickData[] = [];
  let prevOpen = 0;
  let prevClose = 0;
  rows.forEach(({ t, c }, i) => {
    const haClose = (c.open + c.high + c.low + c.close) / 4;
    const haOpen = i === 0 ? (c.open + c.close) / 2 : (prevOpen + prevClose) / 2;
    out.push({
      time: t,
      open: haOpen,
      high: Math.max(c.high, haOpen, haClose),
      low: Math.min(c.low, haOpen, haClose),
      close: haClose,
    });
    prevOpen = haOpen;
    prevClose = haClose;
  });
  return out;
}

/** Map engine indicator points to line data, dropping warm-up / undefined gaps. */
export function toOverlayLineData(
  points: { time: string; value: number | null }[],
): LineData[] {
  const out: LineData[] = [];
  for (const p of points) {
    if (p.value == null || !Number.isFinite(p.value)) continue;
    out.push({ time: toTime(p.time), value: p.value });
  }
  return out;
}

export function toVolumeData(candles: Candle[]): HistogramData[] {
  return normalize(candles).map(({ t, c }) => ({
    time: t,
    value: c.volume,
    color: c.close >= c.open ? `${UP}55` : `${DOWN}55`,
  }));
}

/**
 * Map an oscillator indicator series (e.g. MACD histogram) to histogram data,
 * colouring each bar by sign and dropping warm-up / undefined gaps.
 */
export function toOscillatorHistogram(
  points: { time: string; value: number | null }[],
): HistogramData[] {
  const out: HistogramData[] = [];
  for (const p of points) {
    if (p.value == null || !Number.isFinite(p.value)) continue;
    out.push({
      time: toTime(p.time),
      value: p.value,
      color: p.value >= 0 ? `${UP}aa` : `${DOWN}aa`,
    });
  }
  return out;
}
