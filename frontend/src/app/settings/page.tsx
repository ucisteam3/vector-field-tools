"use client";

import { useState } from "react";
import AppSidebar from "@/components/AppSidebar";
import ExportSettingsPanel from "@/components/ExportSettingsPanel";
import { useAppSettings } from "@/lib/settings-store";

export default function SettingsPage() {
  const [settings, setSettings] = useAppSettings();
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0c10] text-white">
      <AppSidebar />
      <main className="flex-1 ml-64 p-8 bg-[#0a0c10]">
        <div className="max-w-2xl">
          <h1 className="text-2xl font-bold mb-2">Setting</h1>
          <p className="text-zinc-400 mb-6">
            Konfigurasi pengaturan sebelum memulai analisis. Preview dan hasil export akan mengikuti pengaturan ini.
          </p>
          {saved && (
            <div className="mb-4 px-4 py-2 rounded-lg bg-cyan-500/20 text-cyan-400 text-sm">
              Tersimpan!
            </div>
          )}
          <div className="rounded-xl border border-zinc-700 bg-zinc-800/50 overflow-hidden">
            <ExportSettingsPanel
              settings={settings}
              onChange={setSettings}
              standalone
              onSave={handleSave}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
