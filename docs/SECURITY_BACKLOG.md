# Security Backlog

_Last generated: 2026-08-12._

## npm audit baseline

- Moderate: 2
- High: 21
- Critical: 1
- Total: 24

The findings include transitive dependencies under the Electron/Vite/electron-builder toolchain. Available remediations include major-version upgrades, so `npm audit fix --force` was intentionally not run.

## Remediation plan

1. Create a dedicated dependency-upgrade branch.
2. Upgrade direct dependencies in small groups, starting with electron-builder and Vite-related packages.
3. Run typecheck, production build, installer packaging, and startup smoke tests after each group.
4. Re-run `npm audit --json` and document residual findings and exploitability.
5. Do not publish a stable installer while an applicable critical finding remains unresolved.
