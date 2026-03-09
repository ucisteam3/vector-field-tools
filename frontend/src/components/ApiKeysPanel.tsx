"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, Save, RefreshCw, ChevronDown, ChevronUp } from "lucide-react";
import { getApiKeys, saveApiKeys, testApiKeys, type ApiKeysPayload, type ApiKeyTestResult } from "@/lib/api";

function normalizeLines(text: string): string[] {
  return text
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0);
}

function toText(lines: string[]): string {
  return (lines || []).join("\n");
}

type ProviderKey =
  | "openai"
  | "gemini"
  | "anthropic"
  | "llama"
  | "deepseek"
  | "groq";

const PROVIDERS: Array<{ key: ProviderKey; label: string; hint: string }> = [
  { key: "openai", label: "OpenAI – GPT series", hint: "1 key per baris. Rotation hanya saat key error." },
  { key: "gemini", label: "Google – Gemini API", hint: "1 key per baris. Rotation hanya saat key error." },
  { key: "anthropic", label: "Anthropic – Claude", hint: "Disimpan untuk future use." },
  { key: "llama", label: "Meta – Llama API", hint: "Disimpan untuk future use." },
  { key: "deepseek", label: "DeepSeek API", hint: "Disimpan untuk future use." },
  { key: "groq", label: "Groq", hint: "Disimpan untuk future use." },
];

const EMPTY: ApiKeysPayload = {
  openai: [],
  gemini: [],
  anthropic: [],
  llama: [],
  deepseek: [],
  groq: [],
  rotate_on_error: {
    openai: true,
    gemini: true,
    anthropic: true,
    llama: true,
    deepseek: true,
    groq: true,
  },
};

