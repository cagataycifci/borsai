import { useEffect, useRef, useState } from "react";
import type { IChartApi, ISeriesApi } from "lightweight-charts";
import type { VolumeBin } from "../../lib/contracts";

interface Bar {
  y: number; // top of the bar (px)
  h: number; // bar height (px)
  w: number; // bar width (px, ∝ volume)
  poc: boolean;
}

interface Props {
  chartRef: React.MutableRefObject<IChartApi | null>;
  seriesRef: React.MutableRefObject<ISeriesApi<
    "Candlestick" | "Line" | "Area"
  > | null>;
  bins: VolumeBin[];
  maxVolume: number;
  /** Bumped by the parent when the price series is rebuilt, to force a redraw. */
  redrawToken: string;
}

const ACCENT = "#2f81f7";

/**
 * Volume-by-price overlay drawn as an SVG anchored to the price chart's right
 * edge. Bar vertical positions come from the price series' `priceToCoordinate`,
 * so they track the price axis through pan/zoom/resize. Purely presentational
 * and `pointer-events-none`, so it never intercepts chart interaction.
 */
export function VolumeProfileOverlay({
  chartRef,
  seriesRef,
  bins,
  maxVolume,
  redrawToken,
}: Props): JSX.Element {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [bars, setBars] = useState<Bar[]>([]);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const chart = chartRef.current;
    const series = seriesRef.current;
    const el = wrapRef.current;
    if (!chart || !series || !el || bins.length === 0 || maxVolume <= 0) {
      setBars([]);
      return;
    }

    let frame = 0;
    const redraw = (): void => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const w = el.clientWidth;
        setWidth(w);
        const maxBar = Math.min(130, w * 0.28);
        const next: Bar[] = [];
        for (const b of bins) {
          const yMid = series.priceToCoordinate(b.mid);
          const yLow = series.priceToCoordinate(b.low);
          const yHigh = series.priceToCoordinate(b.high);
          if (yMid == null || yLow == null || yHigh == null) continue;
          const h = Math.max(1, Math.abs(yLow - yHigh) - 1);
          next.push({
            y: yMid - h / 2,
            h,
            w: (b.volume / maxVolume) * maxBar,
            poc: b.poc,
          });
        }
        setBars(next);
      });
    };

    redraw();
    const ts = chart.timeScale();
    ts.subscribeVisibleLogicalRangeChange(redraw);
    const ro = new ResizeObserver(redraw);
    ro.observe(el);

    return () => {
      cancelAnimationFrame(frame);
      ts.unsubscribeVisibleLogicalRangeChange(redraw);
      ro.disconnect();
    };
  }, [chartRef, seriesRef, bins, maxVolume, redrawToken]);

  // Anchor bars just left of the price axis (≈60px wide).
  const rightEdge = Math.max(0, width - 62);

  return (
    <div ref={wrapRef} className="pointer-events-none absolute inset-0 z-10">
      <svg className="h-full w-full">
        {bars.map((b, i) => (
          <rect
            key={i}
            x={rightEdge - b.w}
            y={b.y}
            width={b.w}
            height={b.h}
            fill={b.poc ? `${ACCENT}66` : "#8a97a833"}
            stroke={b.poc ? ACCENT : "transparent"}
            strokeWidth={b.poc ? 1 : 0}
          />
        ))}
      </svg>
    </div>
  );
}
