# Changelog — Borsa AI Terminal

All notable changes per session/phase. Dates are local.

## [Unreleased]

### 2026-08-12 — OSS foundation and verification

- Added MIT licensing, contribution, governance, support, conduct, and security policies.
- Added issue/PR templates, Dependabot configuration, line-ending policy, and Windows setup helper.
- Rewrote public status documentation to distinguish implemented features from release readiness.
- Verified 64 engine tests, Ruff, desktop typecheck, and desktop production build.
- Recorded the npm audit baseline and remaining packaging/live-provider verification work.

### Session 2026-07-09 — Phases 8–10 complete

**Phase 8 — Scheduler & Reports**
- `app/scheduler/`: APScheduler jobs, morning summaries (US/TR/global), economic
  calendar, stocks-to-watch digest, `scheduled_reports` table + REST routes.
- Renderer `ReportsPanel` + Sidebar entry.

**Phase 9 — Commentator/Sentiment + Global Search**
- `app/search/`: global search with sector/industry/country facets.
- `app/commentator/`: attributed news opinions + consensus scoring.
- Enhanced `SearchBar`, new `CommentatorPanel`.

**Phase 10 — Hardening**
- GitHub Actions CI, WS integration tests, PyInstaller spec, electron-builder
  config, `npm run package` orchestration.

### Session 2026-06-29 — Phase 7 (Alerts & Notifications) complete

**Added — Engine**
- **Alerts package** (`app/alerts/`): a **pure evaluation engine** (`engine.py`)
  with `Snapshot`/`Indicators` dataclasses and an `evaluate()` that covers price
  above/below, % up/down today, volume-above, RSI above/below, MACD signal-line
  cross (up/down), and golden/death SMA cross — all decided from scalar values so
  they're unit-testable with no DB or network. `build_indicators()` derives those
  scalars from a candle series via `app/technical`.
- **`AlertService`** (`service.py`, direct `session_scope` style): CRUD +
  `active_grouped()` (active alerts by symbol) + `record_event()` (stamps
  `last_triggered_at`, persists an event) + `recent_events()`.
- **`AlertMonitor`** (`monitor.py`): a background task (started in the app
  lifespan) that every 15s evaluates active alerts — fetching a quote once per
  symbol, indicators once per symbol only when a technical alert needs them — and
  broadcasts fired alerts to all WebSocket clients via a `ConnectionHub`,
  respecting each alert's cooldown. Resilient loop (one bad symbol never kills it).
- **DB**: `AlertRow` + `AlertEventRow` (`alerts`, `alert_events`; event→alert FK
  `ON DELETE SET NULL`). Alembic migration `b7e3a1c92d55` (chain: … → ai_reports →
  **alerts**, single head verified).
- **Routes** (`app/api/alert_routes.py`): `GET/POST /api/v1/alerts`,
  `PUT/DELETE /api/v1/alerts/{id}`, `GET /api/v1/alerts/events` (feed). Threshold
  types without a threshold are rejected (400).
- **WS**: each `/ws/stream` connection registers with the `ConnectionHub`; the
  frame set gains `{"type":"alert","data":<AlertEvent>}`. Wired via `deps.py` +
  `main.py` (service + hub + monitor on `app.state`; monitor stopped on shutdown).
- **Tests**: `test_alerts.py` (4 — pure conditions incl. crosses, `build_indicators`,
  and a monitor trigger→broadcast→cooldown test with a fake market) +
  `test_alerts_api.py` (1 — CRUD + validation + events feed). **47 total.**

**Added — Renderer**
- **Alerts panel** (`features/alerts/AlertsPanel.tsx`): create form (symbol +
  type + conditional threshold), a saved-alert list with On/Off toggle + delete,
  and a live "recently triggered" feed (seeded from `GET /alerts/events`, appended
  from the stream).
- **Live alert frames + native notifications**: `useMarketStream` now handles
  `alert` frames — pushing them into a new `useAlertsStore` and firing a native OS
  notification via the existing `window.borsa.notify` bridge.
- **Portfolio "news on your holdings"**: `PortfolioPanel` gained an auto-refreshing
  (60s) section that filters market news to owned symbols (on top of the existing
  15s live-P&L refresh).
