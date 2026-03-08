/**
 * Proxy untuk stream clip - path tanpa .mp4 agar tidak trigger IDM saat Play.
 * Backend fetch dilakukan server-side.
 */
import { NextRequest, NextResponse } from "next/server";

const BACKEND = "http://127.0.0.1:8000";

export async function GET(req: NextRequest) {
  const project = req.nextUrl.searchParams.get("project");
  const file = req.nextUrl.searchParams.get("file");
  if (!project || !file) {
    return NextResponse.json({ error: "Missing project or file" }, { status: 400 });
  }
  try {
    const url = `${BACKEND}/clip/${project}/${encodeURIComponent(file)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Backend ${res.status}`);
    const blob = await res.blob();
    return new NextResponse(blob, {
      headers: {
        "Content-Type": "video/mp4",
        "Content-Disposition": "inline",
        "Cache-Control": "private, max-age=3600",
      },
    });
  } catch (e) {
    console.error("[play-clip]", e);
    return NextResponse.json({ error: "Failed to load clip" }, { status: 502 });
  }
}
