# TASKS.md — Borsa AI Terminal

Legend: ✅ done · 🔄 in progress · ⬜ todo

## Phase 1 — Foundation ✅ (complete & verified)
- ✅ Architecture, roadmap, handoff docs
- ✅ Monorepo (npm workspaces) + .gitignore/.editorconfig + dev orchestrator scripts
- ✅ Engine skeleton: FastAPI app factory + lifespan, config (pydantic-settings),
  logging, async TTL cache, Fernet+keyring secret box
- ✅ Data layer: `MarketDataAdapter` protocol + `YFinanceAdapter` + `MarketDataService`
- ✅ Endpoints: `/health`, `/api/v1/quote`, `/api/v1/search`, `/api/v1/history`,
  `/api/v1/fundamentals`, `WS /ws/stream`
- ✅ Electron main: spawn/supervise engine (reuse running one in dev), lifecycle
- ✅ Preload bridge (`window.borsa`); React shell (dark theme, dockview, stores,
  WS client, REST client); dashboard WatchPanel + DetailPanel
- ✅ End-to-end vertical slice verified (AAPL + ASELS.IS live quotes)
- ✅ Electron extract-zip workaround (`scripts/fix-electron.mjs` postinstall)

## Phase 2 — Market Data ✅ (complete & verified)
- ✅ DB foundation: SQLAlchemy 2.0 (sync) + SQLite (WAL) + Alembic; models
  settings/secrets/symbols/quotes_cache; repositories; `init_db()` runs migrations
- ✅ Initial Alembic migration `9518455a983e`; `env.py` renders UTCDateTime portably
- ✅ Settings service (JSON KV) + routes `GET/PUT /api/v1/settings[/{key}]`
- ✅ Secrets service (Fernet-encrypted, write-only) + routes
  `GET/PUT/DELETE /api/v1/secrets[/{provider}]`
- ✅ Provider order config + routes `GET/PUT /api/v1/providers/order`
- ✅ Symbol universe: US loader (NASDAQ Trader files) + BIST seed (`bist_seed.json`)
- ✅ `SymbolUniverseService` (refresh/ensure_seeded/search/stats) + repository
- ✅ Routes `GET /api/v1/symbols/stats`, `POST /api/v1/symbols/refresh`
- ✅ Universe-backed ranked search wired into `/api/v1/search` (+ provider fallback)
- ✅ `FinnhubAdapter` (US) + `factory.py` building provider chain from config+secrets
- ✅ Write-through quote persistence (`SqliteQuoteStore`) + stale fallback
- ✅ Frontend: `UniverseBadge` (count + refresh); `api.ts` universe endpoints
- ✅ Tests: settings/secrets, universe search ranking, quote persistence (13 total)
- ✅ `auto_seed` config flag; ruff clean; typecheck + build pass

## Phase 3 — Charts ✅ (complete & verified)
- ✅ Engine: 4h history resample (`app/technical/resample.py` + wired into
  `MarketDataService.get_history`: fetch 1h → resample to 4h)
- ✅ Renderer: `features/charts/ChartPanel.tsx` (lightweight-charts v4) + registered
  in Workspace as the **Chart** panel; volume histogram overlay
- ✅ Timeframe selector (1m/5m/15m/1h/4h/1D/1W/1M)
- ✅ Chart types: candlestick, line, area, Heikin-Ashi
- ✅ Indicators — **engine** `app/technical/indicators.py` (SMA, EMA, RSI, MACD,
  VWAP, Bollinger, Ichimoku, Stochastic, ATR) + `GET /api/v1/indicators/{symbol}`
- ✅ Indicators — **renderer** price-pane overlays (SMA 20/50, EMA 20/50, Bollinger,
  VWAP) via an Indicators dropdown
- ✅ Indicators — oscillator sub-panes (RSI/MACD/Stochastic/ATR) in synced secondary
  charts (`OscillatorPane.tsx` + `chartSync.ts`); grouped Overlays/Oscillators menu
- ✅ Volume Profile — engine `app/technical/volume_profile.py` +
  `GET /api/v1/volume-profile/{symbol}`; renderer SVG overlay anchored to the price
  axis with POC highlight (`VolumeProfileOverlay.tsx`)
- ✅ Drawing tools: trend lines, horizontal support/resistance, Fibonacci
  retracement (`DrawingCanvas.tsx` + `drawings.ts`), per-symbol, with a toolbar
- ✅ Tests: `test_volume_profile.py` (5), `test_volume_profile_api.py` (1) — 29 total

## Phase 4 — Watchlists & Portfolio ✅ (complete & verified)
- ✅ DB tables watchlists/watchlist_items/holdings (+ migration `8c2159eb5303`,
  FK cascade + unique `(watchlist_id, symbol)`)
- ✅ CRUD APIs (`app/watchlists/`, `app/portfolio/`); persisted multiple watchlists
  (replaced the in-memory default); `ensure_default` seeds a starter list
- ✅ Portfolio: quantity, avg cost, currency, purchase date, target, stop-loss, notes;
  live P&L (`position_from`/`summarize`) with per-currency totals (no FX conversion)
- ✅ Renderer: API-backed watchlist store (multiple lists, surface preserved);
  Watchlists panel (CRUD + reorder) and Portfolio panel (live P&L + holding form),
  registered in `panelRegistry.tsx` (placeholders removed)
- ✅ Tests: `test_portfolio.py`, `test_watchlists_api.py`, `test_portfolio_api.py`
  (35 total); typecheck + build pass; live smoke test green

## Phase 5 — News Layer ✅ (complete & verified)
- ✅ `NewsSource` shape + pure RSS/Atom parser (`app/news/parser.py`, unit-tested);
  RSS sources (Yahoo Finance/CNBC/MarketWatch) + Yahoo per-symbol headlines
