import type { ReactNode } from "react";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Chat — Prakriti School AI Assistant",
  description: "Chat with the Prakriti AI Assistant (embed-friendly layout)",
};

export default function ChatLayout({ children }: { children: ReactNode }) {
  return children;
}
