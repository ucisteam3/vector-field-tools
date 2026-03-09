"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Youtube, Plus, Film, Calendar, Loader2, Trash2, ShieldCheck, Upload } from "lucide-react";
import AppSidebar from "@/components/AppSidebar";
import { analyzeVideo, getProjects, getProjectStatus, deleteProject, retryProject, videoUrl, uploadCookies, getCookiesStatus, type Project } from "@/lib/api";
import { useModal } from "@/components/ModalProvider";

function getYoutubeThumbnail(url: string | null | undefined): string | null {
  if (!url) return null;
  const m = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/);
  return m ? `https://img.youtube.com/vi/${m[1]}/mqdefault.jpg` : null;
}
import { useAppSettings } from "@/lib/settings-store";

export default function HomePage() {
  const modal = useModal();
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
    const fetchStatus = async () => {
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
    };
    fetchStatus(); // Fetch immediately, don't wait 2s
    const t = setInterval(fetchStatus, 2000);
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
      await modal.alert(String(e), { title: "Gagal" });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (projectId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const ok = await modal.confirm("Hapus project ini?", { title: "Konfirmasi", confirmText: "Hapus", cancelText: "Batal" });
    if (!ok) return;
    setDeleting(projectId);
    try {
      await deleteProject(projectId);
      setProjects((prev) => prev.filter((p) => p.project_id !== projectId));
    } catch (err) {
      await modal.alert(String(err), { title: "Gagal" });
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
      await modal.alert(String(err), { title: "Gagal" });
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
                        await modal.alert(String(err), { title: "Upload cookies gagal" });
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
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {projects.map((p, i) => (
                <motion.div
                  key={p.project_id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="rounded-xl border border-zinc-700 bg-zinc-800/50 overflow-hidden hover:bg-zinc-700/50 transition-colors group relative"
                >
                  <Link href={`/project/${p.project_id}`} className="block">
                    <div className="aspect-video relative bg-zinc-900">
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
                              <div className="w-full h-full flex flex-col items-center justify-center p-4">
                                <Film className="w-12 h-12 text-zinc-600" />
                              </div>
                            )}
                            {p.status === "analyzing" && (
                              <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 p-2 bg-black/70">
                                <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
                                <span className="text-xs text-cyan-400 font-medium text-center">
                                  {(() => {
                                    const prog = statusCache[p.project_id]?.progress || "Loading...";
                                    const pctMatch = prog.match(/([\d.]+)\s*%/);
                                    const nmMatch = prog.match(/(\d+)\s*\/\s*(\d+)/);
                                    if (pctMatch) return `${pctMatch[1]}%`;
                                    if (nmMatch) return `${nmMatch[1]}/${nmMatch[2]}`;
                                    return prog.replace(/\.\.\.?\s*$/, "");
                                  })()}
                                </span>
                                {statusCache[p.project_id]?.eta_message && (
                                  <span className="text-[10px] text-zinc-400">{statusCache[p.project_id].eta_message}</span>
                                )}
                                {(() => {
                                  const prog = statusCache[p.project_id]?.progress || "";
                                  let pct = 0;
                                  const pctMatch = prog.match(/([\d.]+)\s*%/);
                                  const nmMatch = prog.match(/(\d+)\s*\/\s*(\d+)/);
                                  if (pctMatch) pct = parseFloat(pctMatch[1]);
                                  else if (nmMatch) pct = (parseInt(nmMatch[1], 10) / parseInt(nmMatch[2], 10)) * 100;
                                  if (pct > 0 && pct < 100) {
                                    return (
                                      <div className="absolute bottom-0 left-0 right-0 h-1 bg-zinc-700">
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
                      {p.status === "ready" && (
                        <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-cyan-500/90 text-xs font-medium text-black">
                          {p.clips?.length ?? 0} clips
                        </div>
                      )}
                      {p.status === "error" && (
                        <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-red-500/90 text-xs font-medium text-white">
                          Error
                        </div>
                      )}
                    </div>
                    <div className="p-3">
                      <h3 className="font-medium text-sm line-clamp-2 text-zinc-200">{p.title || "Untitled"}</h3>
                      <div className="flex items-center gap-2 mt-1.5 text-xs text-zinc-500">
                        <span className="flex items-center gap-1" suppressHydrationWarning>
                          <Calendar className="w-3 h-3" />
                          {new Date(p.updated_at).toLocaleDateString()}
                        </span>
                        {p.status === "analyzing" && statusCache[p.project_id]?.eta_message && (
                          <span className="text-cyan-400">• {statusCache[p.project_id].eta_message}</span>
                        )}
                      </div>
                      {p.status === "error" && (
                        <div className="mt-1.5 flex items-center gap-2">
                          <span className="text-red-400 text-xs line-clamp-1 flex-1">{p.error}</span>
                          <button
                            onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleRetry(p.project_id, e); }}
                            disabled={retrying === p.project_id || !p.youtube_url}
                            className="text-cyan-400 hover:text-cyan-300 text-xs shrink-0 disabled:opacity-50"
                          >
                            {retrying === p.project_id ? "..." : "Retry"}
                          </button>
                        </div>
                      )}
                    </div>
                  </Link>
                  <button
                    onClick={(e) => handleDelete(p.project_id, e)}
                    disabled={deleting === p.project_id}
                    className="absolute top-2 right-2 p-1.5 rounded-lg bg-black/50 opacity-0 group-hover:opacity-100 hover:bg-red-500/80 hover:text-white transition-all"
                    title="Hapus project"
                  >
                    {deleting === p.project_id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                </motion.div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
