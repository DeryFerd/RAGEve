import type { Metadata } from "next";
import "./globals.css";
import { ConditionalAppShell } from "@/components/layout/ConditionalAppShell";
import { ToastContainer } from "@/components/ui/Toast";

export const metadata: Metadata = {
  title: "RAGEve",
  description: "AI-powered RAG platform with Ollama + Qdrant",
  icons: {
    icon: "/logo.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-theme="dark">
      <body>
        <ConditionalAppShell>{children}</ConditionalAppShell>
        <ToastContainer />
      </body>
    </html>
  );
}
