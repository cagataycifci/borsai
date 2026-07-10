# CONTINUE.md — Borsa AI Terminal

> Single source of truth for resuming work in a new Claude Code session.
> Last updated: **Phase 7 (Alerts & Notifications) COMPLETE** — pure alert engine +
> `AlertMonitor` broadcast over WS + native notifications + Alerts panel.
> Next: **Phase 8 (Scheduler & Reports)**.
> Date: 2026-06-29.

---

## 1. Overall project goal
A production-quality, AI-powered **desktop market terminal** ("personal Bloomberg
Terminal") that monitors **Borsa Istanbul (BIST)** and **US markets (NYSE /
NASDAQ / AMEX)**. Modular, fast, beautiful (dark, TradingView/Bloomberg-style),
maintainable. Real-time-ish quotes, charts, news, AI analysis, portfolio,
alerts, scheduler, AI chat. Build as if commercially sold. **Not financial advice.**

---

## 2. Current architecture
Two processes that talk over **localhost HTTP + WebSocket**:

```
Electron Desktop (apps/desktop)                 Python Engine (services/engine)
  main  ── spawns/supervises ─────────────────►  FastAPI + asyncio (127.0.0.1:8787)
  preload (contextBridge: window.borsa)            ├─ api/      REST routers + WS hub
  renderer (React + Vite)  ── HTTP/WS ──────────►  ├─ data/     adapters + service + universe
                                                   ├─ settings/ settings + encrypted secrets
                                                   ├─ db/       SQLAlchemy + repos (SQLite)
                                                   ├─ core/     config, logging, cache, security
                                                   └─ alembic/  migrations (schema source of truth)
```

- The Electron **main** process owns OS integration + spawns the Python engine
  (in dev it reuses an already-running engine via `/health` probe).
- The **engine** holds ALL finance/data/AI logic. UI never does data work directly.
- **Decision: the engine DB layer is SYNCHRONOUS** SQLAlchemy (not async). Robust
  for a single-user embedded SQLite DB; FastAPI runs sync route handlers in a
  threadpool. Async stays only in the data/provider/HTTP layer.

---

## 3. Folder structure (key files)
```
borsa/
├─ package.json                 # npm workspace root; scripts: dev, dev:engine, dev:desktop
├─ scripts/
│  ├─ dev.mjs                   # boots engine + electron-vite together
│  ├─ engine.mjs                # runs uvicorn from venv
│  └─ fix-electron.mjs          # postinstall: works around electron extract-zip bug
├─ docs/{ARCHITECTURE,ROADMAP,HANDOFF}.md
├─ CONTINUE.md PROJECT_STATUS.md TASKS.md CHANGELOG.md   # (this handoff)
│
├─ apps/desktop/                # Electron + React (TypeScript, electron-vite)
│  ├─ electron.vite.config.ts  tailwind.config.mjs  postcss.config.mjs
│  ├─ tsconfig.{json,web,node}.json
│  └─ src/
│     ├─ main/index.ts                 # window + IPC + engine lifecycle
│     ├─ main/engine/manager.ts        # spawn/supervise/health-probe engine
│     ├─ preload/index.ts(+.d.ts)      # window.borsa bridge
│     └─ renderer/src/
│        ├─ app/{App,TitleBar,Sidebar,Workspace}.tsx
│        ├─ components/{SearchBar,StatusBadge,UniverseBadge,ExchangeBadge,PanelsMenu}.tsx
│        ├─ features/dashboard/{WatchPanel,DetailPanel}.tsx
│        ├─ features/charts/{ChartPanel,OscillatorPane,VolumeProfileOverlay,
│        │                   DrawingCanvas}.tsx + {chartData,chartSync,drawings}.ts  # Phase 3
│        ├─ features/workspace/panelRegistry.tsx            # dockview panel registry
│        ├─ features/watchlists/WatchlistsPanel.tsx         # Phase 4
│        ├─ features/portfolio/{PortfolioPanel,HoldingForm}.tsx  # Phase 4
│        ├─ features/news/NewsPanel.tsx                     # Phase 5
│        ├─ features/ai/AiPanel.tsx                         # Phase 6
│        ├─ features/settings/SettingsPanel.tsx             # Phase 6
│        ├─ hooks/{useEngineBootstrap,useMarketStream,useQuoteSeeder,useWatchlistBootstrap}.ts
│        ├─ lib/{api,ws,contracts,format,cn}.ts
│        ├─ store/{useEngineStore,useQuotesStore,useWatchlistStore,useWorkspaceStore}.ts
│        └─ styles/index.css
│
└─ services/engine/             # Python FastAPI engine
   ├─ pyproject.toml  alembic.ini
   ├─ alembic/{env.py, versions/9518455a983e_initial_schema.py}
   ├─ tests/{conftest,test_cache,test_health,test_settings,test_universe,
   │         test_quote_persistence,test_resample,test_indicators,test_indicators_api}.py
   └─ app/
      ├─ main.py                         # app factory + lifespan (wires everything)
      ├─ core/{config,logging,cache,security}.py
      ├─ db/{base,models,session,repositories}.py
      ├─ data/{base,models,service,factory,quote_store}.py
      ├─ data/providers/{yfinance_adapter,finnhub_adapter}.py
      ├─ data/universe/{loaders,service,bist_seed.json}.py
      ├─ technical/{resample,indicators,volume_profile}.py   # Phase 3
      ├─ settings/{service,schemas}.py
      ├─ watchlists/{service,schemas}.py                      # Phase 4
      ├─ portfolio/{service,schemas}.py                       # Phase 4
      ├─ news/{parser,sources,service,schemas}.py             # Phase 5
      ├─ ai/{base,factory,prompts,service,schemas}.py          # Phase 6
      ├─ ai/providers/{anthropic,openai,gemini,ollama}_adapter.py  # Phase 6
      └─ api/{deps,routes,symbol_routes,settings_routes,
              watchlist_routes,portfolio_routes,news_routes,ai_routes,ws}.py
```

