# immortalwrt24.10-6.6-cmcc_rax3000m

[![Build OpenWrt](https://github.com/XiaoXinCodes/immortalwrt24.10-6.6-cmcc_rax3000m-237/actions/workflows/openwrt-builder.yml/badge.svg)](https://github.com/XiaoXinCodes/immortalwrt24.10-6.6-cmcc_rax3000m-237/actions/workflows/openwrt-builder.yml)
[![GitHub release](https://img.shields.io/github/v/release/XiaoXinCodes/immortalwrt24.10-6.6-cmcc_rax3000m-237?include_prereleases&label=%E5%9B%BA%E4%BB%B6%E7%89%88%E6%9C%AC)](https://github.com/XiaoXinCodes/immortalwrt24.10-6.6-cmcc_rax3000m-237/releases)
[![License](https://img.shields.io/github/license/XiaoXinCodes/immortalwrt24.10-6.6-cmcc_rax3000m-237?label=%E5%8D%8F%E8%AE%AE)](LICENSE)

为 **中国移动定制版 RAX3000M**（CMCC RAX3000M）打造的 ImmortalWrt 固件，基于 `openwrt-24.10` + `6.6` 内核，大功率无线预调，开箱即用。

## 固件信息

| 项目 | 说明 |
| --- | --- |
| 源码 | [padavanonly/immortalwrt-mt798x-6.6](https://github.com/padavanonly/immortalwrt-mt798x-6.6)（`openwrt-24.10-6.6` 分支） |
| 目标平台 | `mediatek/filogic`（MT7981，aarch64） |
| 适配机型 | CMCC RAX3000M（仅此一款，不含其它 filogic 机型） |
| 管理地址 | `192.168.6.1` |
| 登录 | 用户名 `root`，密码为空 |
| 默认主题 | Argon |

## 集成插件

| 插件 | 说明 | 上游 |
| --- | --- | --- |
| HomeProxy | 基于 sing-box 1.14 的代理平台，LuCI 可视化配置 | [szwjp/luci-app-homeproxy](https://github.com/szwjp/luci-app-homeproxy) |
| EasyTier | 去中心化组网 / 异地互联，含核心与 LuCI | [EasyTier/luci-app-easytier](https://github.com/EasyTier/luci-app-easytier) |
| ZeroTier | 虚拟局域网 | 官方 feed |
| USB 打印 | `p910nd` 打印服务器 | 官方 feed |
| USB 网卡 | `kmod-usb-net` 及常用驱动 | 官方 feed |
| TTYD | 网页终端 | 官方 feed |
| iPerf3 | 内网测速 | 官方 feed |
| UPnP | 端口自动映射 | 官方 feed |

> 每次构建查询 sing-box 官方最新稳定版，读取该版本的 `go.mod` 和 `toolchain` 要求，自动选择满足要求的 Go 工具链配方（见 `diy-part2.sh`）。

## 下载与刷机

1. 前往 [Releases](https://github.com/XiaoXinCodes/immortalwrt24.10-6.6-cmcc_rax3000m-237/releases) 下载最新版 `*-sysupgrade.bin`；
2. 在 Breed / U-Boot 下刷入；
3. 首次启动后浏览器打开 `192.168.6.1`，用户名 `root`，密码留空登录。

> 刷机有变砖风险，请确保手头有 Breed 或编程器救砖手段。**首次刷入建议先备份原厂固件 / EEPROM。**

## 自行构建

本仓库使用 GitHub Actions 自动编译，构建流程定义在 [`.github/workflows/openwrt-builder.yml`](.github/workflows/openwrt-builder.yml)。

### 触发构建

- `Actions` → `Build OpenWrt` → `Run workflow`，构建完成后固件自动发布到 Releases，同时保留 Artifacts 备份。

### 自定义固件

| 文件 | 用途 | 执行时机 |
| --- | --- | --- |
| [`.config`](.config) | 编译配置：目标机型、内核模块、插件开关 | feeds 安装后载入 |
| [`diy-part1.sh`](diy-part1.sh) | 添加第三方软件源（如 HomeProxy、EasyTier） | feeds 更新**之前** |
| [`diy-part2.sh`](diy-part2.sh) | 修改默认设置、替换工具链/核心包版本、在 `make defconfig` 前同步插件开关 | feeds 更新**之后** |

改完直接 push，Actions 会自动开始构建。本地想先验证配置：

```bash
git clone https://github.com/padavanonly/immortalwrt-mt798x-6.6 -b openwrt-24.10-6.6 openwrt
cd openwrt
cp /path/to/.config .config
bash /path/to/diy-part1.sh
./scripts/feeds update -a && ./scripts/feeds install -a
bash /path/to/diy-part2.sh
make defconfig RECURSIVE_DEP_IS_ERROR=1
make menuconfig   # 可视化调整
```

### 构建环境说明

工作流先用 [`jlumbroso/free-disk-space`](https://github.com/jlumbroso/free-disk-space) 清理无关预装软件，再安装依赖，最后使用 [`easimon/maximize-build-space`](https://github.com/easimon/maximize-build-space) 将构建盘明确挂载到 `/workdir`。源码、构建目录、下载和临时缓存均放在该盘，避免扩容后仍在根分区编译。分配后给根分区预留 4 GiB；这个数值不代表构建盘容量。

构建前检查实际挂载、可用容量和 inode，默认要求至少 50 GiB 可用空间（工作流变量 `MIN_BUILD_FREE_GIB`）。这是初始预算，并非已测得的最低需求；若 runner 容量不足，应根据完整构建峰值调整预算或使用更大磁盘的 runner。

默认启用 `CONFIG_AUTOREMOVE=y`，由 OpenWrt 在包构建完成后清理中间文件，降低编译期间占用；后续增量重编译会更慢。内核调试信息仍保留。编译期间每 3 分钟记录空间和 inode 使用量，失败时上传 `build-failure-diagnostics`，保留 7 天。开启按包保存日志；失败时将具体编译器错误写入 Actions 注解和摘要，避免只有 `failed to build` 的提示。

上游 `mt_wifi` 从 `warp` 构建目录读取头文件；自动清理会提前删除这些文件，导致无线驱动编译缺失 `warp.h` / `warp_wifi.h`。`diy-part1.sh` 应用 `patches/mtk-warp-stage-headers.patch`，让 `warp` 通过 `Build/InstallDev` 导出头文件到 target staging，保留目录结构，再让 `mt_wifi` 从 staging 读取。自动清理和无线硬件卸载继续启用。工作流先执行上游 `make prepare` 构建 host tools、交叉工具链和目标内核，再编译无线驱动并检查 AArch64 内核模块，最后编译剩余固件。单包编译目标不能代替这些前置构建。

可针对未修改的上游源码复现并验证头文件在清理后的可用性（此检查不代替驱动交叉编译）：

```bash
python3 tests/check_warp_header_staging.py --source-dir /path/to/unmodified/openwrt
```

`diy-part2.sh` 每次查询 sing-box 官方最新稳定 release，获取 OpenWrt master 的打包配方，并根据官方 release 更新版本和源码 SHA-256；缓存及后续下载仍由 OpenWrt 校验哈希。读取发布源码的 Go 要求后，自动从 sbwml 的 Go 分支选择满足最低版本的配方，包含补丁版本比较。发现失败时直接报错，不回退旧版或关闭校验。

当前构建系统的 tiny 虚拟包声明兼容处理仍保留。未选中的 PassWall 不安装进本次构建的包目录；若显式选中它，则保留并交由严格配置检查报告问题。解析后的 sing-box/Go 版本、源码哈希和配方提交记录在 `proxy-package-versions.json`，随固件或失败诊断上传。`Inspect build logs` 工作流可以按 run ID 读取构建日志，生成可直接查看的错误摘要。

## 仓库结构

```
.
├── .config                        # 编译配置
├── .github/workflows/
│   ├── openwrt-builder.yml        # 固件构建流水线
│   └── update-checker.yml         # 上游更新检查
├── diy-part1.sh                   # 第三方软件源（feeds 更新前）
├── diy-part2.sh                   # 工具链/默认设置（feeds 更新后）
└── README.md
```

## 致谢

- [P3TERX/Actions-OpenWrt](https://github.com/P3TERX/Actions-OpenWrt) —— 工作流模板
- [padavanonly](https://github.com/padavanonly/immortalwrt-mt798x-6.6) —— mt798x 机型源码维护
- [ImmortalWrt](https://github.com/immortalwrt/immortalwrt) / [OpenWrt](https://github.com/openwrt/openwrt)
- [szwjp](https://github.com/szwjp/luci-app-homeproxy)、[EasyTier](https://github.com/EasyTier/EasyTier)、[sbwml](https://github.com/sbwml/packages_lang_golang)

## 免责声明

本固件仅供学习交流使用。请遵守当地法律法规，代理类插件请勿用于非法用途。因刷机造成的任何设备损坏或数据丢失，作者不承担责任。

## 协议

[MIT](LICENSE)
