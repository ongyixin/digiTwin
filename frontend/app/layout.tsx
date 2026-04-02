import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Sidebar } from "@/components/shell/Sidebar";
import { InspectorPanel } from "@/components/shell/InspectorPanel";
import { ChatbotWidget } from "@/components/chatbot/ChatbotWidget";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  weight: ["400", "500", "600", "700"],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "digiTwin — Decision Intelligence",
  description: "Permission-aware decision twin for enterprise teams",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="flex h-screen overflow-hidden bg-background">
        <Providers>
          <Sidebar />
          <main className="flex-1 overflow-y-auto">
            {children}
          </main>
          <InspectorPanel />
          <ChatbotWidget />
        </Providers>
      </body>
    </html>
  );
}
