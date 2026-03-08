import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[#0a0c10] flex flex-col items-center justify-center p-8 text-white">
      <h2 className="text-xl font-semibold mb-4">Halaman tidak ditemukan</h2>
      <Link
        href="/"
        className="px-6 py-3 bg-cyan-500 hover:bg-cyan-400 text-black font-semibold rounded-xl transition-colors"
      >
        Kembali ke Dashboard
      </Link>
    </div>
  );
}
