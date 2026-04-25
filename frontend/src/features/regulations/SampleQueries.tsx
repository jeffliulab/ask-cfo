/**
 * SampleQueries —— /regulations 页面顶部示例查询按钮.
 *
 * v0.1 D5：让首次访问的用户能一键试用 agent search。
 * 点击 → 调用 onPick(query) 把 query 提交到 chat 流。
 */

"use client";

import { Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";

const SAMPLES = [
  "研发费用加计扣除比例是多少？",
  "餐饮发票能抵扣进项税吗？",
  "个税专项附加扣除有哪些？",
  "小规模纳税人的优惠政策？",
];

type Props = {
  onPick: (query: string) => void;
  disabled?: boolean;
};

export function SampleQueries({ onPick, disabled }: Props) {
  return (
    <div className="rounded-md border border-dashed border-border bg-muted/20 p-4">
      <div className="mb-3 flex items-center gap-2 text-xs text-muted-foreground">
        <Sparkles className="h-3.5 w-3.5" />
        <span>试用 agent search —— 点一个问题快速开始</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {SAMPLES.map((q) => (
          <Button
            key={q}
            type="button"
            variant="outline"
            size="sm"
            disabled={disabled}
            onClick={() => onPick(q)}
            className="text-xs"
          >
            {q}
          </Button>
        ))}
      </div>
    </div>
  );
}
