/**
 * LeftMenu —— 左栏：5 个 CFO 核心模块 + 历史 workspace 占位.
 *
 * 模块上线节奏（详见 docs/PRD.md + VERSIONS.md）：
 *   v0.1 优先选 1-2 个模块做完整 demo；其他列出但禁用 + tooltip 标 vX.X
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Building2,
  ClipboardCheck,
  FileSearch,
  FileSpreadsheet,
  Receipt,
  Sparkles,
} from "lucide-react";

import { cn } from "@/lib/utils";

type ModuleEntry = {
  href: string;
  label: string;
  icon: typeof Receipt;
  enabled: boolean;
  comingIn?: string;
  hint?: string;
};

const MODULES: ModuleEntry[] = [
  {
    href: "/bookkeeping",
    label: "凭证录入",
    icon: Receipt,
    enabled: true, // v0.1 可达页面（具体功能待 PRD 决定）
    hint: "发票/银行流水 → AI 草拟会计分录",
  },
  {
    href: "/month-end",
    label: "月结对账",
    icon: ClipboardCheck,
    enabled: false,
    comingIn: "v0.2",
    hint: "凭证审核 + 试算平衡 + 出报表",
  },
  {
    href: "/reports",
    label: "财务报表",
    icon: FileSpreadsheet,
    enabled: false,
    comingIn: "v0.3",
    hint: "三大报表 + 多期对比 + 比率分析",
  },
  {
    href: "/tax-filing",
    label: "报税申报",
    icon: Building2,
    enabled: false,
    comingIn: "v0.4",
    hint: "增值税 / 企业所得税 / 个税自动计算 + 预填表",
  },
  {
    href: "/regulations",
    label: "法规问答",
    icon: FileSearch,
    enabled: true, // v0.1 可达（演示三栏壳的最小路径）
    hint: "RAG 检索税法 / 会计准则 + 引用原文",
  },
];

export function LeftMenu() {
  const pathname = usePathname();

  return (
    <div className="flex h-full flex-col gap-1 px-3 py-4">
      {/* Logo / 项目名 */}
      <div className="mb-4 flex items-center gap-2 px-2">
        <Sparkles className="h-5 w-5 text-primary" />
        <div>
          <div className="text-sm font-semibold leading-tight">CFO Agent</div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
            v0.1 · dev
          </div>
        </div>
      </div>

      {/* 模块菜单 */}
      <div className="mb-4">
        <div className="px-2 py-1 text-[10px] uppercase tracking-wider text-muted-foreground">
          模块
        </div>
        <nav className="flex flex-col gap-0.5">
          {MODULES.map((m) => {
            const isActive = pathname?.startsWith(m.href);
            return m.enabled ? (
              <Link
                key={m.href}
                href={m.href}
                title={m.hint}
                className={cn(
                  "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                )}
              >
                <m.icon className="h-4 w-4" />
                <span>{m.label}</span>
              </Link>
            ) : (
              <div
                key={m.href}
                title={`${m.comingIn} 上线 · ${m.hint ?? ""}`}
                className="flex cursor-not-allowed items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground/50"
              >
                <span className="flex items-center gap-2">
                  <m.icon className="h-4 w-4" />
                  <span>{m.label}</span>
                </span>
                <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {m.comingIn}
                </span>
              </div>
            );
          })}
        </nav>
      </div>

      {/* 历史会话占位（v0.4 工作区持久化才真用得上） */}
      <div className="mt-2">
        <div className="px-2 py-1 text-[10px] uppercase tracking-wider text-muted-foreground">
          历史会话
        </div>
        <div className="px-2 py-2 text-xs text-muted-foreground/70">
          v0.4+ 持久化 SQLite 上线后开放
        </div>
      </div>
    </div>
  );
}
