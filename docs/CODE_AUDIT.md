# Code Audit and Verification

_Last verified: 2026-08-12 on Windows, Python 3.12 and Node 24._

## Repository recovery

The canonical GitHub snapshot was recovered into a separate working directory and matched commit `2134092`. The earlier minimal scaffold was preserved separately and was not pushed over the canonical project.

## Verified successfully

- Python environment and editable engine installation completed.
- `python -m ruff check app`: passed.
- Engine test suite: **64 passed**, with one third-party Starlette/httpx deprecation warning.
- Desktop TypeScript typecheck: passed.
- Electron/Vite production build: passed.
- The repository contains real FastAPI routes, WebSocket support, data/AI adapters, persistence, migrations, Electron main/preload/renderer code, and offline tests.

## Open findings

1. `npm audit` reports **24 findings**: 2 moderate, 21 high, and 1 critical. Several fixes require major upgrades of Vite/electron-builder and must be tested rather than applied with `--force`.
2. The first normal `npm ci` attempt failed while downloading the Electron binary (`socket hang up`). Validation used `npm ci --ignore-scripts`; typecheck and build still passed. A clean Electron runtime/install test remains required.
3. Windows installer and PyInstaller bundle were not produced in this audit.
4. Live Finnhub and hosted AI-provider calls were not tested because no credentials were used.
5. BIST universe coverage remains a curated seed rather than a guaranteed complete official list.
6. Python dependencies use minimum-version ranges and are not fully locked.
7. Public user testing and external contributor evidence are still absent.

## Release gate

Do not describe the project as stable or production-ready until the npm security backlog is triaged, a clean Electron install and Windows package succeed, and at least one independent user completes the documented setup.
