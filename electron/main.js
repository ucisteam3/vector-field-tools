const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const http = require("http");

let pyProcess = null;
let feProcess = null;

const BACKEND_URL = "http://127.0.0.1:8001";
const FRONTEND_URL = "http://127.0.0.1:3000";

function waitForUrl(url, timeoutMs = 60000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(url, (res) => {
        res.resume();
        if (res.statusCode && res.statusCode >= 200 && res.statusCode < 500) {
          resolve(true);
        } else {
          retry();
        }
      });
      req.on("error", retry);
      req.setTimeout(2500, () => {
        req.destroy(new Error("timeout"));
      });

      function retry() {
        if (Date.now() - start > timeoutMs) {
          reject(new Error(`Timeout waiting for ${url}`));
          return;
        }
        setTimeout(tick, 500);
      }
    };
    tick();
  });
}

function startPythonBackend() {
  if (pyProcess) return;
  const projectRoot = path.resolve(__dirname, "..");

  // Start: python server.py (port 8001)
  pyProcess = spawn("python", ["server.py"], {
    cwd: projectRoot,
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });

  pyProcess.stdout.on("data", (data) => {
    console.log(`[PY] ${data.toString().trimEnd()}`);
  });
  pyProcess.stderr.on("data", (data) => {
    console.error(`[PY] ${data.toString().trimEnd()}`);
  });
  pyProcess.on("exit", (code) => {
    console.log(`[PY] exited with code ${code}`);
    pyProcess = null;
  });
}

function startFrontend() {
  if (feProcess) return;
  const projectRoot = path.resolve(__dirname, "..");
  const frontendDir = path.join(projectRoot, "frontend");

  // Use local npm on PATH
  feProcess = spawn("npm", ["run", "dev"], {
    cwd: frontendDir,
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });

  feProcess.stdout.on("data", (data) => {
    console.log(`[FE] ${data.toString().trimEnd()}`);
  });
  feProcess.stderr.on("data", (data) => {
    console.error(`[FE] ${data.toString().trimEnd()}`);
  });
  feProcess.on("exit", (code) => {
    console.log(`[FE] exited with code ${code}`);
    feProcess = null;
  });
}

async function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.on("closed", () => {
    // noop
  });

  // Wait for servers to be ready then load UI
  try {
    await waitForUrl(`${BACKEND_URL}/cookies_status`, 60000);
  } catch (e) {
    console.error(String(e));
  }
  try {
    await waitForUrl(FRONTEND_URL, 60000);
  } catch (e) {
    console.error(String(e));
  }

  await win.loadURL(FRONTEND_URL);
}

function stopChild(proc, name) {
  if (!proc) return;
  try {
    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", String(proc.pid), "/T", "/F"], { windowsHide: true });
    } else {
      proc.kill("SIGTERM");
    }
    console.log(`[${name}] stop requested`);
  } catch {
    // ignore
  }
}

app.whenReady().then(async () => {
  startPythonBackend();
  startFrontend();
  await createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  stopChild(feProcess, "FE");
  stopChild(pyProcess, "PY");
});
