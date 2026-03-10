"use client";

import * as React from "react";
import { getRuntimeSettings, saveRuntimeSettings, type RuntimeSettings } from "@/lib/api";

const WHISPER_MODELS: { id: RuntimeSettings["whisper_model"]; label: string; size: string }[] = [
  { id: "tiny", label: "tiny", size: "~75MB" },
  { id: "base", label: "base", size: "~145MB" },
  { id: "small", label: "small", size: "~485MB" },
  { id: "medium", label: "medium", size: "~1.5GB" },
  { id: "large", label: "large", size: "~2.9GB" },
];

export function RuntimeSettingsPanel() {
  const [data, setData] = React.useState<RuntimeSettings | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [err, setErr] = React.useState<string | null>(null);

  React.useEffect(() => {
    let alive = true;
    getRuntimeSettings()
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

  const update = async (patch: Partial<RuntimeSettings>) => {
    if (!data) return;
    setSaving(true);
    setErr(null);
    try {
      const next = await saveRuntimeSettings(patch);
      setData({ ...data, ...next });
    } catch (e) {
      setErr(String((e as Error)?.message || e));
    } finally {
      setSaving(false);
    }
  };

  if (err) return <div className="text-sm text-red-600">{err}</div>;
  if (!data) return <div className="text-sm text-gray-600">Memuat runtime settings...</div>;

  return (
    <div className="space-y-4 text-sm">
      <div>
        <label className="block text-xs text-zinc-500 mb-1">Processing Mode</label>
        <select
          value={data.processing_mode}
          onChange={(e) => update({ processing_mode: e.target.value })}
          className="w-full rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white"
          disabled={saving}
        >
          <option value="auto">Auto (recommended)</option>
          <option value="cpu_only">CPU only</option>
          <option value="gpu_acceleration">GPU acceleration</option>
        </select>
      </div>

      <div>
        <label className="block text-xs text-zinc-500 mb-1">Whisper Model</label>
        <select
          value={data.whisper_model}
          onChange={(e) => update({ whisper_model: e.target.value })}
          className="w-full rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white"
          disabled={saving}
        >
          {WHISPER_MODELS.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label} ({m.size})
            </option>
          ))}
        </select>
        <div className="text-xs text-zinc-500 mt-1">
          Model akan otomatis download ke <code>runtime/models/whisper/</code> saat dipakai.
        </div>
      </div>
    </div>
  );
}

