/**
 * Proxy untuk stream preview - lewat sini agar tidak trigger IDM saat Play.
 * Proksi ke extract (cepat, -c copy) untuk putar instan.
 */
import { NextRequest, NextResponse } from "next/server";

const BACKEND = "http://127.0.0.1:8000";

export async function GET(req: NextRequest) {
  const project = req.nextUrl.searchParams.get("project");
  const index = req.nextUrl.searchParams.get("index");
  if (!project || index === null || index === "") {
    return NextResponse.json({ error: "Missing project or index" }, { status: 400 });
  }
  const idx = parseInt(index, 10);
  if (isNaN(idx) || idx < 0) {
    return NextResponse.json({ error: "Invalid index" }, { status: 400 });
  }
  try {
    const url = `${BACKEND}/clip/${project}/extract/${idx}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Backend ${res.status}`);
    const blob = await res.blob();
    return new NextResponse(blob, {
      headers: {
        "Content-Type": "application/octet-stream",
        "Cache-Control": "private, max-age=3600",
      },
    });
  } catch (e) {
    console.error("[stream-preview]", e);
    return NextResponse.json({ error: "Failed to load preview" }, { status: 502 });
  }
}
