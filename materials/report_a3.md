# 入网体检报告：A3

## 1. 结论

| 项 | 值 |
|---|---|
| 厂商 / 型号 | Tenda / AC15 |
| 固件版本 | V15.03.05.18 |
| 判定 | **conditional** |
| 置信度 | 0.500 |
| 风险敞口 | 0.642 |
| 加权保障度 | 0.262 |

**判定理由**

- 下限：CRED_DEFAULT_ADMIN_WEB（Critical）为 E3 风险，至少条件放行
- 下限：CRED_DEFAULT_SERVICE_LOGIN（Critical）为 E3 风险，至少条件放行
- 下限：UNAUTH_MGMT_ENDPOINT（Critical）为 E3 风险，至少条件放行
- 证据不足：加权保障度 assurance=0.262 < 0.60，未测项或弱证据占比较高，不能直接放行
- 风险项 5 个：CRED_DEFAULT_ADMIN_WEB(E3,c=0.50)；CRED_DEFAULT_SERVICE_LOGIN(E3,c=0.50)；CRED_HARDCODED_SECRET(E3,c=0.40)；UNAUTH_MGMT_ENDPOINT(E3,c=0.30)；EGRESS_FIXED_CLOUD_ENDPOINT(E3,c=0.40)

## 2. 证据清单

共 **36** 条；按等级：E1=0 / E2=0 / E3=36；按类别：CRED=10 / UNAUTH=21 / EGRESS=5。

