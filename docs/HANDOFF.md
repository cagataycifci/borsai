# Handoff — Borsa AI Terminal

> Living document so any new session can continue exactly where the last ended.
> Update the **Current state** and **Next steps** sections at the end of each work block.

## Project one-liner
AI-powered desktop market terminal (BIST + US markets). Electron+React UI,
Python FastAPI engine sidecar, free-tier data behind swappable adapters,
multi-provider AI (Claude/OpenAI/Gemini/Ollama) selectable in Settings.

## Confirmed decisions (from user)
- Desktop shell: **Electron + React** (TypeScript).
- Backend engine: **Python sidecar (FastAPI)**.
- Data: **Free tier first** (yfinance + Finnhub free), behind adapter abstraction.
- AI: **Multi-provider, no hardcoded default** — chosen in Settings.

## Toolchain present on dev machine
- Node v24.17.0, npm 11.13.0, Python 3.12.10, git 2.54 (Windows 11).
- Working dir: `C:\Users\cagat\Desktop\borsa`.

## Key conventions
- BIST symbols stored with `.IS` suffix (yfinance), displayed bare + exchange badge.
- Engine binds loopback `127.0.0.1:8787` (configurable via `BORSA_ENGINE_PORT`).
- Renderer reads engine URL from preload bridge `window.borsa.engineUrl`.
- Secrets encrypted (Fernet), master key in OS keychain (`keyring`). Never plaintext.

## Current state — Phase 2 COMPLETE & verified ✅
Market Data layer done: persistent SQLite DB, a 12,610-symbol universe
(BIST + US) with fast ranked search, a second data provider, settings/secrets
API, and write-through quote persistence. 13 pytest tests pass; ruff clean.

Phase 2 built and verified:
- **DB** (sync SQLAlchemy 2.0 + Alembic + SQLite, WAL): `app/db` (base with
  UTC-aware type, models settings/secrets/symbols/quotes_cache, session,
  repositories). `init_db()` runs `alembic upgrade head` on startup. Alembic
  `env.py` renders the custom UTCDateTime as `sa.DateTime` (portable migrations).
  Decision: sync DB (not async) — robust for single-user SQLite; FastAPI
  threadpools sync handlers. Alembic is the schema source of truth from Phase 2.
- **Settings/secrets** (`app/settings`): `SettingsService` (JSON KV),
  `SecretsService` (Fernet-encrypted provider keys, write-only API). Routes:
  `GET/PUT /api/v1/settings[/{key}]`, `GET/PUT /api/v1/providers/order`,
  `GET/PUT/DELETE /api/v1/secrets[/{provider}]`.
- **Symbol universe** (`app/data/universe`): US from NASDAQ Trader files
  (nasdaqlisted+otherlisted), BIST from bundled `bist_seed.json` (~113 names,
  expandable via KAP later). `SymbolUniverseService` (refresh/ensure_seeded/
  search/stats). Routes `GET /api/v1/symbols/stats`, `POST /api/v1/symbols/refresh`.
  `/api/v1/search` now queries the universe first (ranked: exact>prefix>name),
  falling back to provider search. `auto_seed` config gates startup seeding.
- **Providers**: `FinnhubAdapter` (httpx, key from secrets, US-only; returns
  None for BIST/history so it falls through to yfinance). `factory.py` builds
  the `MarketDataService` chain from provider order + secrets. `SqliteQuoteStore`
  gives write-through persistence + stale-fallback when all providers fail.
- **Frontend**: `UniverseBadge` (title bar) shows symbol count + one-click
  refresh; search already benefits from the DB-backed endpoint. Typecheck+build pass.

Verified: search 'asel'→ASELS.IS first; 'micro'→MU/AMD; settings/secrets/provider
-order roundtrips; universe persists across restarts (no re-seed).

## Earlier — Phase 1 COMPLETE & verified ✅
End-to-end vertical slice works: the Electron app boots, auto-attaches to the
Python engine, and renders live quotes for US + BIST symbols.

Built and verified:
- Monorepo (npm workspaces) + docs + dev orchestrator scripts.
- **Engine** (`services/engine`): FastAPI app factory + lifespan, settings
  (pydantic-settings), logging, async TTL cache, Fernet+keyring secret box,
  `MarketDataAdapter` protocol, `YFinanceAdapter`, `MarketDataService`
  (fallback + cache), routes `/health` `/api/v1/quote/{symbol}`
  `/api/v1/search` `/api/v1/history/{symbol}` `/api/v1/fundamentals/{symbol}`,
  WS hub `/ws/stream` (subscribe/quote frames). 4 pytest tests pass.
- **Desktop** (`apps/desktop`): electron-vite (main/preload/renderer).
  Main spawns+supervises engine (reuses one already running in dev). Preload
  exposes `window.borsa` (engineInfo, onEngineStatus, notify). Renderer: dark
  Bloomberg theme (Tailwind), dockview workspace, Zustand stores (engine,
  quotes, watchlist), QuoteStream WS client w/ reconnect, REST api client,
  TanStack Query search, Sidebar/TitleBar/SearchBar/StatusBadge, WatchPanel +
  DetailPanel. Typecheck + build pass; full `npm run dev` launches the window
  and connects.

Verified data: AAPL (NASDAQ/USD) and ASELS.IS (BIST/TRY) return full quotes
(price, %chg, P/E, EPS, market cap, 52w, sector).

## Known environment gotcha (IMPORTANT for fresh installs)
On this machine, Electron's postinstall `extract-zip` silently extracts only ONE
file from the (valid) cached zip, so `electron-vite dev` fails with
"Error: Electron uninstall". Fix (already applied): extract the cached zip
manually and write `path.txt`. If it recurs after a clean `npm install`:
```
# cached zip lives at: %LOCALAPPDATA%\electron\Cache\<hash>\electron-v33.4.11-win32-x64.zip
# extract it into node_modules/electron/dist and write path.txt = "electron.exe"
```
A helper script may be added at scripts/fix-electron.mjs in a later phase.

## Next steps — Phase 3 (Charts)
- Renderer: integrate `lightweight-charts` (already a dep) in a Chart panel
  registered in the dockview Workspace; wire to `GET /api/v1/history/{symbol}`.
- Timeframes (1m/5m/15m/1h/4h/1D/1W/1M) + candlestick/line/area/Heikin-Ashi.
- Indicators computed engine-side (`app/technical`, pandas-ta) OR client-side;
  RSI/MACD/EMA/SMA/VWAP/Bollinger/Ichimoku/Stochastic/ATR/Volume Profile.
- 4h history: implement the resample in the engine (yfinance has no native 4h;
  `_INTERVAL_MAP` currently maps H4→60m — resample 1h→4h in the data service).
- Drawing tools (trend lines, S/R, Fibonacci) — lightweight-charts primitives.

Open follow-ups / tech debt:
- BIST universe is a curated seed (~113). Full listing needs a KAP scraper
  (`app/data/universe/loaders.py` → add `load_bist_full`). Tracked for later.
- Finnhub adapter is untested against a live key (no key on dev machine); the
  code path is covered by the provider-chain logic + a fake-adapter test.

## How to run
- First-time setup: see README.md (npm install + engine venv + `pip install -e .`).
- Combined dev: `npm run dev` (repo root) — boots engine + Electron together.
- Engine only: `npm run dev:engine`  ·  Desktop only: `npm run dev:desktop`
- Engine tests: `cd services/engine && .venv/Scripts/python -m pytest`
