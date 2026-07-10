# Architecture — Borsa AI Terminal

> An AI-powered desktop market terminal monitoring Borsa Istanbul (BIST) and US
> markets (NYSE / NASDAQ / AMEX). Built as a modular, production-grade system.

---

## 1. High-level topology

```
Electron Desktop (apps/desktop)
  ├─ Main process      → lifecycle, OS tray, native notifications, spawns engine
  ├─ Preload bridge    → typed, sandboxed IPC surface (contextBridge)
  └─ Renderer (React)  → UI: dockable panels, charts, AI, news, portfolio
        │  HTTP + WebSocket over 127.0.0.1
        ▼
Python Engine (services/engine) — FastAPI + asyncio
  ├─ API layer         → REST routers + WebSocket hubs
  ├─ Data layer        → market data adapters (yfinance, Finnhub, …)
  ├─ News layer        → RSS / KAP / SEC aggregation
  ├─ AI layer          → provider abstraction (Claude/OpenAI/Gemini/Ollama)
  ├─ Technical         → indicators (pandas-ta)
  ├─ Fundamental       → ratios, statements
  ├─ Portfolio/Alerts  → holdings, P&L, alert engine
  ├─ Scheduler         → APScheduler background jobs
  ├─ Core              → config, logging, DI, security, cache
  └─ Persistence       → SQLite via SQLAlchemy 2.0 + Alembic
```

### Why a split (Electron UI + Python engine)?
- **Right tool per job.** Quant math, scraping and AI orchestration have a far
  richer Python ecosystem (pandas, pandas-ta, yfinance, feedparser, the official
  AI SDKs). The UI has the richest ecosystem in React/Electron.
- **Clean seam.** The engine exposes a localhost HTTP+WS API. It can be unit
  tested headless, run without the UI, or be relocated later with zero UI churn.
- **Isolation = modularity.** Each engine sub-package is independent and depends
  only on `core` + interfaces, satisfying the "every module isolated" requirement.

---

## 2. Repository layout

```
borsa/
├─ apps/
│  └─ desktop/                  # Electron + React (TypeScript, electron-vite)
│     ├─ electron.vite.config.ts
│     ├─ src/
│     │  ├─ main/               # Electron main process
│     │  │  ├─ index.ts         # app bootstrap, window mgmt
│     │  │  ├─ engine/          # spawns + supervises Python sidecar
│     │  │  ├─ tray.ts          # system tray
│     │  │  └─ notifications.ts # native notifications
│     │  ├─ preload/
│     │  │  └─ index.ts         # contextBridge IPC surface
│     │  └─ renderer/
│     │     └─ src/
│     │        ├─ app/          # shell, layout, routing, providers
│     │        ├─ features/     # feature modules (one folder per domain)
│     │        │  ├─ dashboard/
│     │        │  ├─ watchlist/
│     │        │  ├─ portfolio/
│     │        │  ├─ charts/
│     │        │  ├─ news/
│     │        │  ├─ ai/
│     │        │  └─ settings/
│     │        ├─ components/    # shared presentational components
│     │        ├─ lib/          # api client, ws client, formatters
│     │        ├─ store/        # Zustand stores
│     │        └─ styles/       # Tailwind + theme tokens
│     └─ package.json
│
├─ services/
│  └─ engine/                   # Python FastAPI backend
│     ├─ app/
│     │  ├─ main.py             # FastAPI app factory + lifespan
│     │  ├─ core/               # config, logging, security, cache, errors
│     │  ├─ db/                 # engine, session, models, repositories
│     │  ├─ data/               # market data adapters + service
│     │  │  ├─ base.py          # MarketDataAdapter protocol
│     │  │  ├─ providers/       # yfinance, finnhub, …
│     │  │  └─ service.py       # orchestrates adapters + cache
│     │  ├─ news/               # (Phase 5)
│     │  ├─ ai/                 # (Phase 6) provider abstraction
│     │  ├─ technical/          # (Phase 3) indicators
│     │  ├─ fundamental/        # (Phase 2)
│     │  ├─ portfolio/          # (Phase 4)
│     │  ├─ alerts/             # (Phase 7)
│     │  ├─ scheduler/          # (Phase 8)
│     │  └─ api/                # routers + websocket hubs
│     ├─ tests/
│     ├─ pyproject.toml
│     └─ alembic/               # migrations (added Phase 2)
│
├─ docs/
│  ├─ ARCHITECTURE.md           # this file
│  ├─ ROADMAP.md                # phases + status
│  └─ HANDOFF.md                # living continuation doc
├─ package.json                 # npm workspace root
└─ README.md
```

