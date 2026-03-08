"use client";

import AppSidebar from "@/components/AppSidebar";
import ExportSettingsPanel from "@/components/ExportSettingsPanel";
import { useAppSettings } from "@/lib/settings-store";

export default function SettingsPage() {
  const [settings, setSettings] = useAppSettings();

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0c10] text-white">
      <AppSidebar />
      <main className="flex-1 ml-64 p-8 bg-[#0a0c10]">
        <div className="max-w-2xl">
          <h1 className="text-2xl font-bold mb-2">Setting</h1>
          <p className="text-zinc-400 mb-6">
            Konfigurasi pengaturan sebelum memulai analisis. Preview dan hasil export akan mengikuti pengaturan ini.
          </p>
          <div className="rounded-xl border border-zinc-700 bg-zinc-800/50 overflow-hidden">
            <ExportSettingsPanel settings={settings} onChange={setSettings} />
          </div>
        </div>
      </main>
    </div>
  );
}
