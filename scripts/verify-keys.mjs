#!/usr/bin/env node
/** Run live API-key verification using the engine venv Python. */
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const isWin = process.platform === "win32";
const venvPython = isWin
  ? join(root, "services/engine/.venv/Scripts/python.exe")
  : join(root, "services/engine/.venv/bin/python");
const python = existsSync(venvPython) ? venvPython : isWin ? "python" : "python3";
const script = join(root, "scripts/verify-keys.py");

const result = spawnSync(python, [script], { stdio: "inherit", env: process.env });
process.exit(result.status ?? 1);
