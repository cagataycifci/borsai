# Security Backlog

_Last verified: 2026-08-13._

## npm audit

| Severity | Baseline | Current |
|---|---:|---:|
| Moderate | 2 | 0 |
| High | 21 | 0 |
| Critical | 1 | 0 |
| **Total** | **24** | **0** |

The Node dependency backlog was remediated on a dedicated branch through tested upgrades of Electron, electron-builder, electron-vite, Vite, the React Vite plugin, and Node type definitions. No forced major-version audit fix was used.

## Verification completed

- Dependency installation and lockfile refresh
- `npm audit --audit-level=high`
- Desktop TypeScript typecheck
- Desktop production build
- PyInstaller engine build
- Windows unpacked package
- Bundled-engine health smoke test
- NSIS installer generation

## Remaining security/release work

1. Add code signing and a documented release-key process before distributing a production installer.
2. Run dependency and installer checks on a clean Windows machine.
3. Add Python dependency vulnerability scanning to CI and consider a tested constraints/lock strategy.
4. Migrate deprecated `google.generativeai` usage to the maintained `google.genai` SDK.
5. Continue Dependabot review; never merge dependency upgrades without tests and release checks.
