"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Youtube, Plus, Film, Calendar, Loader2, ExternalLink, Trash2, ShieldCheck, Upload } from "lucide-react";
import AppSidebar from "@/components/AppSidebar";
import { analyzeVideo, getProjects, getProjectStatus, deleteProject, retryProject, videoUrl, uploadCookies, getCookiesStatus, type Project } from "@/lib/api";

function getYoutubeThumbnail(url: string | null | undefined): string | null {
  if (!url) return null;
  const m = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/);
  return m ? `https://img.youtube.com/vi/${m[1]}/mqdefault.jpg` : null;
}
import { useAppSettings } from "@/lib/settings-store";

export default function HomePage() {
  const [exportSettings] = useAppSettings();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [retrying, setRetrying] = useState<string | null>(null);
  const [statusCache, setStatusCache] = useState<Record<string, { progress?: string; eta_message?: string }>>({});
  const [cookiesStatus, setCookiesStatus] = useState<{ exists: boolean; size_kb: number } | null>(null);
  const [uploadingCookies, setUploadingCookies] = useState(false);
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const loadProjects = useCallback(async () => {
    setLoadError(null);
    setLoadingProjects(true);
    try {
      const p = await getProjects();
      setProjects(p);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Gagal memuat projects");
    } finally {
      setLoadingProjects(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
    getCookiesStatus().then(setCookiesStatus).catch(() => {});
  }, [loadProjects]);

  // Poll status for analyzing projects
  const analyzingIds = projects.filter((p) => p.status === "analyzing").map((p) => p.project_id);
  useEffect(() => {
    if (analyzingIds.length === 0) return;
    const t = setInterval(async () => {
      for (const id of analyzingIds) {
        try {
          const st = await getProjectStatus(id);
          setStatusCache((c) => ({
            ...c,
            [id]: { progress: st.progress, eta_message: st.eta_message },
          }));
          if (st.status === "ready" || st.status === "error") {
            loadProjects();
          }
        } catch {
          /* ignore */
        }
      }
    }, 2000);
    return () => clearInterval(t);
  }, [analyzingIds.join(","), loadProjects]);

  const handleAnalyze = async () => {
    if (!url.trim()) return;
    setLoading(true);
    try {
      const { project_id, title } = await analyzeVideo(url.trim(), exportSettings);
      // Add new project to list without redirect
      const newProj: Project = {
        project_id,
        title,
        youtube_url: url.trim(),
        video_path: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        clips: [],
        status: "analyzing",
        error: null,
      };
      setProjects((prev) => [newProj, ...prev]);
      setStatusCache((c) => ({
        ...c,
        [project_id]: { progress: "Starting...", eta_message: "~5 min" },
      }));
      setUrl(""); // Clear input so user can paste another
    } catch (e) {
      alert(String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (projectId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("Hapus project ini?")) return;
    setDeleting(projectId);
    try {
      await deleteProject(projectId);
      setProjects((prev) => prev.filter((p) => p.project_id !== projectId));
    } catch (err) {
      alert(String(err));
    } finally {
      setDeleting(null);
    }
  };

  const handleRetry = async (projectId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setRetrying(projectId);
    try {
      await retryProject(projectId);
      setProjects((prev) =>
        prev.map((p) =>
          p.project_id === projectId ? { ...p, status: "analyzing" as const, error: null } : p
        )
      );
      setStatusCache((c) => ({ ...c, [projectId]: { progress: "Starting...", eta_message: "~5 min" } }));
    } catch (err) {
      alert(String(err));
    } finally {
      setRetrying(null);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0c10] text-white">
      <AppSidebar />

      <main className="flex-1 ml-64 p-8 bg-[#0a0c10]">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-2xl mb-12"
        >
          <h1 className="text-3xl font-bold mb-2">Create viral clips from YouTube</h1>
          <p className="text-zinc-400 mb-6">
            Paste a YouTube link and our AI will detect the best moments to turn into short clips.
          </p>
          <div className="flex flex-col gap-4">
            <div className="flex gap-3">
            <div className="flex-1 flex items-center gap-2 bg-zinc-800/50 border border-zinc-600 rounded-xl px-4 py-3" suppressHydrationWarning>
              <Youtube className="w-5 h-5 text-red-500 flex-shrink-0" />
              <input
                type="url"
                placeholder="https://youtube.com/watch?v=..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
                className="bg-transparent flex-1 outline-none text-white placeholder:text-zinc-500"
                autoComplete="off"
              />
            </div>
            <button
              onClick={handleAnalyze}
              disabled={loading}
              className="px-6 py-3 bg-cyan-500 hover:bg-cyan-400 text-black font-semibold rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Plus className="w-5 h-5" />
                  Analyze
                </>
              )}
            </button>
          </div>
            <div className="flex items-center gap-3 text-sm" suppressHydrationWarning>
              <span className="flex items-center gap-2 text-zinc-500">
                <ShieldCheck className="w-4 h-4" />
                Cookies YouTube:
              </span>
              {!mounted ? (
                <span className="text-zinc-500">...</span>
              ) : cookiesStatus?.exists ? (
                <span className="text-cyan-400">OK {cookiesStatus.size_kb} KB aktif</span>
              ) : (
                <label className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-dashed border-zinc-600 hover:border-cyan-500/50 cursor-pointer text-zinc-400 hover:text-cyan-400 transition-colors">
                  <Upload className="w-4 h-4" />
                  {uploadingCookies ? "Mengunggah..." : "Upload cookies (.txt)"}
                  <input
                    type="file"
                    accept=".txt"
                    className="hidden"
                    onChange={async (e) => {
                      const f = e.target.files?.[0];
                      if (!f) return;
                      setUploadingCookies(true);
                      try {
                        await uploadCookies(f);
                        setCookiesStatus(await getCookiesStatus());
                      } catch (err) {
                        alert(String(err));
                      } finally {
                        setUploadingCookies(false);
                        e.target.value = "";
                      }
                    }}
                    disabled={uploadingCookies}
                  />
                </label>
              )}
              <span className="text-zinc-600 text-xs">(Membantu bypass video terbatas)</span>
            </div>
          </div>
        </motion.div>

        <section>
          <h2 className="text-xl font-semibold mb-4">Your projects</h2>
          {loadingProjects ? (
            <div className="flex items-center gap-2 text-zinc-400">
              <Loader2 className="w-5 h-5 animate-spin" />
              Loading...
            </div>
          ) : loadError ? (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-amber-400">
              <p className="mb-2">{loadError}</p>
              <button
                onClick={loadProjects}
                className="px-4 py-2 bg-amber-500/20 hover:bg-amber-500/30 rounded-lg text-sm transition-colors"
              >
                Coba lagi
              </button>
            </div>
          ) : projects.length === 0 ? (
            <p className="text-zinc-500">No projects yet. Paste a YouTube URL above to get started.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {projects.map((p, i) => (
                <motion.div
                  key={p.project_id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                >
                  <div className="flex items-center gap-4 rounded-xl border border-zinc-700 bg-zinc-800/50 px-4 py-3 hover:bg-zinc-700/50 transition-colors group">
                    <Link href={`/project/${p.project_id}`} className="flex flex-1 items-center gap-4 min-w-0">
                      <div className="w-24 h-14 flex-shrink-0 rounded-lg overflow-hidden bg-zinc-900 relative">
                        {(() => {
                          const thumbUrl = getYoutubeThumbnail(p.youtube_url) ?? (p.video_path && p.status === "ready" ? videoUrl(p.project_id) : null);
                          return (
                            <>
                              {thumbUrl ? (
                                <img
                                  src={thumbUrl}
                                  alt=""
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                <div className="w-full h-full flex flex-col items-center justify-center gap-0.5 p-1">
                                  <Film className="w-8 h-8 text-zinc-600" />
                                </div>
                              )}
                              {p.status === "analyzing" && (
                                <div className="absolute inset-0 flex flex-col items-center justify-center gap-0.5 p-1 bg-black/70">
                                  <Loader2 className="w-5 h-5 animate-spin text-cyan-400 flex-shrink-0" />
                                  <span className="text-[9px] text-cyan-400 font-medium leading-tight text-center truncate w-full">
                                    {(() => {
                                      const prog = statusCache[p.project_id]?.progress || "Loading...";
                                      const m = prog.match(/([\d.]+)\s*%/);
                                      return m ? `${m[1]}%` : prog.replace(/\.\.\.?\s*$/, "");
                                    })()}
                                  </span>
                                  {statusCache[p.project_id]?.eta_message && (
                                    <span className="text-[8px] text-zinc-500">
                                      ETA {statusCache[p.project_id].eta_message}
                                    </span>
                                  )}
                                  {(() => {
                                    const prog = statusCache[p.project_id]?.progress || "";
                                    const m = prog.match(/([\d.]+)\s*%/);
                                    const pct = m ? parseFloat(m[1]) : 0;
                                    if (pct > 0 && pct < 100) {
                                      return (
                                        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-zinc-700">
                                          <div
                                            className="h-full bg-cyan-500 transition-all duration-500"
                                            style={{ width: `${pct}%` }}
                                          />
                                        </div>
                                      );
                                    }
                                    return null;
                                  })()}
                                </div>
                              )}
                            </>
                          );
                        })()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium truncate">{p.title || "Untitled"}</h3>
                        <div className="flex items-center gap-2 mt-0.5 text-sm text-zinc-500">
                          {p.youtube_url ? (
                            <a
                              href={p.youtube_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="flex items-center gap-1 hover:text-cyan-400 truncate max-w-[280px]"
                            >
                              <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
                              <span className="truncate">{p.youtube_url}</span>
                            </a>
                          ) : (
                            <span>{p.clips?.length ?? 0} clips</span>
                          )}
                          <span>·</span>
                          <span className="flex items-center gap-1 flex-shrink-0" suppressHydrationWarning>
                            <Calendar className="w-3.5 h-3.5" />
                            {new Date(p.updated_at).toLocaleDateString()}
                          </span>
                        </div>
                        {p.status === "analyzing" && (
                          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5">
                            <span className="text-cyan-400 text-xs truncate">
                              {statusCache[p.project_id]?.progress || "Processing..."}
                            </span>
                            {statusCache[p.project_id]?.eta_message && (
                              <span className="text-zinc-500 text-xs">
                                • Klip siap ~{statusCache[p.project_id].eta_message}
                              </span>
                            )}
                          </div>
                        )}
                        {p.status === "error" && (
                          <div className="mt-1 flex items-center gap-2">
                            <span className="text-red-400 text-xs truncate flex-1 min-w-0">{p.error}</span>
                            <button
                              onClick={(e) => handleRetry(p.project_id, e)}
                              disabled={retrying === p.project_id || !p.youtube_url}
                              className="text-cyan-400 hover:text-cyan-300 text-xs shrink-0 disabled:opacity-50"
                            >
                              {retrying === p.project_id ? "..." : "Retry"}
                            </button>
                          </div>
                        )}
                        {p.status === "ready" && (
                          <div className="mt-1 text-zinc-500 text-xs">{p.clips?.length ?? 0} clips</div>
                        )}
                      </div>
                    </Link>
                    <button
                      onClick={(e) => handleDelete(p.project_id, e)}
                      disabled={deleting === p.project_id}
                      className="opacity-50 hover:opacity-100 hover:text-red-400 p-2 rounded-lg transition-all flex-shrink-0"
                      title="Hapus project"
                    >
                      {deleting === p.project_id ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <Trash2 className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
