import type { Metadata } from "next";
import localFont from "next/font/local";

import "./globals.css";
import { ThreePaneLayout } from "@/components/ThreePaneLayout";
import { LeftMenu } from "@/components/LeftMenu";
import { ChatPanel } from "@/components/ChatPanel";
import { CitationDrawer } from "@/components/CitationDrawer";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "agent-as-a-cfo · 财务版 Cursor",
  description:
    "面向中国小微企业 / 代账机构的 AI 财务工作台：左菜单选模块（凭证 / 月结 / 报表 / 报税 / 法规），中工作区沉淀凭证 / 报表卡片，右聊天追问。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ThreePaneLayout
          left={<LeftMenu />}
          center={children}
          right={<ChatPanel />}
        />
        <CitationDrawer />
      </body>
    </html>
  );
}
