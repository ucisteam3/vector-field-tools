import type { Metadata } from "next";
import "./globals.css";
import { ModalProvider } from "@/components/ModalProvider";

export const metadata: Metadata = {
  title: "AI Video Clipper",
  description: "Local AI-powered viral clip generator",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" style={{ colorScheme: "dark" }}>
      <body className="min-h-screen bg-[#0a0c10] text-white antialiased" style={{ backgroundColor: "#0a0c10", color: "#f0f6fc" }}>
        <ModalProvider>{children}</ModalProvider>
      </body>
    </html>
  );
}
