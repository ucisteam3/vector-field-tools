"use client";

import { useEffect, useState } from "react";
import { FolderOpen, Save } from "lucide-react";

export default function OutputFolderPanel() {
  const [path, setPath] = useState<string>("");
  const [isElectron, setIsElectron] = useState(false);

  useEffect(() => {
    const api = (window as any).electronAPI;
    if (api && typeof api.getOutputFolder === "function") {
      setIsElectron(true);
      api.getOutputFolder().then((p: string) => setPath(p || "")).catch(() => {});
    }
  }, []);

  const select = async () => {
    const api = (window as any).electronAPI;
    if (!api?.selectOutputFolder) return;
    const folder = await api.selectOutputFolder();
    if (folder) setPath(folder);
  };

  return (
    <div className="p-5 space-y-4">
      {!isElectron ? (
        <div className="text-sm text-zinc-400">
          Output Folder hanya tersedia di aplikasi Desktop (Electron).
        </div>
      ) : (
        <>
          <div>
            <div className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2">Lokasi export klip</div>
            <div className="rounded-lg border border-zinc-700 bg-zinc-900/50 px-4 py-3 text-sm text-zinc-200 break-all">
              {path ? path : <span className="text-zinc-500">Belum dipilih (akan pakai folder project)</span>}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={select}
              className="px-3 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black text-sm font-medium flex items-center gap-2"
            >
              <FolderOpen className="w-4 h-4" /> Pilih Output Folder
            </button>
            <div className="text-xs text-zinc-500">
              Disimpan otomatis ke <code className="text-zinc-300">config/settings.json</code>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
