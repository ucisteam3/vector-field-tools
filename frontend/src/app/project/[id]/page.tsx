"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Film, Play, Download, Loader2, Sparkles, Settings2 } from "lucide-react";
import { getProject, getProjectStatus, exportClipWithSettings, videoUrl, clipUrl, downloadClipExtract, type Project, type Clip } from "@/lib/api";
import AppSidebar from "@/components/AppSidebar";
import { useAppSettings } from "@/lib/settings-store";

export default function ProjectPage() {
  const params = useParams();
  const id = params?.id as string;
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<{ status: string; progress?: string } | null>(null);
  const [playingClip, setPlayingClip] = useState<number | null>(null);
  const [exporting, setExporting] = useState<Set<number>>(new Set());
  const [downloading, setDownloading] = useState<Set<number>>(new Set());
  const previewEndRef = useRef<{ index: number; end: number } | null>(null);
  const [exportSettings] = useAppSettings();
  const videoRef = useRef<HTMLVideoElement>(null);

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

  const seekTo = (start: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = start;
      videoRef.current.play();
    }
  };

  const playClip = (clip: Clip, index: number) => {
    if (clip.clip_path) setPlayingClip(index);
    else previewClip(index);
  };

  const previewClip = (index: number) => {
    const clip = project?.clips?.[index];
    if (!clip || !videoRef.current) return;
    videoRef.current.currentTime = clip.start;
    videoRef.current.play();
    previewEndRef.current = { index, end: clip.end };
  };

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !previewEndRef.current) return;
    const handleTimeUpdate = () => {
      const p = previewEndRef.current;
      if (p && video.currentTime >= p.end) {
        video.pause();
        previewEndRef.current = null;
      }
    };
    video.addEventListener("timeupdate", handleTimeUpdate);
    return () => {
      video.removeEventListener("timeupdate", handleTimeUpdate);
    };
  }, [project?.clips]);

  const handleDownloadExtract = async (index: number, title?: string) => {
    setDownloading((prev) => new Set(prev).add(index));
    try {
      const safe = (title ?? `clip_${index + 1}`).replace(/[^a-zA-Z0-9 _-]/g, "").trim() || `clip_${index + 1}`;
      await downloadClipExtract(id, index, `${safe}.mp4`);
    } catch (e) {
      alert(String(e));
    } finally {
      setDownloading((prev) => {
        const next = new Set(prev);
        next.delete(index);
        return next;
      });
    }
  };

  const handleExportWithSettings = async (index: number) => {
    setExporting((prev) => new Set(prev).add(index));
    try {
      const { clip_path } = await exportClipWithSettings(id, index, exportSettings);
      setProject((p) => {
        if (!p) return p;
        const clips = [...(p.clips || [])];
        if (clips[index]) clips[index] = { ...clips[index], clip_path };
        return { ...p, clips };
      });
    } catch (e) {
      alert(String(e));
    } finally {
      setExporting((prev) => {
        const next = new Set(prev);
        next.delete(index);
        return next;
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
  const duration = clips.length > 0 ? Math.max(...clips.map((c) => c.end)) : 0;

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0c10]">
      <AppSidebar />
      <main className="flex-1 ml-64 p-6 flex flex-col min-h-0">
        <div className="flex gap-4 flex-1 min-h-0 overflow-x-auto overflow-y-hidden min-w-0">
          <div className="flex-1 flex flex-col min-w-0 relative">
            <div
              className={`rounded-xl bg-black overflow-hidden mx-auto shrink-0 ${
                exportSettings.export_mode === "face_tracking" ? "aspect-[9/16] max-w-sm" : "aspect-video max-w-4xl w-full"
              }`}
            >
              {isAnalyzing ? (
                <div className="w-full h-full flex flex-col items-center justify-center gap-4 text-zinc-400">
                  <Loader2 className="w-16 h-16 animate-spin text-cyan-400" />
                  <p>{status?.progress || "Analyzing..."}</p>
                </div>
              ) : project.video_path ? (
                exportSettings.export_mode === "landscape_fit" ? (
                  <div className="relative w-full h-full">
                    <video src={videoUrl(id)} className="absolute inset-0 w-full h-full object-cover blur-2xl scale-110 opacity-50" aria-hidden muted />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <video ref={videoRef} src={videoUrl(id)} controls className="max-h-full max-w-full object-contain rounded shadow-2xl" />
                    </div>
                  </div>
                ) : (
                  <video ref={videoRef} src={videoUrl(id)} controls className="w-full h-full object-cover" />
                )
              ) : (
                <div className="w-full h-full flex items-center justify-center text-zinc-500">No video</div>
              )}
            </div>

            {!isAnalyzing && clips.length > 0 && duration > 0 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-4">
                <p className="text-sm text-zinc-500 mb-2">Timeline</p>
                <div className="h-12 bg-white/5 rounded-lg overflow-hidden flex relative">
                  {clips.map((clip, i) => (
                    <motion.div
                      key={i}
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: 1 }}
                      transition={{ delay: i * 0.03 }}
                      style={{
                        position: "absolute",
                        left: `${(clip.start / duration) * 100}%`,
                        width: `${(clip.duration / duration) * 100}%`,
                        minWidth: 4,
                      }}
                      className="bg-cyan-500/60 hover:bg-cyan-500 cursor-pointer transition-colors"
                      onClick={() => previewClip(i)}
                      title={clip.title}
                    />
                  ))}
                </div>
              </motion.div>
            )}

            <AnimatePresence>
              {playingClip !== null && clips[playingClip]?.clip_path && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="absolute inset-0 z-10 flex items-center justify-center bg-black/90 rounded-xl"
                  onClick={() => setPlayingClip(null)}
                >
                  <video
                    key={playingClip}
                    src={clipUrl(id, clips[playingClip].clip_path!.replace("clips/", ""))}
                    autoPlay
                    controls
                    onClick={(e) => e.stopPropagation()}
                    className="max-w-full max-h-full"
                    onEnded={() => setPlayingClip(null)}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-cyan-400" /> Viral clips ({clips.length})
            </h2>
            {isAnalyzing ? (
              <p className="text-zinc-500 text-sm">Clips will appear when analysis is complete.</p>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 overflow-y-auto pb-4">
                {clips.map((clip, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className="rounded-xl border border-white/10 bg-white/5 overflow-hidden hover:bg-white/10 transition-colors group"
                  >
                    <div
                      className={`relative cursor-pointer ${
                        exportSettings.export_mode === "face_tracking" ? "aspect-[9/16]" : "aspect-video"
                      } bg-zinc-900`}
                      onClick={() => playClip(clip, i)}
                    >
                      {clip.clip_path ? (
                        <video
                          src={clipUrl(id, clip.clip_path.replace("clips/", ""))}
                          className="w-full h-full object-cover"
                          muted
                          preload="metadata"
                          playsInline
                        />
                      ) : (
                        <video
                          src={videoUrl(id)}
                          className="w-full h-full object-cover"
                          muted
                          preload="metadata"
                          playsInline
                          onLoadedMetadata={(e) => { (e.target as HTMLVideoElement).currentTime = clip.start; }}
                        />
                      )}
                      <div className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity">
                        <div className="w-14 h-14 rounded-full bg-cyan-500/80 flex items-center justify-center">
                          <Play className="w-7 h-7 text-white ml-1" fill="currentColor" />
                        </div>
                      </div>
                      <div className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/70 text-xs text-white">
                        {formatTime(clip.duration)}
                      </div>
                      <div className="absolute top-1 left-1 px-1.5 py-0.5 rounded bg-cyan-500/80 text-xs font-medium text-black">
                        {clip.score}
                      </div>
                    </div>
                    <div className="p-2">
                      <h3 className="text-sm font-medium line-clamp-2 mb-2 text-zinc-200">{clip.title}</h3>
                      <div className="flex flex-wrap gap-1">
                        <button
                          onClick={(e) => { e.stopPropagation(); playClip(clip, i); }}
                          className="flex items-center gap-1 px-2 py-1 rounded bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 text-xs"
                        >
                          <Play className="w-3 h-3" /> Play
                        </button>
                        {clip.clip_path ? (
                          <a
                            href={clipUrl(id, clip.clip_path.replace("clips/", ""))}
                            download
                            onClick={(e) => e.stopPropagation()}
                            className="flex items-center gap-1 px-2 py-1 rounded bg-white/10 hover:bg-white/20 text-xs"
                          >
                            <Download className="w-3 h-3" />
                          </a>
                        ) : (
                          <button
                            onClick={(e) => { e.stopPropagation(); handleDownloadExtract(i, clip.title); }}
                            disabled={downloading.has(i)}
                            className="flex items-center gap-1 px-2 py-1 rounded bg-white/10 hover:bg-white/20 text-xs disabled:opacity-50"
                          >
                            {downloading.has(i) ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
                          </button>
                        )}
                        <button
                          onClick={(e) => { e.stopPropagation(); handleExportWithSettings(i); }}
                          disabled={exporting.has(i)}
                          className="flex items-center gap-1 px-2 py-1 rounded bg-white/10 hover:bg-white/20 text-xs disabled:opacity-50"
                        >
                          {exporting.has(i) ? <Loader2 className="w-3 h-3 animate-spin" /> : <Settings2 className="w-3 h-3" />}
                        </button>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>

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
