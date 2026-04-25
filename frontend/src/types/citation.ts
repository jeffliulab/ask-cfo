/**
 * Citation —— 镜像 backend/interfaces.py 的 Citation dataclass.
 *
 * 任何 AI 输出 / 卡片字段背后的"原文出处指针"。前端用 [N] 上标渲染，
 * 点击触发 Citation drawer (Day 8) 抽出右侧 iframe 加载 url.
 */

export type Citation = {
  label: string; // e.g. "[1]"
  source_name: string; // e.g. "巨潮·贵州茅台 2024 年度报告"
  url: string;
};
