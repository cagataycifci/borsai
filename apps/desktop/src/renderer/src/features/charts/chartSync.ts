/**
 * Time-scale synchroniser for stacked lightweight-charts instances.
 *
 * lightweight-charts v4 has no native multi-pane support, so each oscillator
 * (RSI/MACD/Stochastic/ATR) lives in its own `createChart` instance below the
 * price chart. This coordinator keeps every registered chart panning/zooming
 * together by mirroring the visible *logical* range — all panes share the same
 * candle index, so logical ranges line up exactly. A re-entrancy guard prevents
 * the mirror writes from echoing back into an infinite loop.
 */
import type { IChartApi } from "lightweight-charts";

export class ChartSync {
  private charts = new Set<IChartApi>();
  private applying = false;

  /** Register a chart and immediately align it to any existing member's range. */
  add(chart: IChartApi): void {
    const reference = this.charts.values().next().value as IChartApi | undefined;
    this.charts.add(chart);

    chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (this.applying || range == null) return;
      this.applying = true;
      try {
        for (const other of this.charts) {
          if (other !== chart) other.timeScale().setVisibleLogicalRange(range);
        }
      } finally {
        this.applying = false;
      }
    });

    if (reference) this.alignFromOthers(chart);
  }

  remove(chart: IChartApi): void {
    this.charts.delete(chart);
  }

  /** Pull the current visible range from another member onto `chart`. */
  alignFromOthers(chart: IChartApi): void {
    for (const other of this.charts) {
      if (other === chart) continue;
      const range = other.timeScale().getVisibleLogicalRange();
      if (range) {
        this.applying = true;
        try {
          chart.timeScale().setVisibleLogicalRange(range);
        } finally {
          this.applying = false;
        }
      }
      return;
    }
  }
}
