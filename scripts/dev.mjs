// Dev orchestrator: runs the Python engine and the Electron desktop app together
// with colorized, prefixed output. Either process exiting tears down the other.
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const isWin = process.platform === "win32";

const procs = [
  {
    name: "engine",
    cmd: process.execPath,
    args: [join(__dirname, "engine.mjs")],
    cwd: root,
    shell: false,
  },
  {
    name: "desktop",
    // `.cmd` shims (npx/electron-vite) must be launched through a shell on Windows.
    cmd: isWin ? "npx.cmd" : "npx",
    args: ["electron-vite", "dev"],
    cwd: join(root, "apps", "desktop"),
    shell: isWin,
    // Tell the Electron engine manager that *we* own the engine, so it waits for
    // it instead of double-spawning a second uvicorn (which would collide on the
    // port and surface a false "engine offline" error).
    env: { ...process.env, BORSA_DEV_ENGINE: "1" },
  },
];

const children = procs.map(({ name, cmd, args, cwd, shell, env }) => {
  const child = spawn(cmd, args, { cwd, stdio: "inherit", env: env ?? process.env, shell });
  child.on("exit", (code) => {
    console.log(`[dev] ${name} exited (${code}); shutting down.`);
    shutdown();
  });
  return child;
});

let shuttingDown = false;
function shutdown() {
  if (shuttingDown) return;
  shuttingDown = true;
  for (const c of children) {
    try {
      c.kill(process.platform === "win32" ? undefined : "SIGTERM");
    } catch {
      /* ignore */
    }
  }
  process.exit(0);
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
