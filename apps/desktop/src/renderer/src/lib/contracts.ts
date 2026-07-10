/**
 * TypeScript mirror of the engine's Pydantic models (services/engine/app/data/models.py).
 * Keep in sync when the engine models change. (Phase 10 may auto-generate these
 * from the OpenAPI schema.)
 */

export type Exchange = "BIST" | "NYSE" | "NASDAQ" | "AMEX" | "OTHER";
export type AssetType = "EQUITY" | "ETF" | "INDEX" | "CRYPTO" | "OTHER";

export interface SymbolRef {
  symbol: string;
  display_symbol: string;
  name: string;
  exchange: Exchange;
  asset_type: AssetType;
  currency: string;
}

export interface Quote {
  symbol: string;
  display_symbol: string;
  name: string | null;
  exchange: Exchange;
  currency: string;
  price: number | null;
  previous_close: number | null;
  open: number | null;
  day_high: number | null;
  day_low: number | null;
  change: number | null;
  change_percent: number | null;
  volume: number | null;
  market_cap: number | null;
  pe_ratio: number | null;
  eps: number | null;
  dividend_yield: number | null;
  week52_high: number | null;
  week52_low: number | null;
  sector: string | null;
  industry: string | null;
  source: string | null;
  as_of: string | null;
}

export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorPoint {
  time: string;
  value: number | null;
}

export interface IndicatorSeries {
  name: string;
  key: string;
  pane: "price" | "rsi" | "macd" | "stoch" | "atr";
  style: "line" | "histogram";
  points: IndicatorPoint[];
}

export interface IndicatorResponse {
  symbol: string;
  interval: string;
  series: IndicatorSeries[];
}

export interface VolumeBin {
  low: number;
  high: number;
  mid: number;
  volume: number;
  poc: boolean;
}

export interface VolumeProfileResponse {
  symbol: string;
  interval: string;
  bins: VolumeBin[];
  poc: number | null;
  max_volume: number;
}

// ---- Phase 4: Watchlists & Portfolio --------------------------------------

export interface Watchlist {
  id: number;
  name: string;
  position: number;
  symbols: string[];
}

export interface Holding {
  id: number;
  symbol: string;
  quantity: number;
  avg_cost: number;
  currency: string;
  purchase_date: string | null;
  target_price: number | null;
  stop_loss: number | null;
  notes: string | null;
}

/** Payload for creating/updating a holding (all-optional fields for updates). */
export interface HoldingInput {
  symbol?: string;
  quantity?: number;
  avg_cost?: number;
  currency?: string;
  purchase_date?: string | null;
  target_price?: number | null;
  stop_loss?: number | null;
  notes?: string | null;
}

export interface PortfolioPosition {
  holding: Holding;
  name: string | null;
  exchange: Exchange | null;
  price: number | null;
  change: number | null;
  change_percent: number | null;
  market_value: number | null;
  cost_basis: number;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  day_pnl: number | null;
}

export interface PortfolioTotal {
  currency: string;
  market_value: number;
  cost_basis: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  day_pnl: number;
}

export interface PortfolioSummary {
  positions: PortfolioPosition[];
  totals: PortfolioTotal[];
}

// ---- Phase 5: News -------------------------------------------------------

export interface NewsArticle {
  id: number;
  source: string;
  title: string;
  url: string;
  summary: string | null;
  symbols: string[];
  published_at: string | null;
}

// ---- Phase 6: AI ---------------------------------------------------------

export type Sentiment = "bullish" | "bearish" | "neutral";

export interface AnalysisReport {
  symbol: string;
  provider: string;
  model: string;
  sentiment: Sentiment;
  rating: number; // 1 (strong sell) … 5 (strong buy)
  summary: string;
  key_points: string[];
  risks: string[];
  technical_outlook: string;
  recommendation: string;
  disclaimer: string;
  created_at: string | null;
}

export interface NewsClassification {
  id: number | null;
  title: string;
  url: string;
  sentiment: Sentiment;
  importance: number; // 1 (noise) … 5 (market-moving)
  rationale: string;
}

