import { redirect } from "next/navigation";

/**
 * 根路径默认跳转到凭证录入模块（v0.1 第一个上线候选；docs/PRD.md 确认后调整）.
 */
export default function Home() {
  redirect("/bookkeeping");
}
