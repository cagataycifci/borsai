# Contributing to Borsa AI Terminal

Thank you for helping improve Borsa AI Terminal.

## Before you start

- Search existing issues before opening a new one.
- Discuss large or breaking changes in an issue first.
- Never include API keys, tokens, private portfolio data, or licensed market data in commits.
- Keep financial claims source-backed and label AI-generated interpretation clearly.

## Development setup

```bash
npm install
cd services/engine
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
cd ../..
```

## Required checks

```bash
cd services/engine
python -m ruff check app
python -m pytest -q
cd ../..
npm run typecheck -w apps/desktop
npm run build -w apps/desktop
```

## Pull requests

1. Fork the repository and create a focused branch from `main`.
2. Add or update tests for behavior changes.
3. Update documentation and `CHANGELOG.md` when appropriate.
4. Explain the problem, solution, validation performed, and any risks.
5. Keep unrelated formatting or refactors out of the same PR.

All contributions are accepted under the repository's MIT License.
