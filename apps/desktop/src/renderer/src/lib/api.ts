/**
 * REST client for the Python engine. The base URL is resolved at runtime from
 * the preload bridge (the engine port is owned by the main process).
 */
import type {
  AIStatus,
  Alert,
  AlertEvent,
  AlertInput,
  AlertUpdate,
  AnalysisReport,
  Candle,
  ChatMessage,
  CommentatorReport,
  EconomicCalendar,
  FacetHit,
  GlobalSearchResult,
  Holding,
  HoldingInput,
  IndicatorResponse,
  MorningSummary,
  NewsArticle,
  NewsClassification,
  PortfolioSummary,
  Quote,
  ReportRegion,
  SchedulerStatus,
  SecretStatus,
  SecretVerifyResult,
  StocksToWatchDigest,
  SymbolRef,
  VolumeProfileResponse,
  Watchlist,
} from "./contracts";

let baseUrl = "http://127.0.0.1:8787";

export function setEngineBaseUrl(url: string): void {
  baseUrl = url.replace(/\/$/, "");
}

export function getEngineBaseUrl(): string {
  return baseUrl;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`, { signal });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

/** Helper for non-GET JSON requests (POST/PUT/DELETE). */
async function send<T>(
  method: "POST" | "PUT" | "DELETE",
  path: string,
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

const enc = encodeURIComponent;

export const api = {
  searchSymbols: (q: string, signal?: AbortSignal): Promise<SymbolRef[]> =>
    get(`/api/v1/search?q=${encodeURIComponent(q)}`, signal),

  getQuote: (symbol: string, signal?: AbortSignal): Promise<Quote> =>
    get(`/api/v1/quote/${encodeURIComponent(symbol)}`, signal),

  getHistory: (
    symbol: string,
    interval = "1d",
    range = "1y",
    signal?: AbortSignal,
  ): Promise<Candle[]> =>
    get(
      `/api/v1/history/${encodeURIComponent(symbol)}?interval=${interval}&range=${range}`,
      signal,
    ),

  getIndicators: (
    symbol: string,
    indicators: string,
    interval = "1d",
    range = "1y",
    signal?: AbortSignal,
  ): Promise<IndicatorResponse> =>
    get(
      `/api/v1/indicators/${encodeURIComponent(symbol)}?indicators=${encodeURIComponent(
        indicators,
      )}&interval=${interval}&range=${range}`,
      signal,
    ),

  getVolumeProfile: (
    symbol: string,
    bins = 24,
    interval = "1d",
    range = "1y",
    signal?: AbortSignal,
  ): Promise<VolumeProfileResponse> =>
    get(
      `/api/v1/volume-profile/${encodeURIComponent(symbol)}?bins=${bins}&interval=${interval}&range=${range}`,
      signal,
    ),

  getUniverseStats: (signal?: AbortSignal): Promise<Record<string, number>> =>
    get(`/api/v1/symbols/stats`, signal),

  refreshUniverse: async (): Promise<Record<string, number>> => {
    const res = await fetch(`${baseUrl}/api/v1/symbols/refresh`, { method: "POST" });
    if (!res.ok) throw new ApiError("Universe refresh failed", res.status);
    return res.json() as Promise<Record<string, number>>;
  },

  // ---- Watchlists ----------------------------------------------------------
  listWatchlists: (signal?: AbortSignal): Promise<Watchlist[]> =>
    get(`/api/v1/watchlists`, signal),

  createWatchlist: (name: string): Promise<Watchlist> =>
    send("POST", `/api/v1/watchlists`, { name }),

  renameWatchlist: (id: number, name: string): Promise<Watchlist> =>
    send("PUT", `/api/v1/watchlists/${id}`, { name }),

  deleteWatchlist: (id: number): Promise<{ deleted: boolean }> =>
    send("DELETE", `/api/v1/watchlists/${id}`),

  addWatchlistItem: (id: number, symbol: string): Promise<Watchlist> =>
    send("POST", `/api/v1/watchlists/${id}/items`, { symbol }),

  removeWatchlistItem: (id: number, symbol: string): Promise<Watchlist> =>
    send("DELETE", `/api/v1/watchlists/${id}/items/${enc(symbol)}`),

  reorderWatchlistItems: (id: number, symbols: string[]): Promise<Watchlist> =>
    send("PUT", `/api/v1/watchlists/${id}/items`, { symbols }),

  // ---- Portfolio -----------------------------------------------------------
  getPortfolio: (signal?: AbortSignal): Promise<PortfolioSummary> =>
    get(`/api/v1/portfolio`, signal),

  listHoldings: (signal?: AbortSignal): Promise<Holding[]> =>
    get(`/api/v1/holdings`, signal),

  addHolding: (input: HoldingInput): Promise<Holding> =>
    send("POST", `/api/v1/holdings`, input),

  updateHolding: (id: number, input: HoldingInput): Promise<Holding> =>
    send("PUT", `/api/v1/holdings/${id}`, input),

  deleteHolding: (id: number): Promise<{ deleted: boolean }> =>
    send("DELETE", `/api/v1/holdings/${id}`),

  // ---- News ----------------------------------------------------------------
  getNews: (limit = 50, signal?: AbortSignal): Promise<NewsArticle[]> =>
    get(`/api/v1/news?limit=${limit}`, signal),

  refreshNews: (): Promise<{ stored: number }> =>
    send("POST", `/api/v1/news/refresh`),

  getNewsForSymbol: (symbol: string, limit = 30, signal?: AbortSignal): Promise<NewsArticle[]> =>
    get(`/api/v1/news/${enc(symbol)}?limit=${limit}`, signal),

  // ---- AI (Phase 6) --------------------------------------------------------
  aiStatus: (signal?: AbortSignal): Promise<AIStatus> => get(`/api/v1/ai/status`, signal),

  setAiProvider: (active_provider: string, model?: string | null): Promise<AIStatus> =>
    send("PUT", `/api/v1/ai/provider`, { active_provider, model: model ?? null }),

  analyze: (symbol: string): Promise<AnalysisReport> =>
    send("POST", `/api/v1/ai/analyze`, { symbol }),

  getLatestReport: (symbol: string, signal?: AbortSignal): Promise<AnalysisReport> =>
    get(`/api/v1/ai/reports/${enc(symbol)}`, signal),

  classifyNews: (symbol?: string, limit = 12): Promise<NewsClassification[]> =>
    send("POST", `/api/v1/ai/classify`, { symbol: symbol ?? null, limit }),

  // ---- Secrets (write-only) + provider settings ----------------------------
  listSecrets: (signal?: AbortSignal): Promise<SecretStatus[]> =>
    get(`/api/v1/secrets`, signal),

  setSecret: (provider: string, apiKey: string): Promise<SecretStatus> =>
    send("PUT", `/api/v1/secrets/${enc(provider)}`, { api_key: apiKey }),

  deleteSecret: (provider: string): Promise<SecretStatus> =>
    send("DELETE", `/api/v1/secrets/${enc(provider)}`),

  verifySecret: (provider: string, apiKey?: string): Promise<SecretVerifyResult> =>
    send("POST", `/api/v1/secrets/${enc(provider)}/verify`, {
      api_key: apiKey ?? null,
    }),

  // ---- Alerts (Phase 7) ----------------------------------------------------
  listAlerts: (signal?: AbortSignal): Promise<Alert[]> => get(`/api/v1/alerts`, signal),

  createAlert: (input: AlertInput): Promise<Alert> =>
    send("POST", `/api/v1/alerts`, input),

  updateAlert: (id: number, input: AlertUpdate): Promise<Alert> =>
    send("PUT", `/api/v1/alerts/${id}`, input),

  deleteAlert: (id: number): Promise<{ deleted: boolean }> =>
    send("DELETE", `/api/v1/alerts/${id}`),

  listAlertEvents: (limit = 50, signal?: AbortSignal): Promise<AlertEvent[]> =>
    get(`/api/v1/alerts/events?limit=${limit}`, signal),

  // ---- Scheduler & Reports (Phase 8) ---------------------------------------
  schedulerStatus: (signal?: AbortSignal): Promise<SchedulerStatus> =>
    get(`/api/v1/scheduler/status`, signal),

  getMorningSummary: (region: ReportRegion = "us", signal?: AbortSignal): Promise<MorningSummary> =>
    get(`/api/v1/reports/morning?region=${region}`, signal),

  generateMorningSummary: (region: ReportRegion = "us"): Promise<MorningSummary> =>
    send("POST", `/api/v1/reports/morning/generate?region=${region}`),

  getStocksToWatch: (signal?: AbortSignal): Promise<StocksToWatchDigest> =>
    get(`/api/v1/reports/watch`, signal),

  generateStocksToWatch: (): Promise<StocksToWatchDigest> =>
    send("POST", `/api/v1/reports/watch/generate`),

  getEconomicCalendar: (days = 14, signal?: AbortSignal): Promise<EconomicCalendar> =>
    get(`/api/v1/calendar?days=${days}`, signal),

  // ---- Global Search & Commentator (Phase 9) -------------------------------
  globalSearch: (q: string, signal?: AbortSignal): Promise<GlobalSearchResult> =>
    get(`/api/v1/search/global?q=${encodeURIComponent(q)}`, signal),

  facetSymbols: (kind: FacetHit["kind"], label: string, signal?: AbortSignal): Promise<SymbolRef[]> =>
    get(`/api/v1/search/facet/${kind}/${encodeURIComponent(label)}`, signal),

  getCommentatorReport: (symbol: string, signal?: AbortSignal): Promise<CommentatorReport> =>
    get(`/api/v1/commentator/${encodeURIComponent(symbol)}`, signal),
};

/**
 * Stream an AI chat completion over Server-Sent Events. Calls `onToken` for each
 * text chunk; resolves when the stream ends (`[DONE]`). Throws ApiError on a
 * provider/transport failure (including an `event: error` frame).
 */
export async function streamChat(
  messages: ChatMessage[],
  symbol: string | null,
  onToken: (text: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${baseUrl}/api/v1/ai/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, symbol }),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new ApiError(res.statusText || "AI chat failed", res.status);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      let event = "message";
      let dataStr = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
      }
      if (!dataStr) continue;
      if (dataStr === "[DONE]") return;
      const parsed = JSON.parse(dataStr) as unknown;
      if (event === "error") throw new ApiError(String(parsed), 503);
      onToken(parsed as string);
    }
  }
}
