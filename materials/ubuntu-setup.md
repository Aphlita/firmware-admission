# Ubuntu 实验主机准备（T0-4 环境自检 / T1-4 FirmAE 跑分）

> 用途：把「拿到 Ubuntu 主机后要做什么」固化下来，避免临场试错。
> 适用：FirmAE + binwalk + 三个锚点固件的首次真实解包与仿真。
> 说明：本文只写给实验主机用，测试固件来自 `data/firmware/`（不入库）。

## 0. 结论先行（省时间的顺序）

1. **先跑 binwalk 解包**（分钟级），能立刻产出 T1-1 的真实数据与信息表指标；
2. **再跑 FirmAE**（小时级，成功率约 79.36%），起不来的按 `configs/judgement.yaml` 降级 E3；
3. 两个都失败也不阻塞材料：证据按 E3 记录，指标栏写 `TODO(measure)`。

## 1. 主机自检（5 条命令）

```bash
lsb_release -a                          # 目标 Ubuntu 20.04（22.04 也可，但 FirmAE 适配风险更高）
egrep -c '(vmx|svm)' /proc/cpuinfo       # >0 才支持 KVM 加速
ls -l /dev/kvm                           # 存在才可 -enable-kvm
free -g                                  # 建议 >= 8 GB
df -h /                                  # 固件 + 解包产物，建议 >= 40 GB 可用
python3 --version                        # 建议 3.10+；代码用 `X | None` 注解 + from __future__，
                                         # 3.8 理论可跑但未验证，优先 3.11
```

若 `/dev/kvm` 不存在：FirmAE 仍可用 TCG 纯软件模拟，但单个固件可能要 30–90 分钟。

## 2. 依赖

```bash
sudo apt update
sudo apt install -y binwalk qemu-system-arm qemu-system-mips qemu-system-x86 \
                    python3-pip git unzip cpio pkg-config libglib2.0-dev
# binwalk 版本确认（v2 与 v3 输出/目录行为不同，代码已兼容两者）
binwalk --help | head -3
```

> 注意：Ubuntu 22.04 的 `binwalk` 可能被替换为 Rust 版 v3；`src/unpack.py` 已用递归扫描兼容，无需改代码。

## 3. 第一批真实解包（T1-1 验证，分钟级）

把两个固件从 Windows 拷到主机（或用 scp）：

```bash
mkdir -p ~/fw && cd ~/fw
# 从本机传入（在 Windows 侧执行）
# scp data/firmware/US_AC15V1.0BR_V15.03.05.18_multi_TD01.zip 用户@主机:~/fw/

unzip -o US_AC15V1.0BR_V15.03.05.18_multi_TD01.zip
sha256sum US_AC15V1.0BR_V15.03.05.18_multi_TD01.bin
# 期望：15a7c2addb27c8d8525a4bddeb86b3d34fd8e310faf07f178fbbe9207c99cc85

binwalk US_AC15V1.0BR_V15.03.05.18_multi_TD01.bin | head -40
```

`binwalk` 输出里应能看到 `TRX firmware header` / `LZMA compressed data` / `SquashFS filesystem`，这就是 `src/unpack.py` 的 `components` 来源。

再用我们的封装跑一次（在项目根执行）：

```bash
python -m src.unpack ~/fw/US_AC15V1.0BR_V15.03.05.18_multi_TD01.bin
# 期望 JSON：ok=true, components 非空, filesystem_paths 指向 .../squashfs-root, file_count>0
```

## 4. FirmAE 安装与跑分（小时级）

```bash
git clone --recursive https://github.com/pr0v3rbs/FirmAE.git ~/FirmAE
cd ~/FirmAE
./download.sh          # 首次会拉取依赖，耗时较长
sudo ./install.sh
```

跑一个固件（AC15 优先：10.5 MB，老固件，成功率最高）：

```bash
cd ~/FirmAE
sudo ./run.sh -c ~/fw/US_AC15V1.0BR_V15.03.05.18_multi_TD01.bin
# -c 表示 console 模式；跑通后可用 -r 起网络
sudo ./run.sh -r mips ~/fw/US_AC15V1.0BR_V15.03.05.18_multi_TD01.bin  # 视架构而定
```

记录三件事（`docs/00` §4.1 第 2 项的交付物）：
1. 起/不起；
2. 卡点（最后一段报错）；
3. 日志末十行（`~/FirmAE/scratch/<n>/qemu.final.serial.log`）。

**跑不起来怎么办**：直接按 `configs/judgement.yaml` 的 `fallback.when_emulation_failed: E3` 处理，并把卡点写进 `materials/实验记录.md`——失败记录本身就是材料。

## 5. 三个锚点的建议顺序

| 顺序 | 固件 | 理由 |
|---|---|---|
| 1 | Tenda AC15 V15.03.05.18 | 10.5 MB，TRX+LZMA，老平台，FirmAE 命中率最高 |
| 2 | D-Link DCS-960L 1.07.102 | 9.9 MB，有精确匹配的 HNAP 未授权 RCE |
| 3 | Tenda O4 V3.0 | A1，需先从 Tenda 官网取得固件文件（尚未下载到本地） |

> A1 的固件文件目前**不在** `data/firmware/`，只有下载页链接；T1-4 前需先取得。

## 6. 我需要的信息

- `用户名@IP:端口`；
- 是否允许我在这台机器上 `sudo apt install`（FirmAE 安装需要 root）；
- 若走非 22 端口，告诉我端口号。

拿到后我会：SSH 登录 → 执行第 1 节自检 → 按第 2–4 节推进 → 把每步输出写回 `materials/实验记录.md`。