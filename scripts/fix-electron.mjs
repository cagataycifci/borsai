// Repairs a broken Electron install where the postinstall `extract-zip` step
// only extracts one file (a known failure on some Windows setups), leaving
// `node_modules/electron/dist/electron.exe` missing and `electron-vite dev`
// failing with "Error: Electron uninstall".
//
// Strategy: if electron.exe is missing but the cached release zip exists, extract
// it ourselves (PowerShell Expand-Archive on Windows; `unzip` elsewhere) and write
// path.txt. Fully defensive — never throws, so it is safe as a `postinstall` hook.
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync, readdirSync, renameSync, rmSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

function log(msg) {
  console.log(`[fix-electron] ${msg}`);
}

try {
  const electronDir = join(__dirname, "..", "node_modules", "electron");
  if (!existsSync(electronDir)) {
    process.exit(0); // electron not installed (e.g. CI without desktop) — nothing to do
  }

  const platformBin = process.platform === "win32" ? "electron.exe" : "electron";
  const distBin = join(electronDir, "dist", platformBin);
  if (existsSync(distBin)) {
    process.exit(0); // already healthy
  }

  const { version } = JSON.parse(readFileSync(join(electronDir, "package.json"), "utf-8"));
  const arch = process.arch;
  const platform = process.platform === "win32" ? "win32" : process.platform;
  const zipName = `electron-v${version}-${platform}-${arch}.zip`;

  const cacheRoot =
    process.platform === "win32"
      ? join(process.env.LOCALAPPDATA || "", "electron", "Cache")
      : join(process.env.HOME || "", ".cache", "electron");

  if (!existsSync(cacheRoot)) {
    log(`no cache dir at ${cacheRoot}; run electron's installer or reinstall.`);
    process.exit(0);
  }

  // The cache nests the zip under a content-hash directory; find it.
  let zipPath = null;
  for (const entry of readdirSync(cacheRoot)) {
    const candidate = join(cacheRoot, entry, zipName);
    if (existsSync(candidate)) {
      zipPath = candidate;
      break;
    }
  }
  if (!zipPath) {
    log(`cached ${zipName} not found under ${cacheRoot}; reinstall electron.`);
    process.exit(0);
  }

  const distDir = join(electronDir, "dist");
  rmSync(distDir, { recursive: true, force: true });
  log(`extracting ${zipName} → dist ...`);

  if (process.platform === "win32") {
    execFileSync(
      "powershell.exe",
      [
        "-NoProfile",
        "-Command",
        `Expand-Archive -LiteralPath '${zipPath}' -DestinationPath '${distDir}' -Force`,
      ],
      { stdio: "inherit" },
    );
  } else {
    execFileSync("unzip", ["-o", zipPath, "-d", distDir], { stdio: "inherit" });
  }

  // Hoist electron.d.ts and write path.txt, mirroring electron's install.js.
  const dts = join(distDir, "electron.d.ts");
  if (existsSync(dts)) renameSync(dts, join(electronDir, "electron.d.ts"));
  writeFileSync(join(electronDir, "path.txt"), platformBin);

  if (existsSync(distBin)) {
    log("Electron repaired successfully.");
  } else {
    log("extraction completed but binary still missing — manual reinstall needed.");
  }
} catch (err) {
  log(`skipped (non-fatal): ${err?.message ?? err}`);
}