- `panelRegistry.tsx` registers the real **Alerts** panel (placeholder removed);
  `contracts.ts` + `api.ts` gained the alert types/endpoints.

**Verified**: engine `pytest` (47) + `ruff check app` clean; desktop typecheck +
build pass; live smoke test (uvicorn) — migration chain applies through `alerts`,
alert CRUD persists over HTTP, threshold validation returns 400, events feed works.
The monitor firing path is covered by the fake-market unit test.

### Session 2026-06-29 — Phase 6 (AI Layer) complete

**Added — Engine**
- **AI package** (`app/ai/`): a provider-agnostic `AIProvider` protocol
  (`base.py`) mirroring the data-adapter pattern, with two primitives —
  `complete()` (non-streaming, used for analysis + news classification) and
  `stream()` (async text chunks, used for chat). Concrete adapters in
  `app/ai/providers/`: **Anthropic** (reference/default, official `anthropic`
  async SDK, model `claude-opus-4-8`), **OpenAI**, **Gemini**, and **Ollama**
  (local, keyless). Heavy SDKs are imported lazily so only the active provider's
  dependency must be installed.
- **Factory** (`app/ai/factory.py`): `build_ai_provider()` constructs the active
  provider from the `ai.active_provider` setting + the encrypted secrets store
  (returns `None` when a required key is missing, so the service reports
  "not ready" instead of erroring).
- **AIService** (`app/ai/service.py`): assembles a context bundle (latest quote +
  summarized key indicators from `app/technical` + recent `app/news`) and prompts
  the model. `analyze()` returns a structured `AnalysisReport` (sentiment, 1–5
  rating, summary, key points, risks, technical outlook, recommendation) and
  persists it; `chat_stream()` streams chat (optionally grounded on a symbol);
  `classify_news()` labels headlines bullish/bearish/neutral + importance + why.
  Lenient JSON parsing tolerates fenced/prose-wrapped model output. The provider
  is built fresh per request, so a key entered in Settings takes effect without a
  restart.
- **DB**: `AiReportRow` (`ai_reports` table) + Alembic migration `c4d2e1f0a9b8`
  (chain: initial → watchlists → news → **ai_reports**, single head verified).
- **Settings**: `SettingsService` gained `get/set_active_ai_provider` and
  `get/set_ai_model` (keys `ai.active_provider`, `ai.model`).
- **Routes** (`app/api/ai_routes.py`): `GET /api/v1/ai/status`,
  `PUT /api/v1/ai/provider`, `POST /api/v1/ai/analyze`,
  `GET /api/v1/ai/reports/{symbol}`, `POST /api/v1/ai/classify`, and
  `POST /api/v1/ai/chat` (Server-Sent Events; tokens as `data:`, terminated by
  `data: [DONE]`, provider errors as an `event: error` frame). Wired via
  `deps.py` + `main.py` (service constructed after the data layer).
- **Dependency**: added `anthropic>=0.40` (the reference provider) to
  `pyproject.toml`.
- **Tests**: `test_ai_api.py` (3) with a fake provider + fake market/news layers —
  status + provider select, analyze + persistence + retrieval + classification,
  and SSE chat. **42 total**, no live API key required.

**Added — Renderer**
- **AI panel** (`features/ai/AiPanel.tsx`): tabbed **Report** / **Chat**. Report
  shows a sentiment badge, rating, summary, key points, risks, technical outlook,
  recommendation, and provenance; loads the latest stored report on symbol change
  and re-runs on demand. Chat streams tokens over SSE, grounded on the active
  symbol, with a not-configured banner linking to Settings.
- **Settings panel** (`features/settings/SettingsPanel.tsx`): pick the active AI
  provider + optional model override, and manage write-only, encrypted API keys
  per provider (Save/Clear with a configured indicator).
- **Wiring**: the DetailPanel "AI Analysis" button now opens the real AI panel
  (placeholder modal removed). `panelRegistry.tsx` registers the `ai` and
  `settings` panels (placeholders removed). `lib/api.ts` gained AI + secrets
  endpoints and a `streamChat()` SSE helper; `contracts.ts` gained the AI types.