---

## 4. Tech stack
- **Desktop**: Electron 33, React 18, TypeScript 5.6, Vite 5 (electron-vite 2),
  Tailwind 3, Zustand 5, TanStack Query 5, dockview 4 (dockable panels),
  lightweight-charts 4 (installed, used in Phase 3), lucide-react, clsx, tailwind-merge.
- **Engine**: Python 3.12, FastAPI, uvicorn[standard], Pydantic 2, pydantic-settings,
  httpx, yfinance, pandas, SQLAlchemy 2.0, Alembic, cryptography (Fernet), keyring.
- **DB**: SQLite (WAL) at `%APPDATA%/BorsaAI/borsa.db`.

---

## 5. Installed dependencies
**Root** (`package.json`): devDeps `concurrently`. Scripts include a `postinstall`
→ `scripts/fix-electron.mjs`.

**apps/desktop** deps: `@tanstack/react-query, clsx, dockview, lightweight-charts,
lucide-react, react, react-dom, tailwind-merge, zustand`. devDeps: `@types/node,
@types/react, @types/react-dom, @vitejs/plugin-react, autoprefixer, electron,
electron-vite, postcss, tailwindcss, typescript, vite`.

**services/engine** (`pyproject.toml`) deps: `fastapi, uvicorn[standard], pydantic,
pydantic-settings, httpx, yfinance, pandas, sqlalchemy, alembic, cryptography,
keyring, python-dotenv, anthropic` (Phase 6 — reference AI provider). `[dev]`:
`pytest, pytest-asyncio, ruff, mypy`. Installed editable: `pip install -e ".[dev]"`
into `services/engine/.venv`. OpenAI/Gemini SDKs are optional (lazy-imported) —
install `openai` / `google-generativeai` only if you switch to those providers.

---

## 6. Environment variables (prefix `BORSA_`, optional `.env` — see `.env.example`)
| Var | Default | Purpose |
|---|---|---|
| `BORSA_ENGINE_HOST` | `127.0.0.1` | engine bind host (loopback only) |
| `BORSA_ENGINE_PORT` | `8787` | engine port |
| `BORSA_LOG_LEVEL` | `INFO` | log level |
| `BORSA_ENVIRONMENT` | `development` | env name |
| `BORSA_AUTO_SEED` | `true` | seed symbol universe on first run (tests set `false`) |
| `BORSA_DATA_DIR` | per-OS appdata | DB/log location (tests override to tmp) |
| `FINNHUB_API_KEY` | — | optional; keys normally entered in Settings (encrypted) |
| `ELECTRON_RENDERER_URL` | set by electron-vite | dev renderer URL |

Secrets (API keys) are **not** stored in env in normal use — they go through the
encrypted secrets store. Master Fernet key lives in the OS keychain (keyring),
falling back to `data_dir/.master.key` (0600).

---

## 7. API providers (data)
- **yfinance** (free, ~15-min delayed): US + BIST (`.IS` suffix). Quotes, search,
  history, fundamentals. Primary fallback; only BIST source.
- **Finnhub** (free tier, needs key): US equities only (near-real-time quotes,
  profile, metrics). Returns `None` for BIST/history → falls through to yfinance.
- **NASDAQ Trader** symbol directory files (free, no key): the US symbol universe.
- Adapter abstraction (`app/data/base.py::MarketDataAdapter`) makes paid/real-time
  providers (Polygon, a BIST vendor) **drop-in** later — just prepend to the chain.

## 8. AI providers (Phase 6 — implemented)
- **`app/ai/` package** mirrors `app/data`: an `AIProvider` protocol (`complete` +
  `stream`) with adapters for `anthropic` (reference/default, official SDK, model
  `claude-opus-4-8`), `openai`, `gemini`, `ollama` (local, keyless). Provider SDKs
  are **imported lazily** — only the active provider's dependency must be installed
  (`anthropic` is a hard dep; OpenAI/Gemini are optional).
- `app/ai/factory.py::build_ai_provider()` builds the active provider from the
  `ai.active_provider` setting + the encrypted secrets store (returns `None` when a
  required key is missing). The provider is rebuilt **per request**, so a key added
  in Settings takes effect without an engine restart.
