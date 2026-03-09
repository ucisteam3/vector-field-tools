const API = "/api";

export async function analyzeVideo(
  youtubeUrl: string,
  exportSettings?: Record<string, unknown>
): Promise<{ project_id: string; title: string }> {
  const res = await fetch(`${API}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      youtube_url: youtubeUrl,
      export_settings: exportSettings ?? undefined,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteProject(projectId: string): Promise<void> {
  const res = await fetch(`${API}/project/${projectId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text());
}

export async function retryProject(projectId: string): Promise<void> {
  const res = await fetch(`${API}/project/${projectId}/retry`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
}

export async function getProjects(): Promise<Project[]> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const res = await fetch(`${API}/projects`, { signal: controller.signal });
    clearTimeout(timeout);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (e) {
    clearTimeout(timeout);
    if ((e as Error).name === "AbortError") {
      throw new Error("Server tidak merespon. Pastikan backend berjalan: python server.py");
    }
    throw e;
  }
}

export async function getProject(id: string): Promise<Project> {
  const res = await fetch(`${API}/project/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getProjectStatus(id: string): Promise<{
  status: string;
  progress?: string;
  error?: string;
  eta_seconds?: number;
  eta_message?: string;
}> {
  const res = await fetch(`${API}/project/${id}/status`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function exportClip(projectId: string, clipIndex: number): Promise<{ clip_path: string }> {
  const res = await fetch(`${API}/project/${projectId}/export/${clipIndex}`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export type ExportSettingsInput = Record<string, unknown>;

/** Start async export, returns job_id. Poll getExportStatus for progress. */
export async function exportClipAsync(
  projectId: string,
  clipId: number,
  settings: ExportSettingsInput | null
): Promise<{ job_id: string }> {
  const res = await fetch(`${API}/export_clip_async`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: projectId,
      clip_id: clipId,
      settings: settings ?? undefined,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    try {
      const j = JSON.parse(text);
      throw new Error(typeof j?.detail === "string" ? j.detail : text);
    } catch (e) {
      if (e instanceof Error && e.message.length > 0 && !/not valid JSON|Unexpected token/i.test(e.message))
        throw e;
      throw new Error(text || `Export gagal (${res.status})`);
    }
  }
  return res.json();
}

export type ExportStatus = {
  progress: number;
  message: string;
  status: "running" | "done" | "error";
  clip_path?: string;
  error?: string;
  logs?: string[];
};

export async function getExportStatus(jobId: string): Promise<ExportStatus> {
  const res = await fetch(`${API}/export_clip_status?job_id=${encodeURIComponent(jobId)}`);
  if (!res.ok) throw new Error("Status tidak ditemukan");
  return res.json();
}

export async function exportClipWithSettings(
  projectId: string,
  clipId: number,
  settings: ExportSettingsInput | null
): Promise<{ clip_path: string }> {
  const res = await fetch(`${API}/export_clip`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: projectId,
      clip_id: clipId,
      settings: settings ?? undefined,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    try {
      const j = JSON.parse(text);
      const d = j?.detail;
      throw new Error(typeof d === "string" ? d : text || `Error ${res.status}`);
    } catch (e) {
      if (e instanceof Error && e.message.length > 0 && !/not valid JSON|Unexpected token/i.test(e.message)) throw e;
      throw new Error(text || `Export gagal (${res.status})`);
    }
  }
  return res.json();
}

export async function uploadBgm(file: File): Promise<{ path: string; filename: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API}/upload_bgm`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function uploadWatermarkImage(file: File): Promise<{ path: string; filename: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API}/upload_watermark_image`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function uploadCookies(file: File): Promise<{ ok: boolean }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API}/upload_cookies`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getCookiesStatus(): Promise<{ exists: boolean; size_kb: number }> {
  const res = await fetch(`${API}/cookies_status`);
  if (!res.ok) return { exists: false, size_kb: 0 };
  return res.json();
}

export async function getFonts(): Promise<string[]> {
  const res = await fetch(`${API}/fonts`);
  if (!res.ok) return ["Arial", "Roboto-Bold", "Poppins-Bold"];
  return res.json();
}

export type ApiKeysPayload = {
  openai: string[];
  gemini: string[];
  anthropic: string[];
  llama: string[];
  deepseek: string[];
  groq: string[];
  rotate_on_error: Record<string, boolean>;
};

export async function getApiKeys(): Promise<ApiKeysPayload> {
  const res = await fetch(`${API}/settings/api_keys`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function saveApiKeys(payload: ApiKeysPayload): Promise<{ ok: boolean }> {
  const res = await fetch(`${API}/settings/api_keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export type ApiKeyTestResult = {
  key: string;
  status: "ok" | "error" | "saved";
  detail?: string;
};

export async function testApiKeys(provider: string, mode: "all" | "current" = "all"): Promise<{
  provider: string;
  results: ApiKeyTestResult[];
  note?: string;
}> {
  const res = await fetch(`${API}/settings/api_keys/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, mode }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export type Clip = {
  id?: number;
  start: number;
  end: number;
  duration: number;
  score: number;
  title: string;
  clip_path?: string | null;
};

export type Project = {
  project_id: string;
  title: string;
  youtube_url?: string | null;
  video_path: string | null;
  created_at: string;
  updated_at: string;
  clips: Clip[];
  status: string;
  error?: string | null;
};

export function videoUrl(projectId: string): string {
  return `${API}/video/${projectId}`;
}

export function clipUrl(projectId: string, clipFilename: string): string {
  return `${API}/clip/${projectId}/${clipFilename}`;
}

/** URL untuk Play - lewat proxy /stream-clip (bukan /api) agar tidak trigger IDM */
export function playClipUrl(projectId: string, clipFilename: string, forDownload = false): string {
  const base = `/stream-clip?project=${encodeURIComponent(projectId)}&file=${encodeURIComponent(clipFilename)}`;
  return forDownload ? `${base}&download=1` : base;
}

/**
 * Download clip segment via ffmpeg extraction.
 * Use for clips without clip_path (not yet exported).
 */
export function extractClipUrl(projectId: string, clipIndex: number): string {
  return `${API}/clip/${projectId}/extract/${clipIndex}`;
}

/** Thumbnail: single frame from clip (9:16). For card preview. */
export function thumbnailClipUrl(projectId: string, clipIndex: number): string {
  return `${API}/clip/${projectId}/thumbnail/${clipIndex}`;
}

/** Preview: 9:16 center crop, no effects. For Play button. */
export function previewClipUrl(projectId: string, clipIndex: number): string {
  return `${API}/clip/${projectId}/preview/${clipIndex}`;
}

/** URL untuk Play - lewat proxy /stream-preview (bukan /api) agar tidak trigger IDM. Cepat (extract -c copy). */
export function streamPreviewUrl(projectId: string, clipIndex: number): string {
  return `/stream-preview?project=${encodeURIComponent(projectId)}&index=${clipIndex}`;
}

/** Fetch preview via stream-preview proxy - hindari IDM, putar lebih cepat (extract). */
export async function fetchPreviewAsBlobUrl(
  projectId: string,
  clipIndex: number
): Promise<string> {
  const url = streamPreviewUrl(projectId, clipIndex);
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to load preview");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

/** Fetch extract as blob URL for inline playback (avoids IDM interception). */
export async function fetchExtractAsBlobUrl(
  projectId: string,
  clipIndex: number
): Promise<string> {
  const url = extractClipUrl(projectId, clipIndex);
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export async function downloadClipExtract(
  projectId: string,
  clipIndex: number,
  filename?: string
): Promise<void> {
  const url = extractClipUrl(projectId, clipIndex);
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition");
  let name = filename;
  if (!name && disposition) {
    const match = disposition.match(/filename="?([^";\n]+)"?/);
    if (match) name = match[1];
  }
  if (!name) name = `clip_${clipIndex + 1}.mp4`;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}
