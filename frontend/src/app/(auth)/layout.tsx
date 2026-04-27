import type { Metadata } from "next";
import { ToastContainer } from "@/components/ui/Toast";

export const metadata: Metadata = {
  title: "RAGEve - Authentication",
  description: "Login or register for RAGEve",
};

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      {children}
      <ToastContainer />
    </>
  );
}
