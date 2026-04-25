/**
 * /regulations —— 法规问答主页（v0.1.0）.
 *
 * 工作区结构（中栏）：
 * - 顶部：标题 + 当模块状态 idle 时显示 SampleQueries
 * - 中部：AgentTrace（折叠展示 agent 检索轨迹）
 * - 下部：RegulationCard 列表（按出场顺序）
 *
 * Chat 输入在右栏 ChatPanel；点 SampleQueries 通过 ``pendingQuery``
 * 桥接触发 ChatPanel 自动 send（详见 components/ChatPanel.tsx）。
 */

"use client";

import { useEffect } from "react";

import { WorkspaceCanvas } from "@/components/WorkspaceCanvas";
import { AgentTrace } from "@/features/regulations/AgentTrace";
import { RegulationCard } from "@/features/regulations/RegulationCard";
import { SampleQueries } from "@/features/regulations/SampleQueries";
import {
  selectModuleAgentTrace,
  selectModuleCards,
  selectModuleStatus,
  useWorkspaceStore,
} from "@/stores/workspaceStore";
import type { RegulationSnippetCard } from "@/types/workspace";

export default function RegulationsPage() {
  const cards = useWorkspaceStore(selectModuleCards("regulations"));
  const status = useWorkspaceStore(selectModuleStatus("regulations"));
  const agentTrace = useWorkspaceStore(selectModuleAgentTrace("regulations"));
  const setPendingQuery = useWorkspaceStore((s) => s.setPendingQuery);
  const setActiveModule = useWorkspaceStore((s) => s.setActiveModule);

  // 标记当前 active module（v0.6 多客户切换会用到）
  useEffect(() => {
    setActiveModule("regulations");
  }, [setActiveModule]);

  const isEmpty = cards.length === 0 && status === "idle";
  const isLoading = status === "loading";

  // 类型守卫：只渲染 regulation_snippet 类型的卡片
  const regCards = cards.filter(
    (c): c is RegulationSnippetCard => c.card_type === "regulation_snippet",
  );

  return (
    <WorkspaceCanvas>
      <div className="space-y-4">
        {/* 标题 */}
        <div>
          <h1 className="text-lg font-semibold">法规问答</h1>
          <p className="mt-1 text-xs text-muted-foreground">
            自然语言提问 → agent 检索增值税 / 企业所得税 / 个人所得税 / 会计准则 →
            带 [N] 引用的答案 + 点角标看原文。
          </p>
        </div>

        {/* 空状态：示例查询 */}
        {isEmpty && (
          <SampleQueries
            onPick={(q) => setPendingQuery(q)}
            disabled={isLoading}
          />
        )}

        {/* Agent trace（流式更新） */}
        {agentTrace.length > 0 && <AgentTrace events={agentTrace} />}

        {/* 法规条款卡片 */}
        {regCards.length > 0 && (
          <div className="space-y-3">
            {regCards.map((card) => (
              <RegulationCard key={card.workspace_id} card={card} />
            ))}
          </div>
        )}

        {/* 加载中提示（首次） */}
        {isLoading && cards.length === 0 && (
          <div className="rounded-md border border-border bg-muted/20 px-4 py-3 text-xs text-muted-foreground">
            Agent 正在检索法规库...
          </div>
        )}
      </div>
    </WorkspaceCanvas>
  );
}
