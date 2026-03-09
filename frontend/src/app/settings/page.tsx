"use client";

import { useState, useEffect } from "react";
import { CheckCircle, Loader2 } from "lucide-react";
import AppSidebar from "@/components/AppSidebar";
import ExportSettingsPanel from "@/components/ExportSettingsPanel";
import ApiKeysPanel from "@/components/ApiKeysPanel";
import { useAppSettings } from "@/lib/settings-store";

export default function SettingsPage() {
  const [settings, setSettings] = useAppSettings();
  const [showSavedModal, setShowSavedModal] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const handleSave = () => {
    setShowSavedModal(true);
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
          <div className="rounded-xl border border-zinc-700 bg-zinc-800/50 overflow-hidden">
            {mounted ? (
              <ExportSettingsPanel
                settings={settings}
                onChange={setSettings}
                standalone
                onSave={handleSave}
              />
            ) : (
              <div className="p-8 flex items-center justify-center min-h-[200px]">
                <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
              </div>
            )}
          </div>

          <div className="mt-6 rounded-xl border border-zinc-700 bg-zinc-800/50 overflow-hidden">
            <ApiKeysPanel />
          </div>
        </div>
      </main>

      {showSavedModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setShowSavedModal(false)}
        >
          <div
            className="bg-zinc-800 border border-zinc-600 rounded-xl p-6 shadow-xl max-w-sm mx-4 text-center"
            onClick={(e) => e.stopPropagation()}
          >
            <CheckCircle className="w-14 h-14 text-cyan-400 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-white mb-2">Pengaturan sudah disimpan</h3>
            <p className="text-sm text-zinc-400 mb-4">
              Pengaturan akan digunakan untuk preview dan export klip berikutnya.
            </p>
            <button
              onClick={() => setShowSavedModal(false)}
              className="w-full py-2.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black font-medium transition-colors"
            >
              OK
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
