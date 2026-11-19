# AGENTS.md — 码道/任何编码 Agent 的入口

本项目参加第十一届华为 ICT 大赛（2026-2027）中国创新赛 · 赛题一。

## 开工前必读（按顺序）

1. `.codeartsdoer/rules/00-project.md` — 可改范围与编码约定
2. `.codeartsdoer/rules/01-llm-coding-rules.md` — LLM 编码四条行为准则（必守）
3. `docs/02-推行计划.md` — **当前该做什么，按阶段执行**
4. `docs/00-总体框架.md` — 项目定位与架构（背景，不必逐字执行）

## 一句话目标

上传设备固件 → 影子设备实测 → 输出“能不能进网 + 放行什么 + 同族影响面”，
并在初赛前产出全部材料。

## 硬约束

- 只改 `src/`、`tests/`、`configs/`、`materials/`
- `docs/`、`sources/`、`data/` 只读
- 完成标准：`python -m pytest -q` 通过
- 提交信息带 `[codearts]`
- 不编数据、不碰真机/现网、不提交密钥

## 当前阶段

见 `docs/02-推行计划.md` 的“阶段看板”。默认从第一个未完成的任务卡开始。
