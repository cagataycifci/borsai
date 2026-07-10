import { join } from "node:path";
import { app, BrowserWindow, ipcMain, Notification, shell } from "electron";
import { EngineManager } from "./engine/manager";

const engine = new EngineManager();
let mainWindow: BrowserWindow | null = null;

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 680,
    show: false,
    backgroundColor: "#0a0e14",
    autoHideMenuBar: true,
    titleBarStyle: "hiddenInset",
    webPreferences: {
      preload: join(__dirname, "../preload/index.js"),
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.once("ready-to-show", () => mainWindow?.show());

  // Open external links in the OS browser, never in-app.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url);
    return { action: "deny" };
  });

  // Forward engine status changes to the renderer.
  engine.onStatus((info) => {
    mainWindow?.webContents.send("engine:status", info);
  });

  const devUrl = process.env["ELECTRON_RENDERER_URL"];
  if (devUrl) {
    void mainWindow.loadURL(devUrl);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    void mainWindow.loadFile(join(__dirname, "../renderer/index.html"));
  }
}

function registerIpc(): void {
  ipcMain.handle("engine:getInfo", () => engine.getInfo());

  ipcMain.handle(
    "notify",
    (_evt, payload: { title: string; body: string }) => {
      if (Notification.isSupported()) {
        new Notification({ title: payload.title, body: payload.body }).show();
      }
    },
  );
}

app.whenReady().then(async () => {
  registerIpc();
  createWindow();
  // Start (or attach to) the Python engine after the window exists so the
  // renderer receives the initial status transitions.
  void engine.start();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => engine.stop());
