"use client";

import * as React from "react";
import { getHardwareInfo, type HardwareInfo } from "@/lib/api";

function formatBytes(n: number | null | undefined): string {
  if (!n || n <= 0) return "-";
  const gb = n / 1024 / 1024 / 1024;
  if (gb >= 1) return `${gb.toFixed(gb >= 10 ? 0 : 1)} GB`;
  const mb = n / 1024 / 1024;
  return `${mb.toFixed(0)} MB`;
}

export function HardwareInfoPanel() {
  const [data, setData] = React.useState<HardwareInfo | null>(null);
  const [err, setErr] = React.useState<string | null>(null);

  React.useEffect(() => {
    let alive = true;
    getHardwareInfo()
      .then((d) => {
        if (!alive) return;
        setData(d);
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
        <button
          className="px-3 py-2 rounded bg-gray-900 text-white hover:bg-gray-800"
          onClick={() => alert("TODO: Download CUDA runtime into runtime/gpu/cuda/")}
          type="button"
        >
          Download CUDA Acceleration (Recommended for NVIDIA GPU)
        </button>
        <button
          className="px-3 py-2 rounded bg-gray-900 text-white hover:bg-gray-800"
          onClick={() => alert("TODO: Download AMD runtime into runtime/gpu/amd/")}
          type="button"
        >
          Download AMD Acceleration (Recommended for AMD GPU)
        </button>
      </div>
    </div>
  );
}

