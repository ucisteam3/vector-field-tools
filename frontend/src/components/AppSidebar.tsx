"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Film, ChevronLeft, Settings } from "lucide-react";

export default function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-zinc-700 bg-[#0d1117] fixed left-0 top-0 bottom-0 flex flex-col z-10">
      <div className="p-6">
        <Link href="/" className="flex items-center gap-2 text-xl font-bold text-cyan-400">
          <Film className="w-8 h-8" />
          AI Clipper
        </Link>
      </div>
      <nav className="flex-1 px-4 space-y-1">
        <Link
          href="/"
          className={`flex items-center gap-2 px-4 py-3 rounded-lg transition-colors ${
            pathname === "/" ? "bg-cyan-500/20 text-cyan-400" : "text-zinc-400 hover:text-white"
          }`}
        >
          <Film className="w-5 h-5" />
          Dashboard
        </Link>
        <Link
          href="/settings"
          className={`flex items-center gap-2 px-4 py-3 rounded-lg transition-colors ${
            pathname === "/settings" ? "bg-cyan-500/20 text-cyan-400" : "text-zinc-400 hover:text-white"
          }`}
        >
          <Settings className="w-5 h-5" />
          Setting
        </Link>
      </nav>
    </aside>
  );
}