export interface AIStatus {
  ready: boolean;
  active_provider: string;
  model: string;
  configured: Record<string, boolean>;
  providers: string[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

/** Write-only secret status mirror (services/engine/app/settings/schemas.py). */
export interface SecretStatus {
  provider: string;
  configured: boolean;
}

export interface SecretVerifyResult {
  provider: string;
  ok: boolean;
  message: string;
}

// ---- Phase 7: Alerts -----------------------------------------------------

export type AlertType =
  | "price_above"
  | "price_below"
  | "percent_up"
  | "percent_down"
  | "volume_above"
  | "rsi_above"
  | "rsi_below"
  | "macd_cross_up"
  | "macd_cross_down"
  | "golden_cross"
  | "death_cross";

export interface Alert {
  id: number;
  symbol: string;
  type: AlertType;
  threshold: number | null;
  params: Record<string, number> | null;
  active: boolean;
  cooldown_seconds: number;
  note: string | null;
  last_triggered_at: string | null;
}

export interface AlertInput {
  symbol: string;
  type: AlertType;
  threshold?: number | null;
  params?: Record<string, number> | null;
  cooldown_seconds?: number;
  note?: string | null;
}

export interface AlertUpdate {
  threshold?: number | null;
  params?: Record<string, number> | null;
  active?: boolean;
  cooldown_seconds?: number;
  note?: string | null;
}

export interface AlertEvent {
  id: number | null;
  alert_id: number | null;
  symbol: string;
  type: AlertType;
  message: string;
  price: number | null;
  created_at: string | null;
}

// ---- Phase 8: Scheduler & Reports ----------------------------------------

export type ReportRegion = "us" | "tr" | "global";

export interface QuoteSnapshot {
  symbol: string;
  display_symbol: string;
  name: string | null;
  price: number | null;
  change: number | null;
  change_percent: number | null;
  currency: string;
}

export interface NewsHeadline {
  title: string;
  source: string;
  url: string;
}

export interface MorningSummary {
  region: ReportRegion;
  title: string;
  overview: string;
  benchmarks: QuoteSnapshot[];
  headlines: NewsHeadline[];
  highlights: string[];
  ai_enhanced: boolean;
  generated_at: string;
}

export interface WatchPick {
  symbol: string;
  display_symbol: string;
  name: string | null;
  price: number | null;
  change_percent: number | null;
  reason: string;
}

export interface StocksToWatchDigest {
  title: string;
  overview: string;
  picks: WatchPick[];
  generated_at: string;
}

export interface EconomicEvent {
  title: string;
  country: string;
  impact: string;
  event_at: string;
  category: string | null;
}

export interface EconomicCalendar {
  events: EconomicEvent[];
  from_date: string;
  to_date: string;
}

export interface SchedulerJobInfo {
  id: string;
  name: string;
  next_run: string | null;
}

export interface SchedulerStatus {
  running: boolean;
  jobs: SchedulerJobInfo[];
}

// ---- Phase 9: Global Search & Commentator --------------------------------

export type FacetKind = "sector" | "industry" | "country";

export interface FacetHit {
  kind: FacetKind;
  label: string;
  count: number;
  sample_symbols: SymbolRef[];
}

export interface GlobalSearchResult {
  query: string;
  symbols: SymbolRef[];
  facets: FacetHit[];
}

export type ConsensusLabel = "bullish" | "bearish" | "neutral" | "mixed";

export interface AttributedOpinion {
  source: string;
  title: string;
  url: string;
  sentiment: Sentiment;
  importance: number;
  rationale: string;
}

export interface CommentatorReport {
  symbol: string;
  consensus: ConsensusLabel;
  agreement_score: number;
  disagreement: boolean;
  summary: string;
  opinions: AttributedOpinion[];
  bullish_count: number;
  bearish_count: number;
  neutral_count: number;
  generated_at: string;
}

/** WebSocket server → client frames. */
export type StreamFrame =
  | { type: "quote"; data: Quote }
  | { type: "alert"; data: AlertEvent }
  | { type: "report"; data: { kind: string; payload: unknown } }
  | { type: "pong" }
  | { type: "error"; message: string };