---

## 3. Communication contract

- Engine listens on `127.0.0.1:<port>` (default `8787`, configurable).
- **REST** for request/response (quotes, search, fundamentals, AI reports).
- **WebSocket** (`/ws/stream`) for push (price ticks, news, alerts).
- The Electron main process injects the chosen port via env var and passes it to
  the renderer through the preload bridge (`window.borsa.engineUrl`).
- All payloads validated by Pydantic (engine) and typed in TS (renderer). Shared
  shapes are mirrored in `renderer/src/lib/contracts.ts`.

### Engine endpoints (cumulative; Phase 1 in **bold**)
| Method | Path | Purpose | Phase |
|---|---|---|---|
| GET | **`/health`** | liveness + version | 1 |
| GET | **`/api/v1/quote/{symbol}`** | latest quote snapshot | 1 |
| GET | **`/api/v1/search?q=`** | symbol/company search | 1 |
| WS  | **`/ws/stream`** | realtime tick/news/alert hub | 1 (skeleton) |
| GET | `/api/v1/fundamentals/{symbol}` | ratios, statements | 2 |
| GET | `/api/v1/history/{symbol}` | OHLCV candles | 2/3 |
| GET | `/api/v1/news` | aggregated news | 5 |
| POST | `/api/v1/ai/analyze` | full AI stock report | 6 |
| POST | `/api/v1/ai/chat` | AI assistant | 6 |
| CRUD | `/api/v1/portfolio`, `/api/v1/watchlists`, `/api/v1/alerts` | user data | 4/7 |

---

## 4. Data adapter abstraction

The single most important design decision for swappable data sources.

```python
class MarketDataAdapter(Protocol):
    name: str
    async def get_quote(self, symbol: str) -> Quote | None: ...
    async def search(self, query: str) -> list[SymbolRef]: ...
    async def get_history(self, symbol: str, interval, range_) -> list[Candle]: ...
    async def get_fundamentals(self, symbol: str) -> Fundamentals | None: ...
```

- Concrete providers (yfinance, Finnhub) implement the protocol.
- `MarketDataService` holds an ordered list of adapters and applies a
  **fallback + cache** policy: try primary, fall back on failure, cache by TTL.
- Paid/real-time providers are added later as new adapters — **no call-site
  changes**. The active provider order is configurable in Settings.

Symbol convention: BIST tickers use the yfinance `.IS` suffix internally
(e.g. `ASELS.IS`); the UI displays the bare ticker plus an exchange badge.

---

## 5. Persistence (SQLite)

Embedded, zero-config, file at `%APPDATA%/BorsaAI/borsa.db`. SQLAlchemy 2.0 ORM,
Alembic migrations (from Phase 2). Core tables (built up across phases):

- `settings(key, value)` — app config (JSON values).
- `secrets(provider, ciphertext, created_at)` — Fernet-encrypted API keys.
- `symbols(symbol, name, exchange, sector, industry, currency, type)` — universe.
- `quotes_cache(symbol, payload_json, fetched_at)` — last quote snapshot.
- `watchlists(id, name)` / `watchlist_items(watchlist_id, symbol)`.
- `holdings(id, symbol, quantity, avg_cost, purchase_date, target, stop_loss)`.
- `news(id, source, url, title, summary, published_at, symbols, ai_label, …)`.
- `alerts(id, type, symbol, condition_json, active, triggered_at)`.
- `ai_reports(id, symbol, provider, model, report_json, created_at)`.

