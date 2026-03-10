const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  selectOutputFolder: () => ipcRenderer.invoke("select-output-folder"),
  getOutputFolder: () => ipcRenderer.invoke("get-output-folder"),
});
