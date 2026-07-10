import { spawn, type ChildProcess } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { app } from "electron";

export type EngineStatus = "starting" | "ready" | "error" | "stopped";

interface EngineInfo {
  url: string;
  status: EngineStatus;
}

/**
 * Spawns and supervises the Python FastAPI engine sidecar.
 *
 * Behaviour:
 *  - In development the engine is often already running (via `npm run dev`).
 *    We probe `/health` first and reuse it instead of double-spawning.
 *  - Otherwise we spawn it ourselves (venv python in dev, packaged binary in
 *    prod — the packaged-binary path is finalized in the Phase 10 build step).
 *  - We poll `/health` until ready, surfacing status changes to listeners.
 */
export class EngineManager {
  private child: ChildProcess | null = null;
  private status: EngineStatus = "stopped";
  private external = false; // true when attached to an engine we didn't spawn
  private readonly host: string;
  private readonly port: number;
  private listeners = new Set<(info: EngineInfo) => void>();

  constructor() {
    this.host = process.env.BORSA_ENGINE_HOST || "127.0.0.1";
    this.port = Number(process.env.BORSA_ENGINE_PORT || 8787);
  }

  get url(): string {
    return `http://${this.host}:${this.port}`;
  }

  getInfo(): EngineInfo {
    return { url: this.url, status: this.status };
  }

  onStatus(cb: (info: EngineInfo) => void): () => void {
    this.listeners.add(cb);
    return () => this.listeners.delete(cb);
  }

  private setStatus(status: EngineStatus): void {
    this.status = status;
    const info = this.getInfo();
    for (const cb of this.listeners) cb(info);
  }

  async start(): Promise<void> {
    this.setStatus("starting");

    // When the dev orchestrator (`npm run dev`) owns the engine, never spawn our
    // own — just wait for it. First-run universe seeding can take a while, so the
    // grace window is generous; we attach the moment `/health` answers.
    if (process.env.BORSA_DEV_ENGINE === "1") {
      const ready = await this.waitForHealth(60_000);
      this.external = true;
      this.setStatus(ready ? "ready" : "error");
      return;
    }

    if (await this.probeHealth()) {
      // An engine is already running — reuse it.
      this.external = true;
      this.setStatus("ready");
      return;
    }

    try {
      this.spawnEngine();
    } catch (err) {
      console.error("[engine] failed to spawn:", err);
      this.setStatus("error");
      return;
    }

    const ready = await this.waitForHealth(30_000);
    this.setStatus(ready ? "ready" : "error");
  }

  private spawnEngine(): void {
    const { command, args, cwd } = this.resolveLaunch();
    console.log("[engine] spawning:", command, args.join(" "));
    this.child = spawn(command, args, {
      cwd,
      env: {
        ...process.env,
        BORSA_ENGINE_HOST: this.host,
        BORSA_ENGINE_PORT: String(this.port),
      },
      stdio: "pipe",
    });
    this.child.stdout?.on("data", (d) => process.stdout.write(`[engine] ${d}`));
    this.child.stderr?.on("data", (d) => process.stderr.write(`[engine] ${d}`));
    this.child.on("exit", (code) => {
      console.log(`[engine] exited with code ${code}`);
      this.child = null;
      if (this.status === "stopped") return;
      // Our child dying isn't necessarily fatal: another engine (e.g. the dev
      // orchestrator's, or a manually-started one) may be healthy. Re-probe and
      // attach to it rather than surfacing a false error.
      void this.probeHealth().then((healthy) => {
        if (healthy) {
          this.external = true;
          this.setStatus("ready");
        } else {
          this.setStatus("error");
        }
      });
    });
  }

  /** Resolve how to launch the engine for the current environment. */
  private resolveLaunch(): { command: string; args: string[]; cwd: string } {
    const isWin = process.platform === "win32";

    if (!app.isPackaged) {
      // Dev: repo-relative venv + uvicorn.
      const repoRoot = join(app.getAppPath(), "..", "..");
      const engineDir = join(repoRoot, "services", "engine");
      const venvPython = isWin
        ? join(engineDir, ".venv", "Scripts", "python.exe")
        : join(engineDir, ".venv", "bin", "python");
      const python = existsSync(venvPython) ? venvPython : isWin ? "python" : "python3";
      return {
        command: python,
        args: [
          "-m",
          "uvicorn",
          "app.main:app",
          "--host",
          this.host,
          "--port",
          String(this.port),
        ],
        cwd: engineDir,
      };
    }

    // Prod: packaged PyInstaller one-folder bundle in extraResources.
    const binName = isWin ? "borsa-engine.exe" : "borsa-engine";
    const engineDir = join(process.resourcesPath, "engine");
    const binary = join(engineDir, binName);
    if (!existsSync(binary)) {
      throw new Error(`Engine binary not found at ${binary}. Run npm run build:engine first.`);
    }
    return { command: binary, args: [], cwd: engineDir };
  }

  private async probeHealth(): Promise<boolean> {
    try {
      const res = await fetch(`${this.url}/health`, {
        signal: AbortSignal.timeout(1500),
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  private async waitForHealth(timeoutMs: number): Promise<boolean> {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      if (await this.probeHealth()) return true;
      await new Promise((r) => setTimeout(r, 500));
    }
    return false;
  }

  stop(): void {
    this.setStatus("stopped");
    // Only kill an engine we spawned — never an external/orchestrator one.
    if (this.child && !this.external) {
      this.child.kill();
      this.child = null;
    }
  }
}