- `AIService` (`app/ai/service.py`) assembles a context bundle (quote + key
  indicators from `app/technical` + recent `app/news`) and prompts the model:
  `analyze` (structured `AnalysisReport`, persisted), `chat_stream` (SSE), and
  `classify_news` (bullish/bearish/neutral + importance + why). JSON parsing is
  lenient (tolerates fences/prose).

---

## 9. Database schema (SQLite, via Alembic — rev `9518455a983e`)
- **settings**(`key` PK str, `value` JSON, `updated_at`)
- **secrets**(`provider` PK str, `ciphertext` str [Fernet], `created_at`, `updated_at`)
- **symbols**(`symbol` PK, `display_symbol` idx, `name`, `exchange` idx,
  `asset_type`, `currency`, `sector`, `industry`, `source`, `updated_at`;
  composite idx `(display_symbol, exchange)`)
- **quotes_cache**(`symbol` PK, `payload` JSON [serialized Quote], `fetched_at`)
- **watchlists**(`id` PK, `name`, `position`, `created_at`, `updated_at`) — Phase 4
- **watchlist_items**(`id` PK, `watchlist_id` FK→watchlists ON DELETE CASCADE idx,
  `symbol`, `position`, `created_at`; unique `(watchlist_id, symbol)`) — Phase 4
- **holdings**(`id` PK, `symbol` idx, `quantity`, `avg_cost`, `currency`,
  `purchase_date?`, `target_price?`, `stop_loss?`, `notes?`, `created_at`,
  `updated_at`) — Phase 4
- **news**(`id` PK, `source`, `title`, `url` unique idx [dedup key], `summary?`,
  `symbols` JSON, `published_at?` idx, `fetched_at`) — Phase 5
- **ai_reports**(`id` PK, `symbol` idx, `provider`, `model`, `sentiment`,
  `payload` JSON [serialized AnalysisReport], `created_at` idx) — Phase 6
- **alerts**(`id` PK, `symbol` idx, `type`, `threshold?`, `params?` JSON, `active`,
  `cooldown_seconds`, `note?`, `last_triggered_at?`, `created_at`, `updated_at`) — Phase 7
- **alert_events**(`id` PK, `alert_id?` FK→alerts ON DELETE SET NULL idx, `symbol` idx,
  `type`, `message`, `price?`, `created_at` idx) — Phase 7
- **alembic_version**(`version_num`) — head is `b7e3a1c92d55`

All tables through Phase 7 exist. (Phase 8 adds no new tables unless a reports
cache is introduced.)

---

## 10. Features completed
**Phase 1 — Foundation** ✅
- Monorepo + dev orchestrator; Electron shell (dark Bloomberg theme, dockview
  workspace, custom title bar, sidebar); engine auto-spawn/supervise; preload
  bridge; Zustand stores; reconnecting WS client; REST client; live quote
  dashboard (WatchPanel + DetailPanel) for US + BIST.

**Phase 2 — Market Data** ✅
- SQLite + SQLAlchemy 2.0 + Alembic (`init_db` runs migrations on startup).
- Symbol universe: **12,610 symbols** (US live from NASDAQ Trader, BIST from
  bundled seed). DB-backed ranked search (`/api/v1/search`) with provider fallback.
- Finnhub adapter (US) + provider factory building the chain from config + secrets.
- Settings service (JSON KV) + Secrets service (Fernet-encrypted, write-only API).
- Write-through quote persistence (`quotes_cache`) with stale-fallback.
- `UniverseBadge` UI (symbol count + refresh).
- 13 pytest tests pass; ruff clean; desktop typecheck + build pass.

**Phase 3 — Charts ✅ (complete)**
- Engine `app/technical/`: `resample.py` (`resample_candles`) + `indicators.py`
  (SMA, EMA, RSI, MACD, Bollinger, VWAP, Stochastic, ATR, Ichimoku) with a
  spec-parsing `compute_indicators()` returning JSON-safe `IndicatorSeries`
  (NaN→null) tagged with a render `pane` hint. + `volume_profile.py`
  (`compute_volume_profile`: volume-by-price bins + POC).
- `MarketDataService.get_history` synthesizes **4h** candles (fetch 1h → resample).
- Routes `GET /api/v1/indicators/{symbol}` and `GET /api/v1/volume-profile/{symbol}`
  (pandas/CPU offloaded to a thread).
- Renderer `features/charts/`: `ChartPanel.tsx` (lightweight-charts v4) registered
  as the **Chart** dockview panel; timeframe selector (1m→1M), chart types
  (candlestick/Heikin-Ashi/line/area), volume histogram, and an **Indicators**
  dropdown (Overlays / Oscillators / Volume groups).
  - **Overlays**: SMA 20/50, EMA 20/50, Bollinger, VWAP (price-pane lines).
  - **Oscillators**: RSI/MACD/Stochastic/ATR in synced secondary charts
    (`OscillatorPane.tsx` + `chartSync.ts` mirror the visible logical range; v4 has
    no native multi-pane). Bottom pane owns the time axis; `minimumWidth` aligns
    price-scale widths.
  - **Volume Profile**: `VolumeProfileOverlay.tsx` SVG anchored to the price axis
    via `priceToCoordinate`, POC highlighted.
  - **Drawing tools**: `DrawingCanvas.tsx` + `drawings.ts` — trend / horizontal /
    Fibonacci, stored in (time, price) coords per symbol; toolbar + clear; Esc cancels.
