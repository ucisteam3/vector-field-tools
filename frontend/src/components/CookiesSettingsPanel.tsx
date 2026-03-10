"use client";

import { useEffect, useState } from "react";
import { Upload, Loader2, ShieldCheck, FileText, RefreshCw } from "lucide-react";
import { uploadCookies, getCookiesStatus } from "@/lib/api";
import { useModal } from "@/components/ModalProvider";

export default function CookiesSettingsPanel() {
  const modal = useModal();
  const [status, setStatus] = useState<{
    exists: boolean;
    size_kb: number;
    modified_at?: string | null;
  } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadStatus = () => {
    getCookiesStatus()
      .then(setStatus)
      .catch(() => setStatus({ exists: false, size_kb: 0 }))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const formatModified = (iso?: string | null) => {
    if (!iso) return null;
    try {
      const d = new Date(iso);
      return d.toLocaleString("id-ID", {
        dateStyle: "medium",
        timeStyle: "short",
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="p-5 space-y-5">
      <p className="text-sm text-zinc-400">
        Upload file cookies YouTube terbaru agar unduh & subtitle bisa bypass batasan umur/wilayah. File akan disimpan sebagai{" "}
        <code className="text-cyan-400/90 bg-zinc-900 px-1 rounded">www.youtube.com_cookies.txt</code>{" "}
        di folder project.
      </p>

      {/* Status */}
      <div className="rounded-lg border border-zinc-700 bg-zinc-900/50 px-4 py-3 flex flex-wrap items-center gap-3">
        <ShieldCheck className="w-5 h-5 text-zinc-500 flex-shrink-0" />
        {loading ? (
          <span className="text-zinc-500 text-sm flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Memuat status...
          </span>
        ) : status?.exists ? (
          <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-4 text-sm">
            <span className="text-cyan-400 font-medium">
              Cookies aktif — {status.size_kb} KB
            </span>
            {status.modified_at && (
              <span className="text-zinc-500">
                Terakhir diperbarui: <span className="text-zinc-300">{formatModified(status.modified_at)}</span>
              </span>
            )}
          </div>
        ) : (
          <span className="text-amber-400/90 text-sm">Belum ada cookies — unduh video bisa gagal untuk konten terbatas.</span>
        )}
        <button
          type="button"
          onClick={() => {
            setLoading(true);
            loadStatus();
          }}
          className="ml-auto text-xs text-zinc-400 hover:text-cyan-400 flex items-center gap-1"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {/* Upload */}
      <div>
        <label className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2 block">
          Upload cookies terbaru (.txt)
        </label>
        <label className="flex flex-col sm:flex-row items-center justify-center gap-3 px-6 py-8 rounded-xl border-2 border-dashed border-zinc-600 hover:border-cyan-500/50 bg-zinc-900/30 cursor-pointer transition-colors">
          <Upload className="w-8 h-8 text-zinc-500" />
          <div className="text-center sm:text-left">
            <span className="text-zinc-200 font-medium block">
              {uploading ? "Mengunggah..." : "Klik atau seret file cookies (.txt)"}
            </span>
            <span className="text-xs text-zinc-500">Format Netscape dari ekstensi Get cookies.txt (Chrome/Firefox)</span>
          </div>
          <input
            type="file"
            accept=".txt"
            className="hidden"
            disabled={uploading}
            onChange={async (e) => {
              const f = e.target.files?.[0];
              if (!f) return;
              setUploading(true);
              try {
                await uploadCookies(f);
                setStatus(await getCookiesStatus());
                await modal.alert(
                  "Cookies berhasil diperbarui. Unduh video selanjutnya akan memakai file ini.",
                  { title: "Berhasil" }
                );
              } catch (err) {
                await modal.alert(String(err), { title: "Upload cookies gagal" });
              } finally {
                setUploading(false);
                e.target.value = "";
              }
            }}
          />
        </label>
      </div>

      {/* Cara ambil cookies */}
      <div className="rounded-lg border border-zinc-700/80 bg-zinc-900/30 p-4">
        <div className="flex items-center gap-2 text-sm font-medium text-zinc-300 mb-2">
          <FileText className="w-4 h-4 text-cyan-500" />
          Cara update cookies terbaru
        </div>
        <ol className="text-xs text-zinc-400 space-y-2 list-decimal list-inside">
          <li>
            Pasang ekstensi browser: <strong className="text-zinc-300">Get cookies.txt LOCALLY</strong> (Chrome Store) atau serupa.
          </li>
          <li>Buka YouTube, login ke akun Anda.</li>
          <li>
            Klik ekstensi → export untuk domain <code className="text-cyan-400/90">youtube.com</code> → simpan file{" "}
            <code className="text-cyan-400/90">.txt</code>.
          </li>
          <li>Upload file tersebut di sini. Ganti file lama dengan yang baru bila cookies kadaluarsa.</li>
          <li>
            <strong className="text-zinc-300">Video terbatas umur</strong>: buka video tersebut di browser, konfirmasi umur, lalu export cookies lagi — unduh via aplikasi butuh session yang sama.
          </li>
        </ol>
      </div>
    </div>
  );
}