---

## 6. Security

- API keys are **never** stored in plaintext. A master key is generated once and
  stored in the OS keychain via `keyring`. Provider keys are encrypted with
  Fernet (derived from the master key) and stored in `secrets`.
- The engine binds to loopback only (`127.0.0.1`). No external surface.
- Electron renderer runs with `contextIsolation: true`, `nodeIntegration: false`,
  `sandbox: true`. The only privileged surface is the typed preload bridge.
- Secrets never cross IPC to the renderer; the renderer references providers by
  name and the engine resolves keys internally.

---

## 7. Performance strategy

- **Async everywhere** in the engine (httpx, asyncio); blocking libs (yfinance)
  run in a thread pool via `asyncio.to_thread`.
- **TTL cache** for quotes/fundamentals to collapse duplicate requests and respect
  free-tier rate limits.
- **Batch + fan-in** WebSocket pushes (one tick frame for many symbols).
- **TanStack Query** on the renderer dedupes and background-refreshes.
- **APScheduler** runs heavy work (news polling, daily reports) off the request path.
- Rate-limit handling + exponential-backoff retry in the adapter base class.

---

## 8. Key challenges & mitigations

| Challenge | Mitigation |
|---|---|
| Real-time BIST data is paid/locked | Adapter abstraction; start delayed (yfinance), drop in paid later |
| Free-tier rate limits | TTL cache, request coalescing, backoff, multi-provider fallback |
| Packaging a Python sidecar with Electron | PyInstaller one-file binary, shipped as electron extraResource (Phase 10) |
| yfinance is sync + fragile | Wrap in `to_thread`, retry, treat as best-effort, cache last good |
| AI cost/latency | Cache reports, stream responses, let user pick provider/model |
| KAP/news scraping brittleness | Per-source parsers behind a `NewsSource` interface, fail isolated |
| Multi-currency (TRY/USD) | Store native currency per symbol; convert at display time |

---

## 9. As-built notes (updated end of Phase 2)

These refine §5/§3 with decisions made during implementation:

- **DB layer is synchronous** SQLAlchemy 2.0 (not async). Rationale: single-user
  embedded SQLite (WAL); FastAPI runs sync route handlers in a threadpool, so the
  event loop is never blocked. Async remains in the data/provider/HTTP layer.
- **Alembic is the schema source of truth** from Phase 2. `app/db/session.py::init_db()`
  runs `alembic upgrade head` on startup (dev + packaged). `alembic/env.py` renders
  the custom `UTCDateTime` type as `sa.DateTime` so migrations don't import app code.
- **Provider chain is config-driven**: `app/data/factory.py` builds
  `MarketDataService` from the `data.provider_order` setting + encrypted secrets.
  Active providers now: **yfinance** (US + BIST) and **Finnhub** (US, when keyed).
- **Universe-first search**: `/api/v1/search` queries the local `symbols` table
  (ranked exact > prefix > name) and falls back to live provider search.
- **Live endpoints** (Phase 1–3): `/health`; `/api/v1/{search, quote/{symbol},
  history/{symbol}, indicators/{symbol}, fundamentals/{symbol}, symbols/stats,
  symbols/refresh, settings[/{key}], providers/order, secrets[/{provider}]}`;
  `WS /ws/stream`.
- **(Phase 3) Technical module** (`app/technical/`): `resample.py` synthesizes 4h
  candles (1h → resample); `indicators.py` computes the indicator suite (SMA, EMA,
  RSI, MACD, Bollinger, VWAP, Stochastic, ATR, Ichimoku) in pure pandas, returned
  JSON-safe (NaN→null) with a per-series `pane` render hint. Charts use
  lightweight-charts v4; oscillator sub-panes are pending (v4 lacks multi-pane).
- **New-files reference**: see `CONTINUE.md` §3 (folder structure) and §15 (files
  modified) for the current layout. `CONTINUE.md` is the canonical continuation doc.