- 29 pytest tests pass; ruff clean (app); desktop typecheck + build pass.

**Phase 4 — Watchlists & Portfolio ✅ (complete)**
- DB: `watchlists`, `watchlist_items` (FK cascade + unique `(watchlist_id, symbol)`),
  `holdings` (migration `8c2159eb5303`).
- Engine `app/watchlists/` + `app/portfolio/`: services (direct `session_scope`
  style), schemas, routes. Pure P&L math (`position_from`/`summarize`) is unit-tested.
  A starter watchlist is seeded on first run (`ensure_default`).
- Renderer: API-backed `useWatchlistStore` (multiple lists; old surface preserved),
  `useWatchlistBootstrap` loads on engine-ready, `WatchlistsPanel` (CRUD + reorder),
  `PortfolioPanel` + `HoldingForm` (live P&L table, per-currency totals). Both panels
  registered in `panelRegistry.tsx` (placeholders removed).
- 35 pytest tests pass; ruff clean (app); typecheck + build pass; live smoke test green.

**Phase 5 — News Layer ✅ (complete)**
- Engine `app/news/`: provider-agnostic `NewsSource` shape, a pure RSS 2.0/Atom
  `parser.py` (namespace-agnostic, RFC-822 + ISO dates, HTML-stripped, unit-tested),
  `sources.py` (Yahoo Finance/CNBC/MarketWatch RSS + Yahoo per-symbol), and
  `NewsService` (concurrent fan-out, url-dedup, persist).
- DB: `news` table (`url` unique = dedup; `published_at` indexed; migration `f2b025ee9893`).
- Routes: `GET /api/v1/news` (auto-refresh once when empty), `POST /api/v1/news/refresh`,
  `GET /api/v1/news/{symbol}` (live fetch + store, DB fallback).
- Renderer: `features/news/NewsPanel.tsx` (market/symbol toggle, refresh, external
  links via the main-process `setWindowOpenHandler`); registered in `panelRegistry.tsx`.
- 39 pytest tests pass; ruff clean (app); typecheck + build pass; live smoke test
  (real CNBC headlines fetched + deduped). **KAP/SEC sources deferred (additive).**

**Phase 6 — AI Layer ✅ (complete)**
- Engine `app/ai/`: provider-agnostic `AIProvider` protocol (`complete` + `stream`)
  + adapters Anthropic (reference, `claude-opus-4-8`)/OpenAI/Gemini/Ollama (lazy
  SDKs) + `factory.py` (active provider from `ai.active_provider` + encrypted
  secrets). `AIService` assembles quote + key indicators + recent news into a
  structured `AnalysisReport`, streams chat (SSE), and classifies news.
- DB: `ai_reports` table (migration `c4d2e1f0a9b8`); reports persisted on analyze.
- Routes: `GET /ai/status`, `PUT /ai/provider`, `POST /ai/analyze`,
  `GET /ai/reports/{symbol}`, `POST /ai/classify`, `POST /ai/chat` (SSE).
- Renderer `features/ai/AiPanel.tsx` (Report + Chat tabs, streaming) +
  `features/settings/SettingsPanel.tsx` (provider select + write-only API keys);
  the DetailPanel "AI Analysis" button opens the AI panel; both registered in
  `panelRegistry.tsx` (placeholders removed). `lib/api.ts` gained AI/secrets
  endpoints + a `streamChat()` SSE helper.
- 42 pytest tests pass (fake provider, no live key); ruff clean (app); typecheck +
  build pass; live smoke test (status, no-key 503, provider switch). **A live model
  call is unverified pending an API key.**

**Phase 7 — Alerts & Notifications ✅ (complete)**
- Engine `app/alerts/`: a **pure** `engine.py` (`Snapshot`/`Indicators` + `evaluate`)
  covering price above/below, % up/down, volume-above, RSI above/below, MACD signal
  cross (up/down), golden/death SMA cross; `build_indicators()` derives scalars from
  candles via `app/technical`. `AlertService` (CRUD + `active_grouped` + event feed,
  `session_scope` style). `AlertMonitor` + `ConnectionHub` (`monitor.py`): a 15s
  background loop (started in lifespan) broadcasts fired alerts over the WS hub,
  respecting per-alert cooldown; quote fetched once/symbol, indicators only when a
  technical alert needs them.
- DB: `alerts` + `alert_events` (migration `b7e3a1c92d55`).
- Routes: `GET/POST /api/v1/alerts`, `PUT/DELETE /api/v1/alerts/{id}`,
  `GET /api/v1/alerts/events`. WS frame set gains `{"type":"alert","data":<AlertEvent>}`;
  each `/ws/stream` client registers with `app.state.ws_hub`.
