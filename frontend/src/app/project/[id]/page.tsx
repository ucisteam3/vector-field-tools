"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Play, Download, Loader2, Sparkles } from "lucide-react";
import { getProject, getProjectStatus, clipUrl, type Project } from "@/lib/api";
import AppSidebar from "@/components/AppSidebar";

export default function ProjectPage() {
  const params = useParams();
  const id = params?.id as string;
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<{ status: string; progress?: string } | null>(null);
  const [playingClip, setPlayingClip] = useState<number | null>(null);
  const [blobCache, setBlobCache] = useState<Record<number, string>>({});
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

  const playClip = async (index: number) => {
    const clip = project?.clips?.[index];
    if (!clip?.clip_path) return;
    setPlayingClip(index);
    if (blobCache[index]) return;
    try {
      const url = clipUrl(id, clip.clip_path.replace("clips/", ""));
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to load");
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      setBlobCache((prev) => ({ ...prev, [index]: blobUrl }));
    } catch (e) {
      console.error(e);
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
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-cyan-400" /> Viral clips ({clips.length})
          </h2>
          {isAnalyzing ? (
            <div className="flex items-center gap-3 text-zinc-500">
              <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
              <span>{status?.progress || "Analyzing..."}</span>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4 overflow-y-auto pb-4">
              {clips.map((clip, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="rounded-xl border border-white/10 bg-white/5 overflow-hidden hover:bg-white/10 transition-colors group"
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
                        <Loader2 className="w-12 h-12 animate-spin text-cyan-400" />
                      </div>
                    ) : (
                      <>
                        {clip.clip_path ? (
                          <div className="w-full h-full bg-gradient-to-br from-zinc-800 to-zinc-900 flex items-center justify-center">
                            <Play className="w-16 h-16 text-white/30" />
                          </div>
                        ) : (
                          <div className="absolute inset-0 flex items-center justify-center bg-zinc-800">
                            <span className="text-xs text-zinc-500">Rendering...</span>
                          </div>
                        )}
                        {clip.clip_path && (
                          <div
                            className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                            onClick={() => playClip(i)}
                          >
                            <div className="w-14 h-14 rounded-full bg-cyan-500/80 flex items-center justify-center">
                              <Play className="w-7 h-7 text-white ml-1" fill="currentColor" />
                            </div>
                          </div>
                        )}
                        <div className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/70 text-xs text-white">
                          {formatTime(clip.duration)}
                        </div>
                        <div className="absolute top-1 left-1 px-1.5 py-0.5 rounded bg-cyan-500/80 text-xs font-medium text-black">
                          {clip.score}
                        </div>
                      </>
                    )}
                  </div>
                  <div className="p-2">
                    <h3 className="text-sm font-medium line-clamp-2 mb-2 text-zinc-200">{clip.title}</h3>
                    <div className="flex flex-wrap gap-1">
                      {clip.clip_path ? (
                        <>
                          <button
                            onClick={() => playClip(i)}
                            className="flex items-center gap-1 px-2 py-1 rounded bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 text-xs"
                          >
                            <Play className="w-3 h-3" /> Play
                          </button>
                          <a
                            href={clipUrl(id, clip.clip_path.replace("clips/", "")) + "?download=1"}
                            download
                            onClick={(e) => e.stopPropagation()}
                            className="flex items-center gap-1 px-2 py-1 rounded bg-white/10 hover:bg-white/20 text-xs"
                          >
                            <Download className="w-3 h-3" /> Download
                          </a>
                        </>
                      ) : (
                        <span className="text-xs text-zinc-500">Preparing...</span>
                      )}
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
