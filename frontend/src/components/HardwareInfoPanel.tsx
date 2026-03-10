"use client";

import * as React from "react";
import { checkRuntimeUpdates, getHardwareInfo, getRuntimeStatus, type HardwareInfo, type RuntimeStatus } from "@/lib/api";

function formatBytes(n: number | null | undefined): string {
  if (!n || n <= 0) return "-";
  const gb = n / 1024 / 1024 / 1024;
  if (gb >= 1) return `${gb.toFixed(gb >= 10 ? 0 : 1)} GB`;
  const mb = n / 1024 / 1024;
  return `${mb.toFixed(0)} MB`;
}

export function HardwareInfoPanel() {
  const [data, setData] = React.useState<HardwareInfo | null>(null);
  const [rt, setRt] = React.useState<RuntimeStatus | null>(null);
  const [err, setErr] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    let alive = true;
    Promise.all([getHardwareInfo(), getRuntimeStatus()])
      .then(([d, s]) => {
        if (!alive) return;
        setData(d);
        setRt(s);
      })
      .catch((e) => {
        if (!alive) return;
        setErr(String((e as Error)?.message || e));
      });
    return () => {
      alive = false;
    };
  }, []);

  if (err) return <div className="text-sm text-red-600">Gagal membaca hardware: {err}</div>;
  if (!data) return <div className="text-sm text-gray-600">Mendeteksi hardware...</div>;

  return (
    <div className="text-sm space-y-2">
      <div className="font-medium">Kelas Performa: {data.tier}</div>
      <div>
        <div>CPU: {data.cpu || "-"}</div>
        <div>Cores: {data.cpu_cores ?? "-"}</div>
        <div>RAM: {formatBytes(data.ram_bytes)}</div>
      </div>
      <div>
        <div>GPU: {data.gpu || "-"}</div>
        <div>VRAM: {formatBytes(data.vram_bytes)}</div>
        <div>CUDA: {data.cuda_available ? "available" : "not available"}</div>
      </div>
      <div className="text-gray-600">
        Installing GPU acceleration can increase processing speed by up to 10x.
      </div>
      <div className="flex flex-col gap-2">
        {data.cuda_available ? (
          <button
            className="px-3 py-2 rounded bg-gray-900 text-white hover:bg-gray-800 disabled:opacity-60"
            onClick={async () => {
              setBusy(true);
              try {
                await checkRuntimeUpdates();
                const s = await getRuntimeStatus();
                setRt(s);
              } catch (e) {
                setErr(String((e as Error)?.message || e));
              } finally {
                setBusy(false);
              }
            }}
            type="button"
            disabled={busy}
          >
            Check for update (FFmpeg/Runtime)
          </button>
        ) : (
          <div className="text-xs text-zinc-500">
            CUDA tidak terdeteksi. (NVIDIA GPU acceleration tidak tersedia di PC ini)
          </div>
        )}

        {rt?.ffmpeg?.bundled_present === false && (
          <div className="text-xs text-red-600">FFmpeg runtime missing (akan di-install otomatis saat update).</div>
        )}
      </div>
    </div>
  );
}

