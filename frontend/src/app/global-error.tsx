"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body style={{ backgroundColor: "#0a0c10", color: "#fff", fontFamily: "system-ui", padding: "2rem", textAlign: "center" }}>
        <h2>Terjadi kesalahan</h2>
        <p style={{ margin: "1rem 0", color: "#94a3b8" }}>{error.message}</p>
        <button
          onClick={() => reset()}
          style={{ padding: "0.75rem 1.5rem", backgroundColor: "#22d3ee", color: "#000", border: "none", borderRadius: "0.5rem", fontWeight: 600, cursor: "pointer" }}
        >
          Coba lagi
        </button>
      </body>
    </html>
  );
}
