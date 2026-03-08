"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen bg-[#0a0c10] flex flex-col items-center justify-center p-8 text-white">
      <h2 className="text-xl font-semibold mb-4">Terjadi kesalahan</h2>
      <p className="text-zinc-400 mb-6 text-center max-w-md">{error.message}</p>
      <button
        onClick={reset}
        className="px-6 py-3 bg-cyan-500 hover:bg-cyan-400 text-black font-semibold rounded-xl transition-colors"
      >
        Coba lagi
      </button>
    </div>
  );
}
