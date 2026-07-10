#!/usr/bin/env node
/**
 * Smoke-test the packaged Windows build:
 *  1. Assert electron-builder output exists
 *  2. Assert bundled engine binary exists
 *  3. Spawn engine exe, poll /health, exit
 *
 * Run after: npm run package
 */
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const releaseDir = join(root, "apps/desktop/release/win-unpacked");
const appExe = join(releaseDir, "Borsa AI Terminal.exe");
const engineExe = join(releaseDir, "resources/engine/borsa-engine.exe");
const host = process.env.BORSA_ENGINE_HOST || "127.0.0.1";
const port = Number(process.env.BORSA_ENGINE_PORT || 8787);
const healthUrl = `http://${host}:${port}/health`;
const smokeTimeoutMs = Number(process.env.BORSA_SMOKE_TIMEOUT_MS || 120_000);

function fail(msg) {
  console.error(`[package-smoke] FAIL: ${msg}`);
  process.exit(1);
}

function ok(msg) {
  console.log(`[package-smoke] OK: ${msg}`);
}

if (!existsSync(releaseDir)) {
  fail(`Release dir missing: ${releaseDir}\nRun: npm run package`);
}
ok(`Release dir found (${releaseDir})`);

if (!existsSync(appExe)) {
  fail(`Desktop exe missing: ${appExe}`);
}
ok(`Desktop exe found`);

if (!existsSync(engineExe)) {
  fail(`Engine binary missing: ${engineExe}`);
}
ok(`Engine binary found`);

async function waitForHealth(timeoutMs = smokeTimeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const resp = await fetch(healthUrl);
      if (resp.ok) return true;
    } catch {
      // engine still starting
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

console.log("[package-smoke] Starting bundled engine…");
const child = spawn(engineExe, [], {
  cwd: dirname(engineExe),
  env: { ...process.env, BORSA_ENGINE_PORT: String(port) },
  stdio: "ignore",
  windowsHide: true,
});

let exited = false;
child.on("exit", (code) => {
  exited = true;
  if (code !== 0 && code !== null) {
    console.warn(`[package-smoke] Engine exited early (code ${code})`);
  }
});

const ready = await waitForHealth();
if (!ready) {
  child.kill();
  fail(`Engine /health did not respond at ${healthUrl}`);
}

const body = await (await fetch(healthUrl)).json();
ok(`Engine healthy: ${JSON.stringify(body)}`);

child.kill();
console.log("[package-smoke] All checks passed.");