- Renderer `features/alerts/AlertsPanel.tsx` (CRUD + On/Off + live triggered feed) +
  `store/useAlertsStore.ts`; `useMarketStream` routes `alert` frames → store + native
  `window.borsa.notify`. Portfolio panel gained an auto-refreshing (60s) "news on your
  holdings" section. Alerts panel registered in `panelRegistry.tsx` (placeholder gone).
- 47 pytest tests pass; ruff clean (app); typecheck + build pass; live smoke test
  (CRUD over HTTP, 400 validation, events feed, migration chain). Monitor firing +
  cooldown covered by a fake-market unit test.

### Engine endpoints live now
`GET /health` · `GET /api/v1/search?q=&limit=` · `GET /api/v1/quote/{symbol}` ·
`GET /api/v1/history/{symbol}?interval=&range=` (4h synthesized via resample) ·
`GET /api/v1/indicators/{symbol}?indicators=&interval=&range=` (Phase 3) ·
`GET /api/v1/volume-profile/{symbol}?bins=&interval=&range=` (Phase 3) ·
`GET /api/v1/fundamentals/{symbol}` ·
`GET /api/v1/symbols/stats` · `POST /api/v1/symbols/refresh` ·
`GET/PUT /api/v1/settings[/{key}]` · `GET/PUT /api/v1/providers/order` ·
`GET/PUT/DELETE /api/v1/secrets[/{provider}]` ·
**Phase 4** `GET/POST /api/v1/watchlists` · `PUT/DELETE /api/v1/watchlists/{id}` ·
`POST/DELETE /api/v1/watchlists/{id}/items[/{symbol}]` · `PUT /api/v1/watchlists/{id}/items`
(reorder) · `GET /api/v1/portfolio` · `GET/POST /api/v1/holdings` ·
`PUT/DELETE /api/v1/holdings/{id}` ·
**Phase 5** `GET /api/v1/news` · `POST /api/v1/news/refresh` ·
`GET /api/v1/news/{symbol}` ·
**Phase 6** `GET /api/v1/ai/status` · `PUT /api/v1/ai/provider` ·
`POST /api/v1/ai/analyze` · `GET /api/v1/ai/reports/{symbol}` ·
`POST /api/v1/ai/classify` · `POST /api/v1/ai/chat` (SSE) · `WS /ws/stream`.

---

## 11. Features in progress
**None.** Phases 1–6 are complete. Next up is Phase 7 (not yet started).

## 12. Features remaining (Phases 7–10)
7. **Alerts & Notifications** — alert engine, desktop notifications, auto-refresh portfolio page.
8. **Scheduler & Daily Reports** — morning market summary, background workers.
9. **Commentator/Sentiment + Search** — consensus analysis, global search.
10. **Hardening** — tests, packaging (PyInstaller + electron-builder), perf, docs.

---

## 13. Current blockers
**None.** App builds and runs; engine + desktop verified end-to-end.

## 14. Known bugs / gotchas
- **Electron extract-zip bug (Windows)**: a clean `npm install` may leave
  `node_modules/electron` without `dist/electron.exe` ("Error: Electron uninstall").
  Worked around by `scripts/fix-electron.mjs` (postinstall) which extracts the
  cached zip manually and writes `path.txt`. If it recurs, run `npm run fix:electron`.
- **Finnhub adapter untested with a live key** (no key on dev machine). Logic is
  covered by provider-chain + fake-adapter tests; verify once a key is added.
- **BIST universe is a curated seed (~113 names)**, not the full listing. Full list
  needs a KAP scraper (`app/data/universe/loaders.py` → add `load_bist_full`).
- yfinance is delayed (~15 min) and occasionally flaky; treated as best-effort
  with cache + stale fallback. `.info` is wrapped in try/except.
- One harmless warning remains in tests: Starlette TestClient httpx deprecation.

---

## 15b. UX fixes — Session 2026-06-28 (post Phase 3)
Three blocking UI issues from user testing were fixed (see CHANGELOG):
- **Workspace panels are now registry-driven.** Do NOT add panels directly in
  `Workspace.tsx` anymore — register them in
  `renderer/src/features/workspace/panelRegistry.tsx` (`PANELS` + `components`).
  The live `DockviewApi` and open-panel state live in
  `renderer/src/store/useWorkspaceStore.ts` (`openPanel`/`openDashboard`/`resetLayout`).
- **Sidebar** items are all clickable; non-built modules open a placeholder panel
  ("under construction — Coming in Phase X"). New panels: `watchlists, portfolio,
  news, ai, alerts, settings` (placeholders) alongside `chart, detail, watch`.
- **TitleBar** has a **Panels** dropdown (`components/PanelsMenu.tsx`) to reopen any
  closed panel + **Reset Layout**; Workspace shows a Reset overlay when all panels close.
- **DetailPanel** "AI Analysis" button now opens a Phase-6 placeholder modal.
  When Phase 6 lands, replace the modal body with the real analysis call.

