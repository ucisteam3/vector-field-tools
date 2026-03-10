"use client";

import * as React from "react";
import {
  downloadWhisperModel,
  getRuntimeSettings,
  getRuntimeStatus,
  saveRuntimeSettings,
  type RuntimeSettings,
  type RuntimeStatus,
} from "@/lib/api";

const WHISPER_MODELS: { id: RuntimeSettings["whisper_model"]; label: string; size: string }[] = [
  { id: "tiny", label: "tiny", size: "~75MB" },
  { id: "base", label: "base", size: "~145MB" },
  { id: "small", label: "small", size: "~485MB" },
  { id: "medium", label: "medium", size: "~1.5GB" },
  { id: "large", label: "large", size: "~2.9GB" },
];

export function RuntimeSettingsPanel() {
  const [data, setData] = React.useState<RuntimeSettings | null>(null);
  const [rt, setRt] = React.useState<RuntimeStatus | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [err, setErr] = React.useState<string | null>(null);
  const [downloading, setDownloading] = React.useState(false);

  React.useEffect(() => {
    let alive = true;
    Promise.all([getRuntimeSettings(), getRuntimeStatus()])
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

  const installed = new Set((rt?.whisper?.installed || []).map((x) => String(x)));
  const selectedInstalled = installed.has(String(data.whisper_model));

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
        <div className="flex gap-2">
          <select
            value={data.whisper_model}
            onChange={(e) => update({ whisper_model: e.target.value })}
            className="flex-1 rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white"
            disabled={saving || downloading}
          >
            {WHISPER_MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label} ({m.size})
              </option>
            ))}
          </select>

          {!selectedInstalled && (
            <button
              type="button"
              className="px-3 py-2 rounded bg-cyan-500 text-black hover:bg-cyan-400 disabled:opacity-60"
              disabled={downloading || saving}
              onClick={async () => {
                setDownloading(true);
                setErr(null);
                try {
                  await downloadWhisperModel(String(data.whisper_model));
                  const s = await getRuntimeStatus();
                  setRt(s);
                } catch (e) {
                  setErr(String((e as Error)?.message || e));
                } finally {
                  setDownloading(false);
                }
              }}
            >
              Download
            </button>
          )}
        </div>
        <div className="text-xs text-zinc-500 mt-1">
          Status:{" "}
          <span className={selectedInstalled ? "text-green-400" : "text-yellow-300"}>
            {selectedInstalled ? "Installed" : "Not installed"}
          </span>{" "}
          — model akan disimpan di <code>runtime/models/whisper/</code>.
        </div>
      </div>
    </div>
  );
}

