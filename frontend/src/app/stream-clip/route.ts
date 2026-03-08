/**
 * Proxy untuk stream clip - path tanpa .mp4 agar tidak trigger IDM saat Play.
 * Tidak di bawah /api supaya tidak di-rewrite ke backend.
 */
import { NextRequest, NextResponse } from "next/server";

const BACKEND = "http://127.0.0.1:8000";

export async function GET(req: NextRequest) {
  const project = req.nextUrl.searchParams.get("project");
  const file = req.nextUrl.searchParams.get("file");
  const download = req.nextUrl.searchParams.get("download") === "1";
  if (!project || !file) {
    return NextResponse.json({ error: "Missing project or file" }, { status: 400 });
  }
  try {
    const url = `${BACKEND}/clip/${project}/${encodeURIComponent(file)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Backend ${res.status}`);
    const blob = await res.blob();
    const headers: Record<string, string> = {
      "Content-Type": "application/octet-stream",
      "Cache-Control": "private, max-age=3600",
    };
    if (download) {
      const safeName = file.replace(/[^\w\s.-]/g, "_").trim() || "clip.mp4";
      headers["Content-Disposition"] = `attachment; filename="${safeName}"`;
    }
    return new NextResponse(blob, { headers });
  } catch (e) {
    console.error("[stream-clip]", e);
    return NextResponse.json({ error: "Failed to load clip" }, { status: 502 });
  }
}