- ✅ `news` table (`url` unique = dedup, migration `f2b025ee9893`) + `NewsService`
  (concurrent fan-out, dedup, store)
- ✅ Routes `GET /api/v1/news` (auto-refresh when empty), `POST /api/v1/news/refresh`,
  `GET /api/v1/news/{symbol}`
- ✅ Renderer News panel (market/symbol toggle, refresh, external links); registered
  in `panelRegistry.tsx`
- ✅ Tests: `test_news_parser.py`, `test_news_api.py` (39 total); typecheck + build
  pass; live smoke test green
- ⬜ KAP (BIST) + SEC EDGAR parsers (deferred follow-up — the `NewsSource` shape
  makes them additive)

## Phase 6 — AI Layer ✅ (complete & verified)
- ✅ AI provider abstraction (`app/ai/`): `AIProvider` protocol + Anthropic
  (reference, `claude-opus-4-8`), OpenAI, Gemini, Ollama adapters (lazy SDKs);
  `factory.py` builds the active provider from `ai.active_provider` + encrypted
  secrets
- ✅ `AIService`: context bundle (quote + indicators + recent news) → structured
  `AnalysisReport`; persisted to `ai_reports` (migration `c4d2e1f0a9b8`)
- ✅ `POST /api/v1/ai/analyze` (report) + `POST /api/v1/ai/chat` (SSE streaming) +
  `GET /api/v1/ai/status` + `PUT /api/v1/ai/provider` +
  `GET /api/v1/ai/reports/{symbol}` + `POST /api/v1/ai/classify`
- ✅ News classification (bullish/bearish/neutral + importance + why)
- ✅ Renderer: AI panel (Report + Chat tabs, streaming), Settings panel (provider
  select + write-only API keys); "AI Analysis" button opens the AI panel
- ✅ Tests: `test_ai_api.py` (3, fake provider/offline) — 42 total; typecheck +
  build pass; live smoke test green (status, no-key 503, provider switch)
- ⬜ Live model call unverified (no API key on dev machine — covered by fakes)

## Phase 7 — Alerts & Notifications ✅ (complete & verified)
- ✅ Pure alert engine (`app/alerts/engine.py`): price above/below, % up/down,
  volume-above, RSI above/below, MACD signal cross (up/down), golden/death SMA cross
- ✅ `alerts` + `alert_events` tables (migration `b7e3a1c92d55`); `AlertService`
  CRUD + event feed; `AlertMonitor` background loop broadcasts fired alerts over
  `WS /ws/stream` via a `ConnectionHub`, respecting per-alert cooldown
- ✅ Routes `GET/POST /api/v1/alerts`, `PUT/DELETE /api/v1/alerts/{id}`,
  `GET /api/v1/alerts/events`
- ✅ Native desktop notifications via the existing preload `window.borsa.notify`
  (fired from `useMarketStream` on `alert` frames → `useAlertsStore`)
- ✅ Renderer Alerts panel (CRUD + On/Off + live triggered feed), registered in
  `panelRegistry.tsx` (placeholder removed)
- ✅ Auto-refreshing portfolio "news on your holdings" section (60s) atop the
  existing 15s live-P&L refresh
- ✅ Tests: `test_alerts.py` (4) + `test_alerts_api.py` (1) — 47 total; typecheck +
  build pass; live smoke test green
- ⬜ News/AI-score alert types deferred (additive — engine + type enum extend cleanly)

## Phase 8 — Scheduler & Reports ✅ (complete & verified)
- ✅ APScheduler (`AsyncIOScheduler`): news refresh (4h), morning US/TR/global cron,
  stocks-to-watch digest; `BORSA_SCHEDULER_ENABLED` flag (off in tests)
- ✅ Morning market summary with template fallback + optional AI enhancement
- ✅ Economic calendar (offline FOMC/CPI/NFP/ECB + recurring jobless claims)
- ✅ Stocks-to-watch digest from watchlists + portfolio movers
- ✅ `scheduled_reports` table (migration `d8f4b2a31c67`) + REST routes + Reports panel
- ✅ Tests: `test_scheduler_*.py` (5) — 52 total at phase end

## Phase 9 — Commentator/Sentiment + Search ✅ (complete & verified)
- ✅ Global search: `GET /api/v1/search/global` (symbols + sector/industry/country facets)
- ✅ `GET /api/v1/search/facet/{kind}/{label}` + extended `SymbolRepository`
- ✅ Commentator consensus: `GET /api/v1/commentator/{symbol}` (news + AI classify → attributed opinions)
- ✅ Pure `compute_consensus()` + `CommentatorPanel` + enhanced `SearchBar`
- ✅ Tests: `test_commentator_*.py`, `test_search_api.py` (5) — 57 total at phase end

## Phase 10 — Hardening ✅ (complete & verified)
- ✅ GitHub Actions CI (engine pytest+ruff, desktop typecheck+build)
- ✅ WS integration tests (`test_ws.py`)
- ✅ PyInstaller spec (`borsa-engine.spec`) + `scripts/build-engine.mjs`
- ✅ electron-builder config + prod `manager.ts` path with binary check
- ✅ Root `npm run package` orchestration
- ⬜ OpenAPI→TS codegen deferred (contracts remain hand-mirrored)
- ⬜ Full installer smoke test on packaged Windows build (manual)

## Backlog / tech debt
- ⬜ KAP (BIST disclosures) + SEC EDGAR news sources (Phase 5 shipped RSS + Yahoo
  per-symbol; the `NewsSource` shape makes these additive)
- ⬜ Full BIST listing via KAP scraper (`load_bist_full`)
- ⬜ Verify Finnhub adapter with a live API key
- ⬜ Replace 5s WS polling with real-time push when a paid provider is added