**Verified**: engine `pytest` (42) + `ruff check app` clean; desktop typecheck +
build pass; live smoke test (uvicorn) — migration chain applies through
`ai_reports`, `/ai/status` reports the default Claude provider, `/ai/analyze`
returns a clean 503 with no key, and selecting keyless Ollama flips `ready`.
**A live model call is unverified (no API key on the dev machine)** — same posture
as the Finnhub adapter; the flow is covered by fake-provider tests.

### Session 2026-06-28 — Fix: false "engine offline" banner in dev

**Fixed**
- Startup race: `npm run dev` launches the Python engine and Electron together,
  but the Electron `EngineManager` probed `/health` once (1.5s) and — when the
  engine was still booting (migrations/first-run seeding) — **spawned a second
  uvicorn** that collided on port 8787, exited, and flipped status to `error`
  (the offline banner) even though the orchestrator's engine was healthy and the
  UI worked. Now `scripts/dev.mjs` sets `BORSA_DEV_ENGINE=1` for the desktop
  process; the manager then waits for the orchestrator's engine (up to 60s, no
  double-spawn). The child-exit handler also re-probes and attaches to any
  healthy engine instead of erroring, and `stop()` never kills an external one.

### Session 2026-06-28 — Phase 5 (News Layer) complete

**Added — Engine**
- **News package** (`app/news/`): provider-agnostic `NewsSource` shape mirroring the
  data-adapter pattern. `parser.py` is a pure, namespace-agnostic RSS 2.0 / Atom
  parser (RFC-822 + ISO-8601 dates, HTML-stripped summaries) — network-free and
  unit-tested. `sources.py`: `RssNewsSource` (general feeds: Yahoo Finance, CNBC,
  MarketWatch) + `YahooSymbolNews` (per-symbol headlines). `NewsService` fans out
  across sources concurrently (`asyncio.gather`, per-source failures isolated),
  dedups by url, and persists.
- **DB**: `NewsRow` (`url` unique = dedup key, `published_at` indexed). Alembic
  migration `f2b025ee9893` (autogenerated; chain verified initial→watchlists→news).
- **Routes**: `GET /api/v1/news` (recent, paginated; auto-refreshes once on an
  empty store), `POST /api/v1/news/refresh`, `GET /api/v1/news/{symbol}` (live
  per-symbol fetch + store, with a DB fallback). Wired via `deps.py` + `main.py`
  (service constructed on startup; no blocking network at boot).
- **Tests**: `test_news_parser.py` (3, offline RSS/Atom/malformed), `test_news_api.py`
  (1, full flow + dedup + per-symbol with fake sources). **39 total.**

**Added — Renderer**
- **News panel** (`features/news/NewsPanel.tsx`): market-wide / active-symbol toggle,
  refresh, article list (title, source · relative time, summary, symbol tags).
  Links open in the OS browser via the existing `setWindowOpenHandler`. Registered
  in `panelRegistry.tsx` (placeholder removed).
- `api.ts` + `contracts.ts` gained news endpoints/types; `formatRelativeTime` added
  to `lib/format.ts`.

**Verified**: engine `pytest` (39) + `ruff check app` clean; desktop typecheck +
build pass; live smoke test — real CNBC headlines fetched/parsed/stored, dedup
confirmed (second refresh stored 0), migration chain applies.

### Session 2026-06-28 — Phase 4 (Watchlists & Portfolio) complete

**Added — Engine**
- **DB**: `WatchlistRow`, `WatchlistItemRow` (FK `ON DELETE CASCADE` + unique
  `(watchlist_id, symbol)`), `HoldingRow` in `app/db/models.py`. Alembic migration
  `8c2159eb5303` (autogenerated; upgrade/downgrade round-trip verified).
- **Watchlists** (`app/watchlists/`): `WatchlistService` (list/create/rename/delete,
  add/remove/reorder items, `ensure_default` seeds a 7-symbol starter list) +
  schemas. Routes under `/api/v1/watchlists` (CRUD + `/items` add/remove/reorder).
- **Portfolio** (`app/portfolio/`): `PortfolioService` (holdings CRUD) + pure P&L
  functions `position_from`/`summarize` (per-currency totals, no FX conversion) +
  schemas. Routes `GET /api/v1/portfolio` (joins holdings with live quotes fetched
  concurrently via `asyncio.gather`), `GET/POST/PUT/DELETE /api/v1/holdings[/{id}]`.
