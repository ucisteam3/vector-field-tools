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
  if (!res.ok) throw new Error(await res.text());
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
export function playClipUrl(projectId: string, clipFilename: string): string {
  return `/stream-clip?project=${encodeURIComponent(projectId)}&file=${encodeURIComponent(clipFilename)}`;
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

/** Fetch preview (9:16) as blob URL for inline playback. */
export async function fetchPreviewAsBlobUrl(
  projectId: string,
  clipIndex: number
): Promise<string> {
  const url = previewClipUrl(projectId, clipIndex);
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
