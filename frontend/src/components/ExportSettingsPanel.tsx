"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Settings, ChevronDown, ChevronUp, Upload } from "lucide-react";
import {
  type ExportSettings,
  DEFAULT_EXPORT_SETTINGS,
  EXPORT_MODE_OPTIONS,
} from "@/lib/export-settings";
import { getFonts, uploadBgm, uploadWatermarkImage } from "@/lib/api";

type Props = {
  settings: ExportSettings;
  onChange: (s: ExportSettings) => void;
  /** When true, renders as standalone block for /settings page (no aside wrapper) */
  standalone?: boolean;
};

function Section({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-b border-zinc-700/50 last:border-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between py-3 text-sm font-medium text-zinc-300 hover:text-white transition-colors"
      >
        {title}
        {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="pb-4 space-y-3">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Checkbox({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer text-sm text-zinc-400">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="rounded border-zinc-600 bg-zinc-800 text-cyan-500 focus:ring-cyan-500"
      />
      {label}
    </label>
  );
}

export default function ExportSettingsPanel({ settings, onChange, standalone = false }: Props) {
  const [fonts, setFonts] = useState<string[]>(["Arial"]);
  const [bgmUploading, setBgmUploading] = useState(false);
  const [watermarkUploading, setWatermarkUploading] = useState(false);

  useEffect(() => {
    getFonts().then(setFonts).catch(() => {});
  }, []);

  const update = (patch: Partial<ExportSettings>) => {
    onChange({ ...settings, ...patch });
  };

  const handleBgmUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBgmUploading(true);
    try {
      const { path } = await uploadBgm(file);
      update({ bgm_file_path: path, bgm_enabled: true });
    } catch (err) {
      alert(String(err));
    } finally {
      setBgmUploading(false);
      e.target.value = "";
    }
  };

  const content = (
    <div className={standalone ? "p-4 space-y-0" : "flex-1 overflow-y-auto p-4 space-y-0"}>
        {/* Display/Preview Mode */}
        <Section title="Mode Tampilan (Preview & Export)" defaultOpen>
          <div>
            <label className="block text-xs text-zinc-500 mb-1">Mode</label>
            <select
              value={settings.export_mode}
              onChange={(e) => update({ export_mode: e.target.value as ExportSettings["export_mode"] })}
              className="w-full rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            >
              {EXPORT_MODE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </Section>

        {/* Video Effects */}
        <Section title="Video Effects" defaultOpen>
          <Checkbox
            label="Dynamic Zoom"
            checked={settings.dynamic_zoom_enabled}
            onChange={(v) => update({ dynamic_zoom_enabled: v })}
          />
          <Checkbox
            label="Flip Video"
            checked={settings.video_flip_enabled}
            onChange={(v) => update({ video_flip_enabled: v })}
          />
          <Checkbox
            label="Audio Pitch"
            checked={settings.audio_pitch_enabled}
            onChange={(v) => update({ audio_pitch_enabled: v })}
          />
        </Section>

        {/* Subtitle Settings */}
        <Section title="Subtitle Settings" defaultOpen>
          <Checkbox
            label="Enable Subtitle"
            checked={settings.subtitle_enabled}
            onChange={(v) => update({ subtitle_enabled: v })}
          />
          <div className="space-y-2 pt-1">
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Font</label>
              <select
                value={settings.subtitle_font}
                onChange={(e) => update({ subtitle_font: e.target.value })}
                className="w-full rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white"
              >
                {fonts.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Font Size</label>
              <input
                type="number"
                min={8}
                max={96}
                value={settings.subtitle_fontsize}
                onChange={(e) => update({ subtitle_fontsize: +e.target.value || 24 })}
                className="w-full rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white"
              />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Text</label>
                <input
                  type="color"
                  value={settings.subtitle_text_color}
                  onChange={(e) => update({ subtitle_text_color: e.target.value })}
                  className="w-full h-8 rounded border border-zinc-600 cursor-pointer"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Outline</label>
                <input
                  type="color"
                  value={settings.subtitle_outline_color}
                  onChange={(e) => update({ subtitle_outline_color: e.target.value })}
                  className="w-full h-8 rounded border border-zinc-600 cursor-pointer"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Highlight</label>
                <input
                  type="color"
                  value={settings.subtitle_highlight_color}
                  onChange={(e) => update({ subtitle_highlight_color: e.target.value })}
                  className="w-full h-8 rounded border border-zinc-600 cursor-pointer"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Outline Width</label>
              <input
                type="number"
                min={0}
                max={5}
                value={settings.subtitle_outline_width ?? 2}
                onChange={(e) => update({ subtitle_outline_width: +e.target.value || 2 })}
                className="w-full rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Vertical Position</label>
              <input
                type="number"
                min={0}
                max={1000}
                value={settings.subtitle_position_y}
                onChange={(e) => update({ subtitle_position_y: +e.target.value || 50 })}
                className="w-full rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white"
              />
            </div>
          </div>
        </Section>

        {/* Watermark Settings */}
        <Section title="Watermark Settings">
          <Checkbox
            label="Enable Watermark"
            checked={settings.watermark_enabled}
            onChange={(v) => update({ watermark_enabled: v })}
          />
          <div>
            <label className="block text-xs text-zinc-500 mb-1">Type</label>
            <select
              value={settings.watermark_type}
              onChange={(e) => update({ watermark_type: e.target.value as "text" | "image" })}
              className="w-full rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white"
            >
              <option value="text">Text watermark</option>
              <option value="image">Image watermark</option>
            </select>
          </div>
          {settings.watermark_type === "text" && (
            <>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Text</label>
                <input
                  type="text"
                  value={settings.watermark_text}
                  onChange={(e) => update({ watermark_text: e.target.value })}
                  placeholder="Watermark text"
                  className="w-full rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Font</label>
                <select
                  value={settings.watermark_font}
                  onChange={(e) => update({ watermark_font: e.target.value })}
                  className="w-full rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white"
                >
                  {fonts.map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Size</label>
                <input
                  type="number"
                  min={8}
                  max={96}
                  value={settings.watermark_size}
                  onChange={(e) => update({ watermark_size: +e.target.value || 48 })}
                  className="w-full rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Opacity (0-100)</label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={settings.watermark_opacity}
                  onChange={(e) => update({ watermark_opacity: +e.target.value || 80 })}
                  className="w-full rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-zinc-500 mb-1">Position X</label>
                  <input
                    type="number"
                    value={settings.watermark_pos_x}
                    onChange={(e) => update({ watermark_pos_x: +e.target.value || 50 })}
                    className="w-full rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs text-zinc-500 mb-1">Position Y</label>
                  <input
                    type="number"
                    value={settings.watermark_pos_y}
                    onChange={(e) => update({ watermark_pos_y: +e.target.value || 50 })}
                    className="w-full rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white"
                  />
                </div>
              </div>
            </>
          )}
          {settings.watermark_type === "image" && (
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Upload image</label>
              <label className="flex items-center gap-2 px-3 py-2 rounded-lg border border-dashed border-zinc-600 hover:border-cyan-500/50 cursor-pointer transition-colors">
                <Upload className="w-4 h-4 text-zinc-500" />
                <span className="text-sm text-zinc-400">
                  {watermarkUploading ? "Uploading..." : settings.watermark_image_path ? "Replace image" : "Choose PNG/JPG"}
                </span>
                <input
                  type="file"
                  accept=".png,.jpg,.jpeg,.webp,.gif"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    setWatermarkUploading(true);
                    try {
                      const { path } = await uploadWatermarkImage(file);
                      update({ watermark_image_path: path });
                    } catch (err) {
                      alert(String(err));
                    } finally {
                      setWatermarkUploading(false);
                      e.target.value = "";
                    }
                  }}
                  disabled={watermarkUploading}
                  className="hidden"
                />
              </label>
              {settings.watermark_image_path && (
                <p className="mt-1 text-xs text-cyan-400 truncate" title={settings.watermark_image_path}>
                  OK {settings.watermark_image_path.split("/").pop()}
                </p>
              )}
              <div className="mt-2 grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-zinc-500 mb-1">Scale %</label>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={settings.watermark_image_scale ?? 50}
                    onChange={(e) => update({ watermark_image_scale: +e.target.value || 50 })}
                    className="w-full rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs text-zinc-500 mb-1">Opacity</label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={settings.watermark_image_opacity ?? 100}
                    onChange={(e) => update({ watermark_image_opacity: +e.target.value || 100 })}
                    className="w-full rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-white"
                  />
                </div>
              </div>
            </div>
          )}
        </Section>

        {/* BGM Settings */}
        <Section title="BGM Settings">
          <Checkbox
            label="Enable background music"
            checked={settings.bgm_enabled}
            onChange={(v) => update({ bgm_enabled: v })}
          />
          <div>
            <label className="block text-xs text-zinc-500 mb-1">Upload audio file</label>
            <label className="flex items-center gap-2 px-3 py-2 rounded-lg border border-dashed border-zinc-600 hover:border-cyan-500/50 cursor-pointer transition-colors">
              <Upload className="w-4 h-4 text-zinc-500" />
              <span className="text-sm text-zinc-400">
                {bgmUploading ? "Uploading..." : settings.bgm_file_path ? "Replace file" : "Choose MP3/WAV"}
              </span>
              <input
                type="file"
                accept=".mp3,.wav,.m4a,.aac,.ogg"
                onChange={handleBgmUpload}
                disabled={bgmUploading}
                className="hidden"
              />
            </label>
            {settings.bgm_file_path && (
              <p className="mt-1 text-xs text-cyan-400 truncate" title={settings.bgm_file_path}>
                OK {settings.bgm_file_path.split("/").pop()}
              </p>
            )}
          </div>
        </Section>

        <button
          onClick={() => onChange({ ...DEFAULT_EXPORT_SETTINGS })}
          className="mt-4 w-full py-2 rounded-lg border border-zinc-600 text-zinc-400 hover:text-white hover:border-zinc-500 text-sm transition-colors"
        >
          Reset to defaults
        </button>
      </div>
  );

  if (standalone) {
    return (
      <div className="flex flex-col">
        <div className="p-4 border-b border-zinc-700">
          <h2 className="text-lg font-semibold flex items-center gap-2 text-cyan-400">
            <Settings className="w-5 h-5" />
            Pengaturan Tampilan
          </h2>
        </div>
        {content}
      </div>
    );
  }
  return (
    <aside className="w-80 flex-shrink-0 sticky right-0 top-0 border-l border-zinc-700 bg-zinc-900/50 flex flex-col self-stretch shadow-[-4px_0_20px_rgba(0,0,0,0.3)]">
      <div className="p-4 border-b border-zinc-700">
        <h2 className="text-lg font-semibold flex items-center gap-2 text-cyan-400">
          <Settings className="w-5 h-5" />
          Export Settings
        </h2>
      </div>
      {content}
    </aside>
  );
}