| 编号 | 检查项 | 等级 | 置信度 | raw_ref | 说明 |
|---|---|---|---|---|---|
| E-A3-0001 | CRED_DEFAULT_ADMIN_WEB | E3 | 0.500 | webroot_ro/default.cfg:262 | 静态发现口令字段 sys.baseuserpass（值已脱敏，长度 4）；是否默认/可用待实测 TODO(measure) |
| E-A3-0002 | CRED_DEFAULT_SERVICE_LOGIN | E3 | 0.300 | etc_ro/passwd:1 | 静态发现可登录账号 root（uid=0, shell=/bin/sh）；是否为默认口令待影子设备实测 TODO(measure) |
| E-A3-0003 | CRED_DEFAULT_SERVICE_LOGIN | E3 | 0.300 | etc_ro/passwd:2 | 静态发现可登录账号 admin（uid=0, shell=/bin/sh）；是否为默认口令待影子设备实测 TODO(measure) |
| E-A3-0004 | CRED_DEFAULT_SERVICE_LOGIN | E3 | 0.300 | etc_ro/passwd:3 | 静态发现可登录账号 support（uid=0, shell=/bin/sh）；是否为默认口令待影子设备实测 TODO(measure) |
| E-A3-0005 | CRED_DEFAULT_SERVICE_LOGIN | E3 | 0.300 | etc_ro/passwd:4 | 静态发现可登录账号 user（uid=0, shell=/bin/sh）；是否为默认口令待影子设备实测 TODO(measure) |
| E-A3-0006 | CRED_DEFAULT_SERVICE_LOGIN | E3 | 0.300 | etc_ro/passwd:5 | 静态发现可登录账号 nobody（uid=0, shell=/bin/sh）；是否为默认口令待影子设备实测 TODO(measure) |
| E-A3-0007 | CRED_DEFAULT_SERVICE_LOGIN | E3 | 0.500 | webroot_ro/default.cfg:315 | 静态发现口令字段 usb.ftp.pwd（值已脱敏，长度 5）；是否默认/可用待实测 TODO(measure) |
| E-A3-0008 | CRED_DEFAULT_SERVICE_LOGIN | E3 | 0.500 | webroot_ro/default.cfg:323 | 静态发现口令字段 usb.samba.pwd（值已脱敏，长度 5）；是否默认/可用待实测 TODO(measure) |
| E-A3-0009 | CRED_DEFAULT_SERVICE_LOGIN | E3 | 0.500 | webroot_ro/default.cfg:328 | 静态发现口令字段 usb.samba.guest.pwd（值已脱敏，长度 5）；是否默认/可用待实测 TODO(measure) |
| E-A3-0010 | CRED_HARDCODED_SECRET | E3 | 0.400 | etc_ro/shadow:1 | 静态发现 root 口令哈希（算法 MD5-crypt）；弱口令/默认口令待实测 TODO(measure) |
| E-A3-0011 | EGRESS_FIXED_CLOUD_ENDPOINT | E3 | 0.300 | bin/phddns@0xd3f5 | 静态发现二进制内 http 外联地址 host=www.oray.com；域名归属与外联行为未验证 TODO(measure) |
| E-A3-0012 | EGRESS_FIXED_CLOUD_ENDPOINT | E3 | 0.400 | webroot_ro/default.cfg:86 | 静态发现硬编码 http 外联地址 host=www.tenda.com.cn；域名归属与外联行为未验证 TODO(measure) |
| E-A3-0013 | EGRESS_FIXED_CLOUD_ENDPOINT | E3 | 0.400 | webroot_ro/goform/WifiPowerGet.txt:4 | 静态发现硬编码 http 外联地址 host=www.baidu.com；域名归属与外联行为未验证 TODO(measure) |
| E-A3-0014 | EGRESS_FIXED_CLOUD_ENDPOINT | E3 | 0.400 | webroot_ro/index.html:399 | 静态发现硬编码 http 外联地址 host=wifi.yunos.com；域名归属与外联行为未验证 TODO(measure) |
| E-A3-0015 | EGRESS_FIXED_CLOUD_ENDPOINT | E3 | 0.400 | webroot_ro/xunleiDownload.html:40 | 静态发现硬编码 http 外联地址 host=yuancheng.xunlei.com；域名归属与外联行为未验证 TODO(measure) |
| E-A3-0016 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0xd4220 | 静态发现接口 /cgi-bin/DownloadCfg；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0017 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0xd4238 | 静态发现接口 /cgi-bin/DownloadFlash；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0018 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0xd4250 | 静态发现接口 /cgi-bin/DownloadSyslog；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0019 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0xd4268 | 静态发现接口 /cgi-bin/DownloadLog；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0020 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0xd4b6c | 静态发现接口 /goform/telnet；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0021 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0xd4b88 | 静态发现接口 /goform/fast_setting；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0022 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0xd4ba0 | 静态发现接口 /goform/ate；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0023 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0xd4bac | 静态发现接口 /goform/InsertWhite；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0024 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0xd4bd0 | 静态发现接口 /goform/getWanConnectStatus；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0025 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0xd4bec | 静态发现接口 /goform/getProduct；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0026 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0xd4c00 | 静态发现接口 /goform/getRebootStatus；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0027 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0xd4cd4 | 静态发现接口 /goform/GetRouterStatus；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0028 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0xd4cec | 静态发现接口 /goform/getWanParameters；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0029 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0xd4d08 | 静态发现接口 /goform/GetUSBStatus；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0030 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | bin/httpd@0xd4d58 | 静态发现接口 /goform/WifiApScan；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0031 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | etc_ro/nginx/conf/nginx.conf:48 | 静态发现接口 /cgi-bin/luci；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0032 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | webroot_ro/directupgrade.html:27 | 静态发现接口 /cgi-bin/upgrade；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0033 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | webroot_ro/js/dlna.js:134 | 静态发现接口 /goform/refreshDLNA；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0034 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | webroot_ro/system_backup.html:15 | 静态发现接口 /cgi-bin/UploadCfg；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0035 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | webroot_ro/system_password.html:15 | 静态发现接口 /goform/SysToolChangePwd；鉴权状态未验证，需影子设备实测 TODO(measure) |
| E-A3-0036 | UNAUTH_MGMT_ENDPOINT | E3 | 0.300 | webroot_ro/system_reboot.html:15 | 静态发现接口 /goform/SysToolReboot；鉴权状态未验证，需影子设备实测 TODO(measure) |

## 3. 策略

| 项 | 值 |
|---|---|
| 粒度 | fqdn |
| 载体 | acl |
| 规则条数 | 5 |
| ASN 回退 | False |
| 回滚引用 | rb-A3 |

```text
permit tcp any host wifi.yunos.com eq 80
permit tcp any host www.baidu.com eq 80
permit tcp any host www.oray.com eq 80
permit tcp any host www.tenda.com.cn eq 80
permit tcp any host yuancheng.xunlei.com eq 80
```

## 4. 口径与限制

- 本报告全部证据为 E3（静态推断），未在影子设备中实测；结论只作准入初判，具体可利用性写 TODO(measure)。
- 阈值/置信度为 provisional，锚点集校准前不得写入材料指标。
