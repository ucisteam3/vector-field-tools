"use client";

import { useState, useEffect, useCallback } from "react";
import {
  type ExportSettings,
  DEFAULT_EXPORT_SETTINGS,
} from "./export-settings";

const STORAGE_KEY = "ai-clipper-app-settings";
const VALID_MODES = ["landscape_fit", "face_tracking", "podcast_smart"] as const;

function loadFromStorage(): ExportSettings {
  if (typeof window === "undefined") return { ...DEFAULT_EXPORT_SETTINGS };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_EXPORT_SETTINGS };
    const parsed = JSON.parse(raw) as Partial<ExportSettings>;
    const merged = { ...DEFAULT_EXPORT_SETTINGS, ...parsed };
    if (!VALID_MODES.includes(merged.export_mode as (typeof VALID_MODES)[number])) {
      merged.export_mode = DEFAULT_EXPORT_SETTINGS.export_mode;
    }
    return merged;
  } catch {
    return { ...DEFAULT_EXPORT_SETTINGS };
  }
}

function saveToStorage(settings: ExportSettings) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    /* ignore */
  }
}

export function useAppSettings() {
  const [settings, setSettingsState] = useState<ExportSettings>(DEFAULT_EXPORT_SETTINGS);

  useEffect(() => {
    setSettingsState(loadFromStorage());
  }, []);

  const setSettings = useCallback((s: ExportSettings | ((prev: ExportSettings) => ExportSettings)) => {
    setSettingsState((prev) => {
      const next = typeof s === "function" ? s(prev) : s;
      saveToStorage(next);
      return next;
    });
  }, []);

  return [settings, setSettings] as const;
}
