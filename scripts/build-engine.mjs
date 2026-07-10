#!/usr/bin/env node
/**
 * Build the Python engine with PyInstaller (Phase 10).
 *
 * Usage: node scripts/build-engine.mjs
 * Output: services/engine/dist/borsa-engine/
 */
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const engineDir = join(root, "services", "engine");
const isWin = process.platform === "win32";
const venvPython = join(
  engineDir,
  ".venv",
  isWin ? "Scripts/python.exe" : "bin/python",
);
const python = existsSync(venvPython) ? venvPython : isWin ? "python" : "python3";

function run(cmd, args, cwd) {
  const r = spawnSync(cmd, args, { cwd, stdio: "inherit", shell: isWin });
  if (r.status !== 0) process.exit(r.status ?? 1);
}

console.log("Installing PyInstaller…");
run(python, ["-m", "pip", "install", "pyinstaller>=6.0"], engineDir);

console.log("Building engine bundle…");
run(python, ["-m", "PyInstaller", "borsa-engine.spec", "--noconfirm"], engineDir);

console.log("Done → services/engine/dist/borsa-engine/");
