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
              className={`rounded-xl bg-black overflow-hidden max-w-md mx-auto ${
                exportSettings.export_mode === "face_tracking" ? "aspect-[9/16]" : "aspect-video"
              }`}
            >
              {isAnalyzing ? (
                <div className="w-full h-full flex flex-col items-center justify-center gap-4 text-zinc-400">
                  <Loader2 className="w-16 h-16 animate-spin text-cyan-400" />
                  <p>{status?.progress || "Analyzing..."}</p>
                </div>
              ) : project.video_path ? (
                <video ref={videoRef} src={videoUrl(id)} controls className="w-full h-full object-cover" />
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

          <div className="w-80 flex-shrink-0 flex flex-col">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-cyan-400" /> Viral clips ({clips.length})
            </h2>
            <div className="flex-1 overflow-y-auto space-y-3 pr-2">
              {isAnalyzing && (
                <p className="text-zinc-500 text-sm">Clips will appear when analysis is complete.</p>
              )}
              {!isAnalyzing &&
                clips.map((clip, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="rounded-xl border border-white/10 bg-white/5 p-4 hover:bg-white/10 transition-colors"
                  >
                    <h3 className="font-medium text-sm line-clamp-2 mb-2">
                      <span className="text-amber-400">🔥</span> {clip.title}
                    </h3>
                    <div className="flex items-center gap-2 text-xs text-zinc-500 mb-3">
                      <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-400">score {clip.score}</span>
                      <span>|</span>
                      <span>{formatTime(clip.duration)}</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => previewClip(i)}
                        title="Preview in main video"
                        className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-zinc-700/50 hover:bg-zinc-600/50 text-zinc-300 text-sm"
                      >
                        <Play className="w-4 h-4" /> Preview
                      </button>
                      {clip.clip_path ? (
                        <>
                          <button
                            onClick={() => playClip(clip, i)}
                            className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 text-sm"
                          >
                            <Play className="w-4 h-4" /> Play
                          </button>
                          <a
                            href={clipUrl(id, clip.clip_path.replace("clips/", ""))}
                            download
                            className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors text-sm"
                          >
                            <Download className="w-4 h-4" /> Download
                          </a>
                        </>
                      ) : (
                        <button
                          onClick={() => handleDownloadExtract(i, clip.title)}
                          disabled={downloading.has(i)}
                          className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors text-sm disabled:opacity-50"
                        >
                          {downloading.has(i) ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <><Download className="w-4 h-4" /> Download</>
                          )}
                        </button>
                      )}
                      <button
                        onClick={() => handleExportWithSettings(i)}
                        disabled={exporting.has(i)}
                        className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 transition-colors text-sm disabled:opacity-50"
                      >
                        {exporting.has(i) ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <><Settings2 className="w-4 h-4" /> Export</>
                        )}
                      </button>
                    </div>
                  </motion.div>
                ))}
            </div>
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