## 15f. Files created/modified — Phase 6 (Session 2026-06-29)
**Engine (new):** `app/ai/{__init__,base,schemas,factory,prompts,service}.py`,
`app/ai/providers/{__init__,anthropic_adapter,openai_adapter,gemini_adapter,
ollama_adapter}.py`, `app/api/ai_routes.py`,
`alembic/versions/c4d2e1f0a9b8_ai_reports.py`, `tests/test_ai_api.py`.
**Engine (modified):** `app/db/models.py` (AiReportRow), `app/settings/service.py`
(active-AI-provider + model helpers, `KEY_AI_MODEL`, `DEFAULT_AI_PROVIDER`),
`app/api/deps.py` (+`get_ai_service`), `app/main.py` (AIService + router),
`pyproject.toml` (+`anthropic>=0.40`).
**Desktop (new):** `renderer/src/features/ai/AiPanel.tsx`,
`renderer/src/features/settings/SettingsPanel.tsx`.
**Desktop (modified):** `lib/api.ts` (AI + secrets endpoints + `streamChat()` SSE
helper), `lib/contracts.ts` (AI types), `features/workspace/panelRegistry.tsx`
(real AI + Settings panels), `features/dashboard/DetailPanel.tsx` (button opens the
AI panel; placeholder modal removed).
**Docs:** this file, `TASKS.md`, `CHANGELOG.md`, `PROJECT_STATUS.md`.

## 15e. Files created/modified — Phase 5 (Session 2026-06-28)
**Engine (new):** `app/news/{__init__,schemas,parser,sources,service}.py`,
`app/api/news_routes.py`,
`alembic/versions/f2b025ee9893_news.py`,
`tests/{test_news_parser,test_news_api}.py`.
**Engine (modified):** `app/db/models.py` (NewsRow), `app/api/deps.py`
(+news provider), `app/main.py` (NewsService + router).
**Desktop (new):** `renderer/src/features/news/NewsPanel.tsx`.
**Desktop (modified):** `lib/{api.ts,contracts.ts}` (news endpoints + type),
`lib/format.ts` (+formatRelativeTime), `features/workspace/panelRegistry.tsx`
(real News panel).
**Docs:** this file, `TASKS.md`, `CHANGELOG.md`, `PROJECT_STATUS.md`.

## 15d. Files created/modified — Phase 4 (Session 2026-06-28)
**Engine (new):** `app/watchlists/{__init__,schemas,service}.py`,
`app/portfolio/{__init__,schemas,service}.py`,
`app/api/{watchlist_routes,portfolio_routes}.py`,
`alembic/versions/8c2159eb5303_watchlists_and_portfolio.py`,
`tests/{test_portfolio,test_watchlists_api,test_portfolio_api}.py`.
**Engine (modified):** `app/db/models.py` (Watchlist/WatchlistItem/Holding rows),
`app/api/deps.py` (+watchlist/portfolio providers), `app/main.py` (services + routers).
**Desktop (new):** `renderer/src/features/watchlists/WatchlistsPanel.tsx`,
`renderer/src/features/portfolio/{PortfolioPanel,HoldingForm}.tsx`,
`renderer/src/hooks/useWatchlistBootstrap.ts`.
**Desktop (modified):** `store/useWatchlistStore.ts` (API-backed, multi-list),
`lib/{api.ts,contracts.ts}` (watchlist/portfolio endpoints + types),
`features/workspace/panelRegistry.tsx` (real panels), `app/App.tsx` (bootstrap hook),
`styles/index.css` (`.input` utility).
**Docs:** this file, `TASKS.md`, `CHANGELOG.md`, `PROJECT_STATUS.md`.

## 15c. Files created/modified — Phase 3 completion (Session 2026-06-28)
**Engine (new):** `app/technical/volume_profile.py`,
`tests/{test_volume_profile,test_volume_profile_api}.py`.
**Engine (modified):** `app/technical/__init__.py` (export volume profile),
`app/api/routes.py` (+`/volume-profile/{symbol}`).
**Desktop (new):** `renderer/src/features/charts/{OscillatorPane,VolumeProfileOverlay,
DrawingCanvas}.tsx`, `renderer/src/features/charts/{chartSync,drawings}.ts`.
**Desktop (modified):** `renderer/src/features/charts/{ChartPanel.tsx (oscillators +
volume profile + drawing toolbar),chartData.ts (+toOscillatorHistogram)}`,
`renderer/src/lib/{api.ts (+getVolumeProfile),contracts.ts (+VolumeProfile* types)}`.
**Docs:** this file, `TASKS.md`, `CHANGELOG.md`, `PROJECT_STATUS.md`.

## 15a. Files created/modified — Phase 3 partial (earlier session)
**Engine (new):** `app/technical/{__init__,resample,indicators}.py`,
`tests/{test_resample,test_indicators,test_indicators_api}.py`.
**Engine (modified):** `app/data/service.py` (4h resample in `get_history` +
`_fetch_history` helper), `app/data/providers/yfinance_adapter.py` (comment),
`app/api/routes.py` (+`/indicators/{symbol}`, `asyncio` import).
**Desktop (new):** `renderer/src/features/charts/{ChartPanel.tsx,chartData.ts}`.
**Desktop (modified):** `renderer/src/app/Workspace.tsx` (register Chart panel),
`renderer/src/lib/{api.ts (+getIndicators),contracts.ts (+Indicator* types)}`.
**Docs:** this file, `TASKS.md`, `CHANGELOG.md`, `PROJECT_STATUS.md`.

