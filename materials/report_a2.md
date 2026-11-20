# 入网体检报告：A2

## 1. 结论

| 项 | 值 |
|---|---|
| 厂商 / 型号 | D-Link / DCS-960L |
| 固件版本 | 1.07.102 |
| 判定 | **conditional** |
| 置信度 | 0.300 |
| 风险敞口 | 0.794 |
| 加权保障度 | 0.132 |

**判定理由**

- 下限：UNAUTH_MGMT_ENDPOINT（Critical）为 E3 风险，至少条件放行
- 证据不足：加权保障度 assurance=0.132 < 0.60，未测项或弱证据占比较高，不能直接放行
- 风险项 3 个：CRED_HARDCODED_SECRET(E3,c=0.50)；UNAUTH_MGMT_ENDPOINT(E3,c=0.30)；EGRESS_FIXED_CLOUD_ENDPOINT(E3,c=0.40)

## 2. 证据清单

共 **4** 条；按等级：E1=0 / E2=0 / E3=4；按类别：CRED=1 / UNAUTH=2 / EGRESS=1。

| 编号 | 检查项 | 等级 | 置信度 | raw_ref | 说明 |
|---|---|---|---|---|---|
| E-A2-0001 | CRED_HARDCODED_SECRET | E3 | 0.500 | etc/rc.d/init.d/pppoe.sh:8 | 静态发现口令字段 pppoepwd（值已脱敏，长度 11）；是否默认/可用待实测 TODO(measure) |
| E-A2-0002 | EGRESS_FIXED_CLOUD_ENDPOINT | E3 | 0.400 | web/cgi-bin/home.asp:619 | 静态发现硬编码 http 外联地址 host=www.dlink.com；域名归属与外联行为未验证 TODO(measure) |
| E-A2-0003 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | etc/httpd.ini:2 | 静态发现接口 /hnap/hnap_service；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A2-0004 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | usr/sbin/eventd@0x22690 | 静态发现接口 /cgi-bin/lang；鉴权状态未验证，需影子设备实测 TODO(measure) |

## 3. 策略

| 项 | 值 |
|---|---|
| 粒度 | fqdn |
| 载体 | acl |
| 规则条数 | 1 |
| ASN 回退 | False |
| 回滚引用 | rb-A2 |

```text
permit tcp any host www.dlink.com eq 80
```

## 4. 口径与限制

- 本报告全部证据为 E3（静态推断），未在影子设备中实测；结论只作准入初判，具体可利用性写 TODO(measure)。
- 阈值/置信度为 provisional，锚点集校准前不得写入材料指标。
