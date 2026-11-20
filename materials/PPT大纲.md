# PPT 大纲（12–15 页，初赛版）

> 目标：12 月 14 日前定稿；每页只讲一个评分点，数字必须来自 `materials/实验记录.md` / `materials/指标表.md`。
> 评分对齐：创新性 60% + 应用价值 40%；五个必含项：背景价值 / 创新性 / 数据集与处理 / 关键代码 / 可量化指标。

| 页 | 标题 | 要点 | 素材 |
|---|---|---|---|
| 1 | 封面 | 作品名《入网体检》；一句话：上传固件 → 影子设备实测 → 能不能进网 + 放行什么 + 同族影响面；队伍/学校 | 项目名、队名 |
| 2 | 问题：设备上线前的安全判断是空的 | 校园/园区 IoT 设备先上线再补安全；NAC/微隔离要求“先跑起来才能学”；采购验收只看功能 | `docs/00` §1、信息表背景节 |
| 3 | 现有方案的结构性缺口 | 802.1X/NAC/微分段：先上线→再学习→后收紧；未部署设备没有流量，无法生成策略 | 对比图 |
| 4 | 我们的答案：上线前给结论 | 影子设备（FirmAE/QEMU 隔离仿真）→ 三类取证 → 证据分级 → 三态判定 → 最小权限策略 | 八段流水线图 |
| 5 | 创新点一：证据分级决策 | E1 实测 / E2 单点 / E3 静态；仿真失败强制降级 E3；每条 raw_ref 可追溯；不把静态推断写成实测 | `configs/judgement.yaml`、`src/evidence.py` |
| 6 | 创新点二：判定口径可解释 | 阳性发现按风险累计；未测按最坏；保障度不足只能条件放行；Critical E1 硬红线 | `materials/判定口径-T2-1.md`、`src/exposure.py` |
| 7 | 创新点三：策略与判定同源、可回滚 | 端点 → FQDN/vendor-group/ASN；ACL/MUD；`asn-fallback` 显式；`rollback_ref` 必填 | `src/policy.py`、`configs/baseline.yaml` |
| 8 | 数据集：三锚点 + 12 固件计划 | A1 Tenda O4 V3.0、A2 D-Link DCS-960L 1.07.102、A3 Tenda AC15 V15.03.05.18；公开固件、SHA-256、CVE 版本对齐；12 固件目标 | `configs/anchors.yaml`、`materials/数据集说明.md` |
| 9 | 数据集处理：解包与取证 | binwalk 封装；AC15 841 文件/1.488 s、DCS-960L 1133 文件/1.432 s、O4 614 文件；三类静态取证 36/4/32 条 | `materials/实验记录.md`、`materials/证据样例` |
| 10 | 实验：影子设备跑分 | AC15 armel 启动成功、网络 192.168.0.1 可达、Web 80 拒绝；DCS/O4 待跑；失败按 E3 记录 | `materials/firmae/` |
| 11 | 证据链样例 | 默认口令 `sys.baseuserpass`、`/goform/telnet`、`www.tenda.com.cn`/`www.oray.com`；每条 level/confidence/raw_ref | `materials/report_a3.md` |
| 12 | 判定样例 | A1/A2/A3 当前 E3-only 均 `conditional`（U/A：0.625/0.245、0.794/0.132、0.642/0.262）；pass/reject 需 E1/clean 固件 | `materials/decision_sample_a*.json` |
| 13 | 策略样例 | A1/A2/A3 ACL 4/1/5 条；FQDN；`asn-fallback` 0/3（真实样例），ASN 路径由单测覆盖 | `materials/policy_sample_a*.json` |
| 14 | 指标与验证 | 解包耗时/文件数；kappa/覆盖率/误杀/漏放待标注；启动成功率/Web 可用率；不编数字 | `materials/指标表.md`、`src/metrics.py` |
| 15 | 落地与路线 | 校园/园区网管场景、等保最小授权、可复制性；CodeArts/RDS/Redis 留痕；下一步 FirmAE/标注/策略 demo | 部署方案、实验记录 |

## 讲述节奏（15 分钟版）

- 0–2 min：问题与现有方案缺口（页 2–3）；
- 2–6 min：三个创新点（页 5–7），重点讲“为什么 E1 不能算 0”；
- 6–9 min：数据与实验（页 8–10），只讲有来源的数字；
- 9–12 min：证据/判定/策略样例（页 11–13）；
- 12–15 min：指标、落地与路线（页 14–15）。

## 制作注意

- E3-only 的页面必须加“静态初判，未实测”角标；
- 不把 A1/A2/A3 的 `conditional` 说成“通过”或“拒绝”；
- 图表中每个数字标注来源（实验记录行/JSON 文件）；
- CodeArts 截图、模型名单独一页或页脚留痕。