- **Wiring**: `deps.py` + `main.py` construct both services on startup (default
  watchlist seeded) and register the routers.
- **Tests**: `test_portfolio.py` (4, pure P&L), `test_watchlists_api.py` (1, full
  CRUD), `test_portfolio_api.py` (1, CRUD + summary with a fake adapter). **35 total.**

**Added — Renderer**
- **Watchlist store rewired** to be API-backed with multiple lists
  (`store/useWatchlistStore.ts`), preserving the existing surface
  (`symbols`/`activeSymbol`/`setActive`/`add`/`remove`) so the stream, seeder,
  chart and quote panels keep working; mutations are optimistic + reconciled.
  New `hooks/useWatchlistBootstrap.ts` loads lists when the engine is ready.
- **Watchlists panel** (`features/watchlists/WatchlistsPanel.tsx`): create/rename/
  delete lists, switch active, add/remove/reorder symbols with live quotes.
- **Portfolio panel** (`features/portfolio/{PortfolioPanel,HoldingForm}.tsx`): live
  P&L table (15s refresh), per-currency totals, add/edit/delete holdings via a modal.
- Both registered in `panelRegistry.tsx` (placeholders removed); `api.ts` +
  `contracts.ts` gained watchlist/portfolio endpoints and types; added an `.input`
  form-control utility to `styles/index.css`.

**Verified**: engine `pytest` (35) + `ruff check app` clean; desktop typecheck +
build pass; live smoke test (uvicorn) — migrations apply, default watchlist seeds,
holdings CRUD works, `/portfolio` returns live P&L from a real quote.

### Session 2026-06-28 — Phase 3 (Charts) completed

Finished the three remaining Phase 3 items: oscillator sub-panes, Volume Profile,
and drawing tools. Phase 3 is now complete.

**Added — Engine**
- `app/technical/volume_profile.py` — `compute_volume_profile()` buckets the
  candle price range into N levels, distributing each candle's volume across the
  levels its low–high spans; flags the Point of Control (highest-volume level).
  Returns `VolumeProfileResponse` (bins + poc + max_volume).
- Route `GET /api/v1/volume-profile/{symbol}?bins=&interval=&range=` (CPU work
  offloaded via `asyncio.to_thread`).
- Tests: `test_volume_profile.py` (5: empty, span, conservation, POC, flat range)
  + `test_volume_profile_api.py` (1, offline fake-adapter HTTP path). **29 total.**

**Added — Renderer (`features/charts/`)**
- **Oscillator sub-panes**: `OscillatorPane.tsx` renders RSI, MACD (line+signal+
  histogram), Stochastic (%K/%D) and ATR — each in its own `lightweight-charts`
  instance below the price chart, with overbought/oversold guide lines. v4 has no
  native multi-pane, so `chartSync.ts` (`ChartSync`) mirrors the visible logical
  range across the price chart + all panes (re-entrancy-guarded). The bottom-most
  pane owns the shared time axis; price-scale widths aligned via `minimumWidth`.
- **Volume Profile**: `VolumeProfileOverlay.tsx` — an SVG overlay anchored to the
  price axis via `priceToCoordinate`, re-projected on pan/zoom/resize, POC bar
  highlighted. Toggle in the Indicators dropdown.
- **Drawing tools**: `DrawingCanvas.tsx` + `drawings.ts` — trend lines, horizontal
  support/resistance, and Fibonacci retracement (0/23.6/38.2/50/61.8/78.6/100%).
  Points stored in chart (time, price) coordinates so drawings stick to the data
  through pan/zoom; kept per symbol; Escape cancels; toolbar with a clear button.
- **Indicators dropdown** reorganized into **Overlays / Oscillators / Volume**
  groups; `toOscillatorHistogram` added to `chartData.ts`; `contracts.ts` +
  `api.ts` gained `VolumeProfile*` types and `getVolumeProfile`.

**Verified**: engine `pytest` (29) + `ruff check app` clean; desktop typecheck +
build pass.

### Session 2026-06-28 — UX fixes (navigation + panel recovery)

User testing surfaced three blocking UI/UX issues; fixed without deferring to later phases.