export default function ApiKeysPanel() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [testing, setTesting] = useState<Record<string, boolean>>({});
  const [testResults, setTestResults] = useState<Record<string, ApiKeyTestResult[]>>({});
  const [testNote, setTestNote] = useState<Record<string, string | undefined>>({});
  const [open, setOpen] = useState<Record<string, boolean>>({
    openai: true,
    gemini: true,
    anthropic: false,
    llama: false,
    deepseek: false,
    groq: false,
  });

  const [form, setForm] = useState<Record<ProviderKey, string>>({
    openai: "",
    gemini: "",
    anthropic: "",
    llama: "",
    deepseek: "",
    groq: "",
  });
  const [rotate, setRotate] = useState<Record<string, boolean>>(EMPTY.rotate_on_error);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setLoading(true);
        const data = await getApiKeys();
        if (!alive) return;
        setForm({
          openai: toText(data.openai),
          gemini: toText(data.gemini),
          anthropic: toText(data.anthropic),
          llama: toText(data.llama),
          deepseek: toText(data.deepseek),
          groq: toText(data.groq),
        });
        setRotate({ ...EMPTY.rotate_on_error, ...(data.rotate_on_error || {}) });
        setError(null);
        setDirty(false);
        setSaved(false);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const payload: ApiKeysPayload = useMemo(
    () => ({
      openai: normalizeLines(form.openai),
      gemini: normalizeLines(form.gemini),
      anthropic: normalizeLines(form.anthropic),
      llama: normalizeLines(form.llama),
      deepseek: normalizeLines(form.deepseek),
      groq: normalizeLines(form.groq),
      rotate_on_error: rotate,
    }),
    [form, rotate]
  );

  async function onSave() {
    try {
      setSaving(true);
      setSaved(false);
      await saveApiKeys(payload);
      setSaved(true);
      setDirty(false);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  async function onTest(provider: ProviderKey) {
    try {
      setTesting((t) => ({ ...t, [provider]: true }));
      setError(null);
      const r = await testApiKeys(provider, "all");
      setTestResults((s) => ({ ...s, [provider]: r.results || [] }));
      setTestNote((n) => ({ ...n, [provider]: r.note }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setTesting((t) => ({ ...t, [provider]: false }));
    }
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[200px]">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
      </div>
    );
  }

  return (
    <div className="p-5 space-y-4">
      <div>
        <h2 className="text-lg font-semibold">API Key</h2>
        <p className="text-sm text-zinc-400">
          Masukkan API key (1 per baris). Jika banyak, aplikasi akan rotate <b>hanya saat key error</b> dan index terakhir
          akan diingat (tidak selalu mulai dari key pertama).
        </p>
      </div>

      {saved && (
        <div className="rounded-lg border border-emerald-700/50 bg-emerald-900/20 p-3 text-sm text-emerald-200">
          API Key tersimpan.
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-red-700/50 bg-red-900/20 p-3 text-sm text-red-200">{error}</div>
      )}

      <div className="space-y-4">
        {PROVIDERS.map((p) => (
          <div key={p.key} className="rounded-xl border border-zinc-700 bg-zinc-900/30 p-4">
            <button
              onClick={() => setOpen((o) => ({ ...o, [p.key]: !o[p.key] }))}
              className="w-full flex items-start justify-between gap-3 text-left"
            >
              <div>
                <div className="text-sm font-medium text-zinc-200">{p.label}</div>
                <div className="text-xs text-zinc-500 mt-0.5">{p.hint}</div>
              </div>
              <div className="mt-0.5 text-zinc-400">{open[p.key] ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}</div>
            </button>

            {open[p.key] && (
              <>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onTest(p.key);
                    }}
                    disabled={!!testing[p.key]}
                    className="text-xs px-3 py-1.5 rounded-md border border-zinc-600 bg-zinc-800/60 hover:bg-zinc-800 text-zinc-200 disabled:opacity-60 inline-flex items-center gap-2"
                  >
                    {testing[p.key] ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <RefreshCw className="w-3.5 h-3.5" />
                    )}
                    Test
                  </button>
                  <label className="text-xs text-zinc-400 flex items-center gap-2 select-none">
                    <input
                      type="checkbox"
                      checked={!!rotate[p.key]}
                      onChange={(e) => {
                        setRotate((r) => ({ ...r, [p.key]: e.target.checked }));
                        setDirty(true);
                        setSaved(false);
                      }}
                      className="rounded border-zinc-600 bg-zinc-800 text-cyan-500 focus:ring-cyan-500"
                    />
                    Rotate on error
                  </label>
                </div>

                <textarea
                  value={form[p.key]}
                  onChange={(e) => {
                    setForm((f) => ({ ...f, [p.key]: e.target.value }));
                    setDirty(true);
                    setSaved(false);
                  }}
                  placeholder="tempel key di sini...\n1 key per baris"
                  className="mt-3 w-full min-h-[110px] rounded-lg bg-zinc-950/40 border border-zinc-700 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                />

                {(testNote[p.key] || testResults[p.key]) && (
                  <div className="mt-3 text-xs">
                    {testNote[p.key] && <div className="text-zinc-500">{testNote[p.key]}</div>}
                    {!!(testResults[p.key] || []).length && (
                      <div className="mt-2 space-y-1">
                        {(testResults[p.key] || []).map((r, idx) => (
                          <div
                            key={`${r.key}-${idx}`}
                            className="flex items-center justify-between gap-2 rounded-md border border-zinc-700 bg-zinc-950/30 px-2 py-1"
                          >
                            <span className="font-mono text-zinc-300">{r.key}</span>
                            <span
                              className={
                                r.status === "ok"
                                  ? "text-emerald-300"
                                  : r.status === "saved"
                                  ? "text-zinc-400"
                                  : "text-red-300"
                              }
                              title={r.detail || ""}
                            >
                              {r.status === "ok" ? "OK" : r.status === "saved" ? "SAVED" : "ERROR"}
                            </span>
                          </div>
                        ))}
                        {(testResults[p.key] || []).some((r) => r.status === "error" && r.detail) && (
                          <div className="text-zinc-500 mt-1">Hover status “ERROR” untuk melihat ringkasan error.</div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        ))}
      </div>

      <div className="flex items-center justify-end gap-3 pt-2">
        <button
          onClick={onSave}
          disabled={saving || !dirty}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black font-medium transition-colors disabled:opacity-60"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Simpan API Key
        </button>
      </div>
    </div>
  );
}

