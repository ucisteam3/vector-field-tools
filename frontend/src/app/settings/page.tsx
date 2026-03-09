"use client";

import { useState, useEffect } from "react";
import { CheckCircle, Loader2, ChevronDown, ChevronUp } from "lucide-react";
import AppSidebar from "@/components/AppSidebar";
import ExportSettingsPanel from "@/components/ExportSettingsPanel";
import ApiKeysPanel from "@/components/ApiKeysPanel";
import { useAppSettings } from "@/lib/settings-store";

function AccordionSection({
  title,
  description,
  open,
  onToggle,
  children,
}: {
  title: string;
  description?: string;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-800/50 overflow-hidden">
      <button onClick={onToggle} className="w-full px-5 py-4 flex items-start justify-between text-left">
        <div>
          <div className="text-sm font-semibold text-zinc-100">{title}</div>
          {description && <div className="text-xs text-zinc-400 mt-1">{description}</div>}
        </div>
        <div className="text-zinc-400 mt-0.5">{open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}</div>
      </button>
      {open && <div className="border-t border-zinc-700/50">{children}</div>}
    </div>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useAppSettings();
  const [showSavedModal, setShowSavedModal] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [openExport, setOpenExport] = useState(true);
  const [openKeys, setOpenKeys] = useState(false);

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
          <div className="space-y-4">
            <AccordionSection
              title="Export Settings"
              description="Pengaturan export (mode, zoom, subtitle, watermark, BGM)."
              open={openExport}
              onToggle={() => setOpenExport((v) => !v)}
            >
              {mounted ? (
                <ExportSettingsPanel settings={settings} onChange={setSettings} standalone onSave={handleSave} />
              ) : (
                <div className="p-8 flex items-center justify-center min-h-[200px]">
                  <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
                </div>
              )}
            </AccordionSection>

            <AccordionSection
              title="API Key"
              description="Simpan & test key. 1 key per baris. Rotate hanya saat error."
              open={openKeys}
              onToggle={() => setOpenKeys((v) => !v)}
            >
              <ApiKeysPanel />
            </AccordionSection>
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
