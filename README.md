# 入网体检（工作名）

> 固件 → 影子设备 → 准入判定 + 最小权限策略。
> 参赛：第十一届华为 ICT 大赛 2026-2027 · 中国创新赛 · 赛题一。

## 先读

| 文档 | 内容 |
|---|---|
| [AGENTS.md](AGENTS.md) | 码道/编码 Agent 的入口 |
| [docs/02-推行计划.md](docs/02-推行计划.md) | **当前该做什么**（阶段看板 + 任务卡 + 材料清单） |
| [docs/00-总体框架.md](docs/00-总体框架.md) | 架构、初赛范围、分工、CodeArts 规范 |
| [docs/01-赛题与初赛要求.md](docs/01-赛题与初赛要求.md) | 官方赛题原文、评分权重、材料要求 |
| `.codeartsdoer/rules/` | 码道行为准则（含 Karpathy 四条规则） |
| `sources/` | 官方手册、赛题原文、路演胶片（取证材料） |

## 当前阶段

初赛（材料为主，不做完整系统）：

1. 锚点 ≥3（Tenda O4 V3.0 已有）
2. FirmAE 跑 3 个固件
3. 证据链样例 + 决策样例
4. 策略合成 demo
5. PPT + 3 分钟视频 + 信息收集表

## 目录

```
docs/       文档
src/        源码（unpack / exposure / policy / evidence）
tests/      测试
configs/    配置
sources/    官方取证材料（只读）
.codeartsdoer/  码道项目规则与技能
```

## 约定

- 只改 `src/ tests/ configs/`；`docs/` 由人维护；
- 提交信息带 `[codearts]` 表示该改动由码道生成；
- 不提交 `data/`、固件二进制与任何未脱敏样本。
