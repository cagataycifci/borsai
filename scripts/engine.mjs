// Locates the engine's Python interpreter (prefers the local .venv) and runs
// the FastAPI app with uvicorn in reload mode for development.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const engineDir = join(__dirname, "..", "services", "engine");
const isWin = process.platform === "win32";

const venvPython = isWin
  ? join(engineDir, ".venv", "Scripts", "python.exe")
  : join(engineDir, ".venv", "bin", "python");

const python = existsSync(venvPython) ? venvPython : isWin ? "python" : "python3";

if (!existsSync(venvPython)) {
  console.warn(
    "[engine] No .venv found; falling back to system Python. " +
      "Run the setup steps in README.md for an isolated environment.",
  );
}

const host = process.env.BORSA_ENGINE_HOST || "127.0.0.1";
const port = process.env.BORSA_ENGINE_PORT || "8787";

const child = spawn(
  python,
  ["-m", "uvicorn", "app.main:app", "--host", host, "--port", port, "--reload"],
  { cwd: engineDir, stdio: "inherit", env: process.env },
);

child.on("exit", (code) => process.exit(code ?? 0));
process.on("SIGINT", () => child.kill("SIGINT"));
process.on("SIGTERM", () => child.kill("SIGTERM"));