**Added**
- **Workspace panel registry** (`renderer/src/features/workspace/panelRegistry.tsx`):
  single source of truth for all dockview panels (real feature panels + "under
  construction" placeholders for future phases), the shared `Placeholder` component,
  `addRegisteredPanel`, and `buildDefaultLayout`.
- **Workspace store** (`renderer/src/store/useWorkspaceStore.ts`): publishes the live
  `DockviewApi` and tracks open panel ids; actions `openPanel`/`openDashboard`/
  `resetLayout`/`syncOpen` consumed by the Sidebar and the new Panels menu.
- **Panels menu** (`renderer/src/components/PanelsMenu.tsx`) in the TitleBar: reopen/
  focus any panel (closed ones included, with a check mark for open ones) plus a
  **Reset Layout** action.
- **Empty-state recovery**: when every dockview panel is closed, the Workspace shows a
  centered overlay with a **Reset Layout** button so the app can never get stuck blank.
- **AI Analysis modal** in `DetailPanel`: clicking the (previously disabled) button now
  opens a popup — "AI Analysis Engine is loading… (Available in Phase 6)".

**Changed/Fixed**
- **Sidebar nav buttons are no longer disabled/dead.** Every item (Watchlists,
  Portfolio, News, AI, Alerts, Settings) is clickable and opens either its module
  placeholder panel or, for Dashboard, restores the default layout.
- **CRITICAL: closed Dockview panels are now recoverable** (Chart/Quote/Watchlist) via
  the Panels menu and the empty-state Reset button — previously there was no way to
  reopen them and closing all panels left the app blank/unusable.
- `Workspace.onReady` now publishes the api to the store, subscribes to add/remove
  events to keep `openIds` in sync, and guards `buildDefaultLayout` against
  StrictMode double-ready.

**Verified**: desktop `npm run typecheck` + `npm run build` pass.

### Session 2026-06-27 — Phase 3 (Charts, in progress)

#### Phase 3 — Charts (partial: chart panel + indicators landed)
**Added**
- **Engine `app/technical/`** package (provider-agnostic, reusable by alerts/AI):
  - `resample.py` — `resample_candles()` aggregates finer OHLCV bars into coarser
    ones (open=first/high=max/low=min/close=last/volume=sum), left-labelled.
  - `indicators.py` — full suite over pandas: SMA, EMA, RSI (Wilder), MACD,
    Bollinger Bands, VWAP (cumulative), Stochastic, ATR (Wilder), Ichimoku.
    `compute_indicators()` parses a compact spec (`"sma:20,ema:50,macd,bbands:20:2"`)
    into render-ready `IndicatorSeries` with a `pane` hint (price/rsi/macd/stoch/atr)
    and NaN→null cleaning for JSON safety.
- **4h history**: `MarketDataService.get_history` now synthesizes 4h candles by
  fetching 1h bars and resampling (yfinance has no native 4h interval).
- **Route**: `GET /api/v1/indicators/{symbol}?indicators=&interval=&range=`
  (pandas work offloaded via `asyncio.to_thread`).
- **Renderer charts** (`features/charts/`):
  - `ChartPanel.tsx` — TradingView-style `lightweight-charts` (v4) panel wired to
    `GET /api/v1/history`, driven by the active symbol. Volume histogram overlay.
  - Timeframe selector (1m/5m/15m/1h/4h/1D/1W/1M, each mapped to a sensible
    interval+range respecting yfinance limits).
  - Chart types: candlestick, Heikin-Ashi, line, area.
  - Indicators dropdown toggling price-pane overlays (SMA 20/50, EMA 20/50,
    Bollinger, VWAP), fetched from the indicators endpoint and drawn on the price scale.
  - `chartData.ts` — pure candle→series transforms (candles, Heikin-Ashi, line,
    overlay lines, volume) with ascending/unique-timestamp normalization.
- **Workspace**: registered the **Chart** dockview panel (main area; Quote docked
  below, Watchlist to the left).
- **Tests**: `test_resample.py` (3), `test_indicators.py` (6), `test_indicators_api.py`
  (1, full HTTP + JSON-safety). Total **23 passing**; ruff clean; typecheck + build pass.

**Remaining in Phase 3** (next session): oscillator sub-panes (RSI/MACD/Stochastic/ATR
rendering — needs a synced secondary chart in lightweight-charts v4), Volume Profile,
and drawing tools (trend lines, support/resistance, Fibonacci).

### Session 2026-06-27 — Phases 1 & 2

#### Phase 2 — Market Data (complete)
**Added**
- **Persistence**: synchronous SQLAlchemy 2.0 over SQLite (WAL mode); `app/db/`
  (`base.py` with a UTC-aware `UTCDateTime` type, `models.py`, `session.py`,
  `repositories.py`). `init_db()` applies migrations on startup.
- **Alembic**: `alembic.ini`, `alembic/env.py` (renders `UTCDateTime` as
  `sa.DateTime` for portable migrations), initial migration `9518455a983e`
  creating `settings`, `secrets`, `symbols`, `quotes_cache`.
- **Symbol universe** (`app/data/universe/`): US loader from official NASDAQ
  Trader files (`nasdaqlisted.txt` + `otherlisted.txt`), BIST from bundled
  `bist_seed.json` (~113 names). `SymbolUniverseService` (refresh / ensure_seeded
  / search / stats). Seeds **12,610 symbols** on first run.
- **Routes**: `GET /api/v1/symbols/stats`, `POST /api/v1/symbols/refresh`,
  `GET/PUT /api/v1/settings[/{key}]`, `GET/PUT /api/v1/providers/order`,
  `GET/PUT/DELETE /api/v1/secrets[/{provider}]`.
- **Settings/secrets** (`app/settings/`): `SettingsService` (JSON KV),
  `SecretsService` (Fernet-encrypted provider keys, write-only API),
  provider-order config, known data + AI provider registry.
- **Providers**: `FinnhubAdapter` (US equities; returns None for BIST/history).
  `factory.py` builds the `MarketDataService` chain from provider order + secrets.
- **Quote persistence**: `SqliteQuoteStore` write-through cache + stale fallback
  when all providers fail.
- **Frontend**: `UniverseBadge` (title-bar symbol count + one-click refresh);
  `api.ts` universe endpoints.
- **Tests**: `test_settings.py`, `test_universe.py`, `test_quote_persistence.py`,
  `conftest.py` (isolated temp DB + no-network seeding). Total **13 passing**.

**Changed**
- `/api/v1/search` now queries the local universe first (ranked exact > prefix >
  name), falling back to live provider search and merging deduped results.
- `MarketDataService` accepts an optional `QuoteStore` for persistence.
- `app/main.py` lifespan wires DB init, settings/secrets, universe seeding, and
  the configured provider chain; registers the new routers; closes provider
  HTTP clients on shutdown.
- `config.py`: added `auto_seed` flag and `data_dir` env override.
- Enums converted to `StrEnum`; `datetime.UTC` adopted; ruff clean.

#### Phase 1 — Foundation (complete)
**Added**
- Monorepo (npm workspaces) + dev orchestrator (`scripts/dev.mjs`,
  `scripts/engine.mjs`) + docs (`docs/ARCHITECTURE.md`, `ROADMAP.md`, `HANDOFF.md`).
- **Engine**: FastAPI app factory + lifespan, config, logging, async TTL cache,
  Fernet+keyring secret box, `MarketDataAdapter` protocol, `YFinanceAdapter`,
  `MarketDataService` (fallback + cache), REST routes + `WS /ws/stream`.
- **Desktop** (electron-vite): main process spawning/supervising the Python
  engine, preload `window.borsa` bridge, React renderer with a dark
  Bloomberg-style theme (Tailwind), dockview workspace, Zustand stores
  (engine/quotes/watchlist), reconnecting WS client, REST client, TanStack Query
  search, Sidebar/TitleBar/SearchBar/StatusBadge, WatchPanel + DetailPanel.
- `scripts/fix-electron.mjs` postinstall to work around the Windows electron
  extract-zip bug.

**Verified**
- End-to-end: `npm run dev` launches the engine + Electron window; live quotes
  render for AAPL (NASDAQ/USD) and ASELS.IS (BIST/TRY). Typecheck + build pass.

**Known issues**
- BIST universe is a curated seed (full listing pending KAP scraper).
- Finnhub adapter not yet verified against a live key.
- yfinance data is delayed (~15 min) and best-effort.
