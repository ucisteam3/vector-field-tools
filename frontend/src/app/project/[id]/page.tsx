"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Play, Download, Loader2, Sparkles } from "lucide-react";
import {
  getProject,
  getProjectStatus,
  playClipUrl,
  thumbnailClipUrl,
  fetchPreviewAsBlobUrl,
  exportClipWithSettings,
  type Project,
} from "@/lib/api";
import { useAppSettings } from "@/lib/settings-store";
import { EXPORT_MODE_OPTIONS } from "@/lib/export-settings";
import AppSidebar from "@/components/AppSidebar";

export default function ProjectPage() {
  const params = useParams();
  const id = params?.id as string;
  const [exportSettings, setExportSettings] = useAppSettings();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<{ status: string; progress?: string } | null>(null);
  const [playingClip, setPlayingClip] = useState<number | null>(null);
  const [blobCache, setBlobCache] = useState<Record<number, string>>({});
  const [downloading, setDownloading] = useState<Set<number>>(new Set());
  const blobCacheRef = useRef<Record<number, string>>({});
  blobCacheRef.current = blobCache;

  const loadProject = async () => {
    try {
      const p = await getProject(id);
      setProject(p);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) loadProject();
  }, [id]);

  useEffect(() => {
    if (!project || project.status !== "analyzing") return;
    const interval = setInterval(async () => {
      const s = await getProjectStatus(id);
      setStatus(s);
      if (s.status === "ready" || s.status === "error") {
        clearInterval(interval);
        loadProject();
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [id, project?.status]);

  useEffect(() => () => {
    Object.values(blobCacheRef.current).forEach((url) => URL.revokeObjectURL(url));
  }, []);

  const preloadClip = useCallback(
    (index: number) => {
      if (!project?.clips?.[index] || blobCache[index]) return;
      fetchPreviewAsBlobUrl(id, index).then((url) => {
        setBlobCache((prev) => {
          if (prev[index]) {
            URL.revokeObjectURL(url);
            return prev;
          }
          return { ...prev, [index]: url };
        });
      }).catch(() => {});
    },
    [id, project?.clips, blobCache]
  );

  const playClip = async (index: number) => {
    const clip = project?.clips?.[index];
    if (!clip) return;
    setPlayingClip(index);
    if (blobCache[index]) return;
    try {
      const blobUrl = await fetchPreviewAsBlobUrl(id, index);
      setBlobCache((prev) => ({ ...prev, [index]: blobUrl }));
    } catch (e) {
      console.error(e);
    }
  };

  const handleDownload = async (e: React.MouseEvent, index: number) => {
    e.preventDefault();
    e.stopPropagation();
    const clip = project?.clips?.[index];
    if (!clip) return;
    setDownloading((s) => new Set(s).add(index));
    try {
      const { clip_path } = await exportClipWithSettings(id, index, exportSettings);
      const filename = (clip_path || "").replace("clips/", "");
      if (!filename) throw new Error("Export gagal");
      const downloadName = (clip.title || `clip_${index + 1}`).replace(/[^a-zA-Z0-9 _-]/g, "").trim().slice(0, 50) + ".mp4";
      const url = playClipUrl(id, filename, true);
      const a = document.createElement("a");
      a.href = url;
      a.download = downloadName;
      a.style.display = "none";
      document.body.appendChild(a);
      a.click();
      setTimeout(() => document.body.removeChild(a), 100);
      loadProject();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Export gagal. Cek konsol untuk detail.");
    } finally {
      setDownloading((s) => {
        const n = new Set(s);
        n.delete(index);
        return n;
      });
    }
  };

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  if (loading && !project) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-12 h-12 animate-spin text-cyan-400" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-zinc-400">Project not found</p>
        <Link href="/" className="text-cyan-400 hover:underline">Back to Dashboard</Link>
      </div>
    );
  }

  const isAnalyzing = project.status === "analyzing";
  const clips = project.clips ?? [];

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0c10]">
      <AppSidebar />
      <main className="flex-1 ml-64 p-6 flex flex-col min-h-0 overflow-auto">
        <div className="flex flex-col flex-1 min-h-0">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-cyan-400" /> Viral clips ({clips.length})
            </h2>
            {!isAnalyzing && (
              <div className="flex items-center gap-2">
                <label className="text-xs text-zinc-500">Mode</label>
                <select
                  value={exportSettings.export_mode}
                  onChange={(e) => setExportSettings((s) => ({ ...s, export_mode: e.target.value as typeof s.export_mode }))}
                  className="bg-zinc-800 border border-zinc-600 rounded-lg px-3 py-2 text-sm text-white focus:ring-2 focus:ring-cyan-500/50 outline-none"
                >
                  {EXPORT_MODE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
          {isAnalyzing ? (
            <div className="flex items-center gap-3 text-zinc-500">
              <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
              <span>{status?.progress || "Analyzing..."}</span>
            </div>
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-8 gap-3 overflow-y-auto pb-4">
              {clips.map((clip, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="rounded-lg border border-white/10 bg-white/5 overflow-hidden hover:bg-white/10 transition-colors group"
                  onMouseEnter={() => preloadClip(i)}
                >
                  <div className="relative aspect-[9/16] bg-zinc-900">
                    {playingClip === i && blobCache[i] ? (
                      <video
                        src={blobCache[i]}
                        autoPlay
                        controls
                        playsInline
                        className="w-full h-full object-cover"
                        onEnded={() => setPlayingClip(null)}
                      />
                    ) : playingClip === i ? (
                      <div className="absolute inset-0 flex items-center justify-center bg-black/60">
                        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
                      </div>
                    ) : (
                      <>
                        <div className="absolute inset-0 bg-gradient-to-br from-zinc-800 to-zinc-900 flex items-center justify-center">
                          <Play className="w-10 h-10 text-white/30" />
                        </div>
                        <img
                          src={thumbnailClipUrl(id, i)}
                          alt=""
                          className="absolute inset-0 w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = "none";
                          }}
                        />
                        <div
                          className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                          onClick={() => playClip(i)}
                        >
                          <div className="w-14 h-14 rounded-full bg-cyan-500/80 flex items-center justify-center">
                            <Play className="w-7 h-7 text-white ml-1" fill="currentColor" />
                          </div>
                        </div>
                        <div className="absolute bottom-0.5 right-0.5 px-1 py-0.5 rounded bg-black/70 text-[10px] text-white">
                          {formatTime(clip.duration)}
                        </div>
                        <div className="absolute top-0.5 left-0.5 px-1 py-0.5 rounded bg-cyan-500/80 text-[10px] font-medium text-black">
                          {clip.score}
                        </div>
                      </>
                    )}
                  </div>
                  <div className="p-1.5">
                    <h3 className="text-[11px] font-medium line-clamp-2 mb-1 text-zinc-200">{clip.title}</h3>
                    <div className="flex flex-wrap gap-0.5">
                      <button
                        onClick={() => playClip(i)}
                        className="flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 text-[10px]"
                      >
                        <Play className="w-2.5 h-2.5" /> Play
                      </button>
                      <button
                        type="button"
                        onClick={(e) => handleDownload(e, i)}
                        disabled={downloading.has(i)}
                        className="flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-white/10 hover:bg-white/20 text-[10px] disabled:opacity-50"
                      >
                        {downloading.has(i) ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <Download className="w-2.5 h-2.5" />} Export
                      </button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {project.status === "error" && (
          <div className="mt-4 p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">
            {project.error}
          </div>
        )}
      </main>
    </div>
  );
}