## 15. Files created/modified — Phase 2 (earlier)
**Phase 2 engine (new):** `app/db/{base,models,session,repositories}.py`,
`app/data/{factory,quote_store}.py`, `app/data/providers/finnhub_adapter.py`,
`app/data/universe/{__init__,loaders,service,bist_seed.json}`,
`app/settings/{__init__,service,schemas}.py`,
`app/api/{settings_routes,symbol_routes}.py`,
`alembic.ini`, `alembic/{env.py,script.py.mako,versions/9518455a983e_initial_schema.py}`,
`tests/{conftest,test_settings,test_universe,test_quote_persistence}.py`.
**Phase 2 engine (modified):** `pyproject.toml` (+alembic), `app/core/config.py`
(+auto_seed, data_dir env), `app/data/{base,models,service}.py`, `app/api/{deps,routes}.py`,
`app/main.py` (lifespan wiring), providers (StrEnum/UTC cleanups).
**Phase 2 desktop (new/modified):** `components/UniverseBadge.tsx`, `lib/api.ts`
(+universe endpoints), `app/TitleBar.tsx`.
**Docs:** `docs/{ROADMAP,HANDOFF}.md` updated; this handoff set added.
**Phase 1 files** (created earlier this session) listed in `docs/HANDOFF.md`.

---

## 16. Important implementation decisions
1. **Sync DB layer** (SQLAlchemy 2.0 sync + SQLite WAL). Simpler/robust for a
   single user; FastAPI threadpools sync handlers. Async only in data/HTTP layer.
2. **Alembic is the schema source of truth** from Phase 2. `init_db()` runs
   `alembic upgrade head` on startup. `env.py` renders custom `UTCDateTime` as
   `sa.DateTime` so generated migrations don't import app code.
3. **Adapter abstraction + provider factory**: provider order is config-driven
   (`data.provider_order` setting) and built from encrypted secrets; paid
   providers are additive.
4. **Universe-first search**: `/api/v1/search` queries the local DB (ranked
   exact>prefix>name), falling back to live provider search when results are thin.
5. **Secrets are write-only + encrypted** (Fernet, key in OS keychain). Plaintext
   never crosses IPC or the API.
6. **BIST `.IS` convention**: stored with suffix, displayed bare + exchange badge.
7. **StrEnum** for Exchange/AssetType/Interval/Range (Python 3.11+).
8. **Renderer security**: contextIsolation + sandbox + no nodeIntegration; strict CSP.
9. **(Phase 3) Indicators computed engine-side** in `app/technical/` (pure pandas,
   no pandas-ta dependency) so they're reusable by alerts/AI and unit-tested
   headless. NaN warm-up values are serialized as JSON `null`. Each series carries
   a `pane` hint so the renderer knows price-overlay vs oscillator-pane placement.
10. **(Phase 3) 4h is synthesized** (fetch 1h → `resample_candles`); no provider
    offers native 4h. The helper is generic for any pandas offset rule.
11. **(Phase 3) Charts use lightweight-charts v4** (`addCandlestickSeries` etc.).
    v4 lacks native multi-pane, so oscillators each get a secondary `createChart`
    synced via `chartSync.ts` (`ChartSync` mirrors the visible logical range).
12. **(Phase 3) Volume Profile + drawings are renderer overlays** (SVG positioned
    with `priceToCoordinate`/`timeToCoordinate`), re-projected on pan/zoom/resize.
    The profile is computed engine-side; drawings are client-only and stored per
    symbol in component state (persistence deferred to a later phase).
13. **(UX) Workspace panels are registry-driven** (`features/workspace/panelRegistry.tsx`
    + `store/useWorkspaceStore.ts`). Register new panels there, not in `Workspace.tsx`.
