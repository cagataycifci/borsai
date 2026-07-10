# Roadmap & Status — Borsa AI Terminal

Status legend: ☐ not started · ◐ in progress · ☑ done

| # | Phase | Scope | Status |
|---|---|---|---|
| 1 | Foundation | Monorepo, engine skeleton, Electron shell, data adapter + yfinance, end-to-end quote slice | ☑ |
| 2 | Market Data | Full quote/fundamentals/history, symbol universe (BIST+US), caching, WS streaming | ☑ |
| 3 | Charts | lightweight-charts, indicators, timeframes, drawing tools | ☑ |
| 4 | Watchlists & Portfolio | CRUD, P&L, persistence, multiple watchlists | ☑ |
| 5 | News Layer | RSS aggregation, dedup, storage, per-source parsers | ☑ |
| 6 | AI Layer | Provider abstraction, stock analysis report, news classification, AI chat | ☑ |
| 7 | Alerts & Notifications | Alert engine, desktop notifications, auto-refresh portfolio page | ☑ |
| 8 | Scheduler & Reports | Morning market summary, background workers, economic calendar | ☑ |
| 9 | Commentator/Sentiment + Search | Consensus analysis, global search | ☑ |
| 10 | Hardening | Tests, packaging (PyInstaller + electron-builder), perf, docs | ☑ |

**All 10 phases complete.** See `PROJECT_STATUS.md` for current health and follow-ups.
