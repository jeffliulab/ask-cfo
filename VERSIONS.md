# agent-as-a-cfo 版本总览

> 按 [agent-rules / workflows/rapid-versioning.md](https://github.com/jeffliulab/agent-rules) 的 pre-1.0 轻量模式。
> 详细任务清单见 [`docs/NEXT_STEPS.md`](docs/NEXT_STEPS.md)。每个版本的开发日志见 [`docs/versions/`](docs/versions/)。

## 当前开发

```
v0.1.0   全栈骨架 + 选 1-2 个 CFO 模块做完整 demo
         （候选：凭证录入 + 法规问答；详见 docs/PRD.md）
         任务清单 → docs/NEXT_STEPS.md
         开发日志 → docs/versions/v0.1.0.md
         开始日期：2026-04-24
```

## 计划中

```
v0.2.0P  月结对账（凭证审核 + 试算平衡）
v0.3.0P  财务报表（三大报表 + 多期对比 + 比率分析）
v0.4.0P  报税申报（增值税 / 企业所得税 / 个税自动计算 + 预填表）
         + 工作区持久化 SQLite
v0.5.0P  Citation Drawer 增强（PDF.js 高亮原文）+ 真 RAG 切分
v0.6.0P  代账机构多客户管理 + 权限隔离
v0.7.0P  打包 Docker + 部署演示站点
v1.0.0P  开源发布 + 文档站 + 第一批用户（升级到 versioning.md 完整规范）
```

## 已完成

> （v0.1.0 完成后归档至此，附 git tag + 归档日期）

---

**版本号约定**：`v0.{MINOR}.{PATCH}` SemVer，pre-1.0 阶段 MINOR bump 即一个阶段。
**与 fin-pilot 关系**：framework 壳子从 fin-pilot v0.1.0 (commit `ac6f87c`) 复制；
两个项目独立演进，未来如果共享代码超过 2-3 处再考虑抽 npm/pip 包。