14. **(Phase 4) Watchlist/portfolio services use the direct `session_scope` style**
    (like `SettingsService`), not the repository layer — simplest for CRUD. P&L math
    is pure (`app/portfolio/service.py::position_from`/`summarize`), unit-tested
    without DB/network. Portfolio totals are **per-currency** (no FX conversion —
    there's no FX feed yet). The renderer watchlist store is API-backed but keeps the
    original surface so chart/quote/stream consumers were untouched.
15. **(Phase 5) News parsing is pure + provider-agnostic** (`app/news/parser.py`
    matches on *local* XML tag names → one parser for RSS 2.0 + Atom, unit-tested
    offline). Sources isolate network failures via `asyncio.gather(return_exceptions
    =True)`; dedup is by `url` (unique). Refresh is on-demand (no blocking network at
    startup); `GET /news` auto-refreshes once when the store is empty. News links open
    in the OS browser through the existing `setWindowOpenHandler` (no preload change).
16. **(Phase 6) AI mirrors the data layer** — an `AIProvider` protocol + concrete
    adapters + a config-driven factory. **Anthropic is the reference/default**
    (`claude-opus-4-8`, official SDK, a hard dep); OpenAI/Gemini/Ollama SDKs are
    **lazy-imported** so they're optional. **Thinking is intentionally left off** in
    the adapters — analysis and chat want predictable, low-latency, text-only output,
    so chat streams plain text deltas (not summarized reasoning). The provider is
    **built per request** from settings + secrets, so a key added in Settings works
    without a restart. Analysis output is **structured JSON** parsed leniently
    (tolerates fences/prose) into a typed `AnalysisReport`, persisted to `ai_reports`.
    Chat streams over **SSE** (`text/event-stream`; `data:` tokens, `data: [DONE]`
    terminator, `event: error` frames). Tests use a **fake provider** — no live key.

---

## 17. EXACT next task to continue
**Begin Phase 7 — Alerts & Notifications.** Phases 1–6 are fully DONE. **Do NOT
redo them.** Steps, in order:
1. **DB + service**: an `alerts` table (`AlertRow`: id, symbol, type, condition
   JSON, active, last_triggered_at, notes) + Alembic migration after
   `c4d2e1f0a9b8`. An `app/alerts/` package (service + schemas) in the direct
   `session_scope` style (like `watchlists`/`portfolio`).
2. **Alert engine**: evaluate conditions reusing existing layers — price/%
   thresholds (quotes), RSI/MACD cross + golden/death cross (`app/technical`),
   news/AI-score (`app/ai`). Background evaluation can hook the existing WS poll or
   a simple periodic task (full APScheduler is Phase 8).
3. **Routes**: `GET/POST/PUT/DELETE /api/v1/alerts[/{id}]` + a triggered-events feed;
   push fired alerts over `WS /ws/stream` (extend the frame union).
4. **Desktop notifications**: add a `notify` method to the preload bridge
   (`window.borsa`) backed by an Electron `Notification` in the main process; fire
   it when the renderer receives an alert frame.
5. **Renderer**: a real **Alerts** panel (CRUD + status), replacing the Phase-7
   placeholder in `panelRegistry.tsx`; and an auto-refreshing portfolio view that
   surfaces news affecting owned stocks.

Verify each step: `cd services/engine && .venv/Scripts/python -m pytest &&
.venv/Scripts/python -m ruff check app` · `cd apps/desktop && npm run typecheck &&
npm run build` · then `npm run dev` and exercise the alert flows. Keep the alert
engine unit-tested with pure condition functions (no DB/network).

## 18. EXACT current phase
**Phase 6 (AI Layer) — COMPLETE.** Next: **Phase 7 (Alerts & Notifications)** — not
yet started (see §17).

---

## 19. Recommended prompt for the next Claude Code session
> Continue building the Borsa AI Terminal. Read `CONTINUE.md`, `PROJECT_STATUS.md`,
> `TASKS.md`, and `docs/ARCHITECTURE.md` first. **Phases 1–6 are complete** — do NOT
> redo them. The engine has an AI layer (`app/ai/`: `AIProvider` abstraction over
> Anthropic/OpenAI/Gemini/Ollama, `POST /api/v1/ai/{analyze,chat,classify}`,
> `ai_reports` table) and the renderer has AI + Settings panels, alongside charts,
> watchlists, portfolio and news. **Begin Phase 7 (Alerts & Notifications)** per
> `CONTINUE.md` §17: (1) an `alerts` table + migration after `c4d2e1f0a9b8` and an
> `app/alerts/` service (direct `session_scope` style); (2) an alert engine with pure
> condition functions reusing `app/technical` (RSI/MACD/golden-death cross) and
> `app/ai` (AI score), evaluated off the WS poll; (3) CRUD routes
> `/api/v1/alerts[/{id}]` + push fired alerts over `WS /ws/stream` (extend the frame
> union); (4) native desktop notifications via a new preload `window.borsa.notify`
> backed by an Electron `Notification`; (5) a real Alerts panel (replace the Phase-7
> placeholder in `panelRegistry.tsx`) + auto-refreshing portfolio news. Keep existing
> patterns: sync DB + Alembic, adapter/factory abstractions, async/httpx, Zustand +
> TanStack Query, Tailwind dark theme, registry-driven panels, pure unit-tested
> condition functions. After each step run `cd services/engine &&
> .venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check app` and
> `cd apps/desktop && npm run typecheck && npm run build`. Update `TASKS.md`,
> `CHANGELOG.md`, `PROJECT_STATUS.md`, and `CONTINUE.md` as you go. Verify with
> `npm run dev`.

## 20. How to run
```bash
# First-time setup
npm install                              # root + workspaces (+ electron fix postinstall)
cd services/engine && python -m venv .venv && .venv/Scripts/activate && pip install -e ".[dev]" && cd ../..

# Run (engine + desktop together)
npm run dev
# Engine only: npm run dev:engine   ·   Desktop only: npm run dev:desktop
# Tests:  cd services/engine && .venv/Scripts/python -m pytest -q
# Lint:   cd services/engine && .venv/Scripts/python -m ruff check app
# TS:     cd apps/desktop && npm run typecheck
```
