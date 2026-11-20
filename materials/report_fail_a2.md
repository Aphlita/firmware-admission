# 入网体检报告：A2

## 1. 结论

| 项 | 值 |
|---|---|
| 厂商 / 型号 | D-Link / DCS-960L |
| 固件版本 | 1.07.102 |
| 判定 | **reject** |
| 置信度 | 0.900 |
| 风险敞口 | 0.932 |
| 加权保障度 | 0.299 |

**判定理由**

- 红线：CRED_DEFAULT_ADMIN_WEB（Critical）为 E1 确认风险，直接拒绝
- 证据不足：加权保障度 assurance=0.299 < 0.60，未测项或弱证据占比较高，不能直接放行
- 风险项 3 个：CRED_DEFAULT_ADMIN_WEB(E1,c=0.90)；UNAUTH_MGMT_ENDPOINT(E2,c=0.70)；UNAUTH_INFO_DISCLOSURE(E2,c=0.70)

## 2. 证据清单

共 **3** 条；按等级：E1=1 / E2=2 / E3=0；按类别：CRED=1 / UNAUTH=2 / EGRESS=0。

| 编号 | 检查项 | 等级 | 置信度 | raw_ref | 说明 |
|---|---|---|---|---|---|
| E-A2-E1-0001 | CRED_DEFAULT_ADMIN_WEB | E1 | 0.900 | materials/firmae/dcs_login_home_headers.txt:1 | DCS-960L 1.07.102 影子设备；HTTP Basic admin/空口令返回 200，/home.asp 返回 38,782 字节管理页；默认口令实测复现 |
| E-A2-E2-0001 | UNAUTH_MGMT_ENDPOINT | E2 | 0.700 | materials/firmae/dcs_login_hnap.txt:1 | DCS-960L 1.07.102 影子设备；未认证 GET /HNAP1/ 返回 200 与 GetDeviceSettingsResponse；单次请求，未形成完整利用链 TODO(measure) |
| E-A2-E2-0002 | UNAUTH_INFO_DISCLOSURE | E2 | 0.700 | materials/firmae/dcs_login_hnap.txt:1 | 未认证 HNAP 响应泄露型号/固件/硬件/MAC（DCS-960L / A1 / 1.07 / 52:54:00:12:34:56）；单次请求 TODO(measure) |

## 3. 策略

本样例未生成策略。

## 4. 口径与限制

- 本报告含 E1/E2 证据；实测结论必须带报文/响应原文 raw_ref。
- 阈值/置信度为 provisional，锚点集校准前不得写入材料指标。
