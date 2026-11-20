# 入网体检报告：A1

## 1. 结论

| 项 | 值 |
|---|---|
| 厂商 / 型号 | Tenda / O4 V3.0 |
| 固件版本 | V1.0.0.19(6074) |
| 判定 | **conditional** |
| 置信度 | 0.500 |
| 风险敞口 | 0.625 |
| 加权保障度 | 0.245 |

**判定理由**

- 下限：CRED_DEFAULT_ADMIN_WEB（Critical）为 E3 风险，至少条件放行
- 下限：CRED_DEFAULT_SERVICE_LOGIN（Critical）为 E3 风险，至少条件放行
- 下限：UNAUTH_MGMT_ENDPOINT（Critical）为 E3 风险，至少条件放行
- 证据不足：加权保障度 assurance=0.245 < 0.60，未测项或弱证据占比较高，不能直接放行
- 风险项 5 个：CRED_DEFAULT_ADMIN_WEB(E3,c=0.50)；CRED_DEFAULT_SERVICE_LOGIN(E3,c=0.30)；CRED_HARDCODED_SECRET(E3,c=0.50)；UNAUTH_MGMT_ENDPOINT(E3,c=0.30)；EGRESS_FIXED_CLOUD_ENDPOINT(E3,c=0.40)

## 2. 证据清单

共 **32** 条；按等级：E1=0 / E2=0 / E3=32；按类别：CRED=4 / UNAUTH=24 / EGRESS=4。

| 编号 | 检查项 | 等级 | 置信度 | raw_ref | 说明 |
|---|---|---|---|---|---|
| E-A1-0001 | CRED_DEFAULT_ADMIN_WEB | E3 | 0.500 | webroot_ro/default.cfg:48 | 静态发现口令字段 sys.baseuserpass（值已脱敏，长度 8）；是否默认/可用待实测 TODO(measure) |
| E-A1-0002 | CRED_DEFAULT_SERVICE_LOGIN | E3 | 0.300 | etc_ro/passwd:1 | 静态发现可登录账号 root（uid=0, shell=/bin/sh）；是否为默认口令待影子设备实测 TODO(measure) |
| E-A1-0003 | CRED_HARDCODED_SECRET | E3 | 0.500 | etc_ro/prod-script:363 | 静态发现口令字段 old_password（值已脱敏，长度 4）；是否默认/可用待实测 TODO(measure) |
| E-A1-0004 | CRED_HARDCODED_SECRET | E3 | 0.400 | etc_ro/shadow:1 | 静态发现 root 口令哈希（算法 MD5-crypt）；弱口令/默认口令待实测 TODO(measure) |
| E-A1-0005 | EGRESS_FIXED_CLOUD_ENDPOINT | E3 | 0.300 | bin/httpd@0x751f8 | 静态发现二进制内 https 外联地址 host=cloudfi.tendacn.com；域名归属与外联行为未验证 TODO(measure) |
| E-A1-0006 | EGRESS_FIXED_CLOUD_ENDPOINT | E3 | 0.300 | bin/httpd@0x75218 | 静态发现二进制内 https 外联地址 host=ims.ip-com.com.cn；域名归属与外联行为未验证 TODO(measure) |
| E-A1-0007 | EGRESS_FIXED_CLOUD_ENDPOINT | E3 | 0.300 | bin/httpd@0x75238 | 静态发现二进制内 https 外联地址 host=imsen.ip-com.com.cn；域名归属与外联行为未验证 TODO(measure) |
| E-A1-0008 | EGRESS_FIXED_CLOUD_ENDPOINT | E3 | 0.400 | webroot_ro/goform/getCloud/index.html:6 | 静态发现硬编码 https 外联地址 host=cloudfi.tenda.com.cn；域名归属与外联行为未验证 TODO(measure) |
| E-A1-0009 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x6e27c | 静态发现接口 /cgi-bin/upgrade；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0010 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x75be8 | 静态发现接口 /goform/ate；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0011 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x75bf4 | 静态发现接口 /goform/ate_rf；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0012 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x75c10 | 静态发现接口 /goform/usbTest；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0013 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x75c20 | 静态发现接口 /goform/getAdStatistics；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0014 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x75c48 | 静态发现接口 /goform/telnet；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0015 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x75c58 | 静态发现接口 /goform/consoleOpen；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0016 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x75c6c | 静态发现接口 /goform/consoleClose；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0017 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x75c84 | 静态发现接口 /goform/getLoginInfo；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0018 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x75c9c | 静态发现接口 /goform/initAdminUser；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0019 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x75cd4 | 静态发现接口 /goform/getPreTimeoutNotify；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0020 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x75cf0 | 静态发现接口 /goform/getTimeoutNotify；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0021 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x75d0c | 静态发现接口 /goform/ackPreTimeoutNotify；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0022 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x75d28 | 静态发现接口 /goform/getQuickset；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0023 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x75d3c | 静态发现接口 /goform/getSysLogin；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0024 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x75d50 | 静态发现接口 /goform/setQuickset；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0025 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0x75d98 | 静态发现接口 /goform/get；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0026 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | webroot_ro/app.js:338 | 静态发现接口 /goform/getStaticsInfo；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0027 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | webroot_ro/goform/clearSyslog/index.html:2 | 静态发现接口 /goform/clearSyslog；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0028 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | webroot_ro/goform/test/index.html:2 | 静态发现接口 /goform/test；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0029 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | webroot_ro/js/system_config.js:177 | 静态发现接口 /cgi-bin/DownloadCfg；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0030 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | webroot_ro/js/system_status.js:31 | 静态发现接口 /goform/getSysStatusInfo；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0031 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | webroot_ro/js/wrl_advance.js:138 | 静态发现接口 /goform/setWrlAdvanceInfo；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A1-0032 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | webroot_ro/js/wrl_basic.js:896 | 静态发现接口 /goform/setWrlBasicInfo；鉴权状态未验证，需影子设备实测 TODO(measure) |

## 3. 策略

| 项 | 值 |
|---|---|
| 粒度 | fqdn |
| 载体 | acl |
| 规则条数 | 4 |
| ASN 回退 | False |
| 回滚引用 | rb-A1 |

```text
permit tcp any host cloudfi.tenda.com.cn eq 443
permit tcp any host cloudfi.tendacn.com eq 443
permit tcp any host ims.ip-com.com.cn eq 443
permit tcp any host imsen.ip-com.com.cn eq 443
```

## 4. 口径与限制

- 本报告全部证据为 E3（静态推断），未在影子设备中实测；结论只作准入初判，具体可利用性写 TODO(measure)。
- 阈值/置信度为 provisional，锚点集校准前不得写入材料指标。
